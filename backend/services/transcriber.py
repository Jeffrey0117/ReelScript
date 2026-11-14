"""
Transcription service — Whisper-based speech-to-text.

The Whisper work itself (model loading, GPU with CPU fallback, sentence splitting, the
non-English guard) lives in whisper_kit.py, a copy of github.com/Jeffrey0117/whisper-kit.
This file only maps ReelScript's config.json and data shapes onto it.
"""

import os
import json
from dataclasses import dataclass, asdict
from typing import List, Optional

from . import whisper_kit

DEFAULT_WHISPER_CONFIG = {
    "model": "distil-large-v3",
    "language": "en",
    "device": "auto",
    "compute_type": "int8",
    "vad_filter": True,
    "max_words_per_segment": 30,
}


class NonEnglishAudioError(Exception):
    """Raised when the audio track is confidently detected as a non-English language."""

    def __init__(self, language: str, probability: float):
        self.language = language
        self.probability = probability
        # video_routes matches failures on the "Non-English audio" prefix — keep it.
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
    Config (config.json):
    {
        "whisper": {
            "model": "distil-large-v3",
            "language": "en",
            "device": "auto",              // GPU when there is one, CPU otherwise
            "compute_type": "int8",
            "vad_filter": true,
            "max_words_per_segment": 30,
            "reject_non_english": true,    // only applies when language is "en"
            "language_detect_threshold": 0.5
        }
    }
    """

    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> dict:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"whisper": dict(DEFAULT_WHISPER_CONFIG)}

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

        cfg = self.config.get("whisper", {})
        lang = language or cfg.get("language", "en")
        # Pinning language=en on non-English audio makes Whisper invent fake English,
        # so English-only transcription first checks what the audio really is.
        guard = lang == "en" and cfg.get("reject_non_english", True)

        print(f"[Whisper] Transcribing: {os.path.basename(video_path)} (lang={lang})")
        try:
            result = whisper_kit.transcribe(
                video_path,
                model=cfg.get("model", "base"),
                device=cfg.get("device", "auto"),
                compute_type=cfg.get("compute_type", ""),
                language=lang,
                guard_language=guard,
                guard_threshold=cfg.get("language_detect_threshold", 0.5),
                max_words=cfg.get("max_words_per_segment", 12),
                vad=cfg.get("vad_filter", True),
                vad_parameters=cfg.get("vad_parameters"),
            )
        except whisper_kit.UnexpectedLanguageError as error:
            raise NonEnglishAudioError(error.language, error.probability) from error

        segments = [
            Segment(index=i, start=piece["start"], end=piece["end"], text=piece["text"])
            for i, piece in enumerate(result["segments"], start=1)
        ]
        print(f"[Whisper] Done — {len(segments)} segments "
              f"({result['language']}, {result['model']} on {result['device']})")
        return segments

    @staticmethod
    def segments_to_dict(segments: List[Segment]) -> list:
        return [asdict(s) for s in segments]

    @staticmethod
    def segments_to_full_text(segments: List[Segment]) -> str:
        return " ".join(s.text for s in segments)


# Singleton
transcriber = Transcriber()
