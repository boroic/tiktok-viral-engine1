import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main as video_engine


class _StubOpenAI:
    def generate_script(self, *_args, **_kwargs):
        return {"hook": "Hook", "body": ["Tip 1", "Tip 2"], "cta": "Follow for more"}

    def generate_hashtags(self, *_args, **_kwargs):
        return ["#viral", "#tips"]

    def generate_captions(self, *_args, **_kwargs):
        return ["Caption option"]

    def generate_full_content_pack(self, *_args, **_kwargs):
        return {
            "caption_final": "Final caption",
            "voiceover_script": "Hook Tip 1 Tip 2 Follow for more"
        }


class _StubAPIManager:
    def __init__(self):
        self.openai = _StubOpenAI()


class _StubVideoAssembler:
    def __init__(self, assemble_result):
        self.assemble_result = assemble_result
        self.last_audio_path = None

    def build_subtitles(self, _scene_plan, _duration_seconds, _destination):
        return None

    def assemble(self, duration_seconds, subtitle_path, output_path, audio_path=None):
        _ = (duration_seconds, subtitle_path, output_path)
        self.last_audio_path = audio_path
        return dict(self.assemble_result)


class _StubTTSProvider:
    provider_name = "openai"

    def __init__(self, result):
        self.result = result

    def synthesize(self, text, voice_preset, destination):
        _ = (text, voice_preset, destination)
        return dict(self.result)


class AutoCreateVideoFallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.upload_dir_patch = patch.object(video_engine, "UPLOAD_STORAGE_DIR", Path(self.tmp_dir.name))
        self.upload_dir_patch.start()

    def tearDown(self):
        self.upload_dir_patch.stop()
        self.tmp_dir.cleanup()

    def _build_engine(self, tts_result, assemble_result):
        engine = video_engine.TikTokViralEngine()
        engine.api_manager = _StubAPIManager()
        engine.tts_provider = _StubTTSProvider(tts_result)
        engine.video_assembler = _StubVideoAssembler(assemble_result)
        engine._register_artifact = lambda _artifact_id, _output_path: None
        return engine

    def test_tts_429_uses_silent_fallback_and_returns_ready_video(self):
        engine = self._build_engine(
            tts_result={
                "status": "error",
                "error_type": "rate_limited",
                "message": "TTS quota/rate-limit reached (HTTP 429).",
                "http_status": 429
            },
            assemble_result={"status": "success", "message": "MP4 generated successfully.", "diagnostics": {}}
        )

        result = engine.auto_create_video("topic", "balanced", "general", 45, "female", "educational")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["video"]["status"], "ready")
        self.assertTrue(result["video"]["download_url"])
        self.assertEqual(result["warnings"][0]["warning_code"], video_engine.TTS_FALLBACK_WARNING_CODE)
        self.assertIn("HTTP 429", result["warnings"][0]["warning_message"])
        self.assertIn("without voiceover", result["video"]["message"])
        self.assertIsNone(engine.video_assembler.last_audio_path)

    def test_tts_exception_uses_silent_fallback_and_returns_ready_video(self):
        engine = self._build_engine(
            tts_result={
                "status": "error",
                "error_type": "exception",
                "message": "TTS generation failed: timeout while contacting provider."
            },
            assemble_result={"status": "success", "message": "MP4 generated successfully.", "diagnostics": {}}
        )

        result = engine.auto_create_video("topic", "balanced", "general", 45, "female", "educational")

        self.assertEqual(result["video"]["status"], "ready")
        self.assertEqual(result["warnings"][0]["warning_code"], video_engine.TTS_FALLBACK_WARNING_CODE)
        self.assertIn("timeout", result["warnings"][0]["warning_message"])
        self.assertTrue(result.get("scene_plan"))
        self.assertTrue(result.get("caption_final"))
        self.assertTrue(result.get("hashtags"))

    def test_media_assembly_failure_still_returns_not_generated(self):
        engine = self._build_engine(
            tts_result={
                "status": "error",
                "error_type": "rate_limited",
                "message": "TTS quota/rate-limit reached (HTTP 429).",
                "http_status": 429
            },
            assemble_result={"status": "error", "message": "Video assembly failed.", "diagnostics": {}}
        )

        result = engine.auto_create_video("topic", "balanced", "general", 45, "female", "educational")

        self.assertEqual(result["video"]["status"], "not_generated")
        self.assertEqual(result["video"]["download_url"], "")
        self.assertIn("Video assembly failed.", result["video"]["message"])


if __name__ == "__main__":
    unittest.main()
