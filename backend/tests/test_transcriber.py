"""The transcriber is a thin adapter over whisper_kit. These tests pin down what the rest of
ReelScript relies on, without loading a model.

Run from backend/:  python -m unittest discover -s tests
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import whisper_kit  # noqa: E402
from services.transcriber import NonEnglishAudioError, Segment, Transcriber  # noqa: E402

KIT_RESULT = {
    "language": "en", "language_probability": 0.99, "duration": 5.0, "device": "cpu", "model": "distil-large-v3",
    "segments": [{"start": 0.0, "end": 2.5, "text": "Hello there."}, {"start": 2.5, "end": 5.0, "text": "Next one."}],
}


def make(whisper_config: dict) -> Transcriber:
    with mock.patch.object(Transcriber, "_load_config", return_value={"whisper": whisper_config}):
        return Transcriber()


class TranscriberTest(unittest.TestCase):
    def setUp(self):
        exists = mock.patch("os.path.exists", return_value=True)
        exists.start()
        self.addCleanup(exists.stop)

    def run_with(self, whisper_config, **kwargs):
        with mock.patch.object(whisper_kit, "transcribe", return_value=KIT_RESULT) as fake:
            segments = make(whisper_config).transcribe("video.mp4", **kwargs)
        return segments, fake.call_args

    def test_segments_keep_the_shape_the_routes_use(self):
        segments, _ = self.run_with({})
        self.assertEqual(segments, [
            Segment(index=1, start=0.0, end=2.5, text="Hello there.", translation=""),
            Segment(index=2, start=2.5, end=5.0, text="Next one.", translation=""),
        ])
        self.assertEqual(Transcriber.segments_to_full_text(segments), "Hello there. Next one.")
        self.assertEqual(Transcriber.segments_to_dict(segments)[1]["index"], 2)

    def test_config_reaches_the_kit(self):
        config = {"model": "distil-large-v3", "language": "en", "device": "auto", "compute_type": "int8",
                  "vad_filter": True, "max_words_per_segment": 30, "vad_parameters": {"min_silence_duration_ms": 500},
                  "language_detect_threshold": 0.7}
        _, call = self.run_with(config)
        self.assertEqual(call.args, ("video.mp4",))
        self.assertEqual(call.kwargs, {
            "model": "distil-large-v3", "device": "auto", "compute_type": "int8", "language": "en",
            "guard_language": True, "guard_threshold": 0.7, "max_words": 30, "vad": True,
            "vad_parameters": {"min_silence_duration_ms": 500},
        })

    def test_defaults_when_config_is_empty(self):
        _, call = self.run_with({})
        self.assertEqual((call.kwargs["model"], call.kwargs["language"], call.kwargs["max_words"]), ("base", "en", 12))
        self.assertEqual((call.kwargs["device"], call.kwargs["vad"], call.kwargs["guard_threshold"]), ("auto", True, 0.5))

    def test_guard_only_for_pinned_english_and_can_be_turned_off(self):
        self.assertTrue(self.run_with({"language": "en"})[1].kwargs["guard_language"])
        self.assertFalse(self.run_with({"language": "en", "reject_non_english": False})[1].kwargs["guard_language"])
        self.assertFalse(self.run_with({"language": "ja"})[1].kwargs["guard_language"])
        # an explicit language argument wins over the config
        call = self.run_with({"language": "en"}, language="ja")[1]
        self.assertEqual((call.kwargs["language"], call.kwargs["guard_language"]), ("ja", False))

    def test_wrong_language_keeps_the_error_the_pipeline_matches_on(self):
        refusal = whisper_kit.UnexpectedLanguageError("en", "ja", 0.93)
        with mock.patch.object(whisper_kit, "transcribe", side_effect=refusal):
            with self.assertRaises(NonEnglishAudioError) as caught:
                make({"language": "en"}).transcribe("video.mp4")
        self.assertEqual((caught.exception.language, caught.exception.probability), ("ja", 0.93))
        # video_routes maps failures by this exact prefix
        self.assertTrue(str(caught.exception).startswith("Non-English audio"))

    def test_missing_file(self):
        with mock.patch("os.path.exists", return_value=False):
            with self.assertRaises(FileNotFoundError):
                make({}).transcribe("nope.mp4")


if __name__ == "__main__":
    unittest.main()
