"""
Transcription service — Whisper-based speech-to-text.
Adapted from AutoReel's subtitle_generator.py (faster-whisper engine).
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional


class NonEnglishAudioError(Exception):
    """Raised when the audio track is confidently detected as a non-English language."""

    def __init__(self, language: str, probability: float):
        self.language = language
        self.probability = probability
        super().__init__(f"Non-English audio detected: {language} ({probability:.0%})")


@dataclass
class Segment:
    """A single transcript segment with timestamps."""
    index: int
    start: float  # seconds
    end: float    # seconds
    text: str
    translation: str = ""


class Transcriber:
    """
    Whisper-based transcriber using faster-whisper.

    Config (config.json):
    {
        "whisper": {
            "model": "base",
            "language": "en",
            "device": "auto",
            "compute_type": "int8",
            "vad_filter": true
        }
    }
    """

    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self._model = None
        self._detect_model = None

    def _load_config(self, config_path: str) -> dict:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "whisper": {
                "model": "distil-large-v3",
                "language": "en",
                "device": "auto",
                "compute_type": "int8",
                "vad_filter": True,
                "max_words_per_segment": 30,
            }
        }

    def _get_device(self) -> str:
        device = self.config.get("whisper", {}).get("device", "auto")
        if device == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return device

    def _load_model(self):
        if self._model is not None:
            return self._model

        # Suppress HuggingFace symlink warnings on Windows
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

        from faster_whisper import WhisperModel

        whisper_cfg = self.config.get("whisper", {})
        model_name = whisper_cfg.get("model", "base")
        device = self._get_device()
        compute_type = whisper_cfg.get("compute_type", "int8" if device == "cpu" else "float16")

        print(f"[Whisper] Loading model: {model_name} (device={device}, compute={compute_type})")

        self._model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )
        return self._model

    def transcribe(self, video_path: str, language: Optional[str] = None) -> List[Segment]:
        """
        Transcribe a video file into timestamped segments.

        Args:
            video_path: Path to the video/audio file
            language: Language code (default from config)

        Returns:
            List of Segment objects
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        model = self._load_model()
        whisper_cfg = self.config.get("whisper", {})
        lang = language or whisper_cfg.get("language", "en")
        max_words = whisper_cfg.get("max_words_per_segment", 12)
        vad_filter = whisper_cfg.get("vad_filter", True)
        vad_params = whisper_cfg.get("vad_parameters", None)

        print(f"[Whisper] Transcribing: {os.path.basename(video_path)} (lang={lang})")

        # Guard: pinning language=en on non-English audio makes Whisper hallucinate
        # fake English. Detect the real language first and reject confident non-English.
        if lang == "en" and whisper_cfg.get("reject_non_english", True):
            self._assert_english(video_path, whisper_cfg)

        transcribe_opts = {
            "language": lang,
            "task": "transcribe",
            "word_timestamps": True,
            "vad_filter": vad_filter,
        }
        if vad_filter and vad_params:
            transcribe_opts["vad_parameters"] = vad_params

        segments_gen, info = model.transcribe(video_path, **transcribe_opts)
        print(f"[Whisper] Detected: {info.language} ({info.language_probability:.0%})")

        segments = self._process_segments(segments_gen, max_words)
        print(f"[Whisper] Done — {len(segments)} segments")
        return segments

    def _load_detect_model(self):
        """Multilingual 'tiny' model used ONLY for language detection — the main
        model (distil-large-v3) is an English-only distillation whose detection
        always reports en, so it can't be trusted for this."""
        if self._detect_model is None:
            from faster_whisper import WhisperModel
            device = self._get_device()
            print("[Whisper] Loading detection model: tiny")
            self._detect_model = WhisperModel("tiny", device=device, compute_type="int8")
        return self._detect_model

    def _assert_english(self, video_path: str, whisper_cfg: dict) -> None:
        """Cheap detection pass (first 30s, no decode) — raises NonEnglishAudioError
        when the audio is confidently not English. Low-confidence detections pass
        through so accented English isn't rejected."""
        threshold = whisper_cfg.get("language_detect_threshold", 0.5)
        try:
            model = self._load_detect_model()
            gen, info = model.transcribe(
                video_path,
                language=None,
                task="transcribe",
                vad_filter=False,
                condition_on_previous_text=False,
            )
            del gen  # detection only — never consume the generator
        except Exception as e:
            print(f"[Whisper] Language detection failed (non-fatal, continuing): {e}")
            return
        print(f"[Whisper] Language detected: {info.language} ({info.language_probability:.0%})")
        if info.language != "en" and info.language_probability >= threshold:
            raise NonEnglishAudioError(info.language, info.language_probability)

    def _process_segments(self, segments_gen, max_words: int) -> List[Segment]:
        entries = []
        idx = 1

        for seg in segments_gen:
            words = seg.words

            if not words:
                entries.append(Segment(
                    index=idx,
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                ))
                idx += 1
                continue

            # Split into segments at sentence-ending punctuation only
            current_words = []
            current_start = None

            for w in words:
                if current_start is None:
                    current_start = w.start
                current_words.append(w.word.strip())

                is_sentence_end = w.word.rstrip().endswith((".", "?", "!"))
                is_too_long = len(current_words) >= max_words

                if (is_sentence_end or is_too_long) and current_words:
                    text = " ".join(current_words).strip()
                    if text:
                        entries.append(Segment(
                            index=idx,
                            start=current_start,
                            end=w.end,
                            text=text,
                        ))
                        idx += 1
                    current_words = []
                    current_start = None

            if current_words:
                text = " ".join(current_words).strip()
                if text:
                    entries.append(Segment(
                        index=idx,
                        start=current_start,
                        end=words[-1].end,
                        text=text,
                    ))
                    idx += 1

        return entries

    @staticmethod
    def segments_to_dict(segments: List[Segment]) -> list:
        return [asdict(s) for s in segments]

    @staticmethod
    def segments_to_full_text(segments: List[Segment]) -> str:
        return " ".join(s.text for s in segments)


# Singleton
transcriber = Transcriber()
