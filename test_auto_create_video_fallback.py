import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess

import main


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
        self.upload_dir_patch = patch.object(main, "UPLOAD_STORAGE_DIR", Path(self.tmp_dir.name))
        self.upload_dir_patch.start()

    def tearDown(self):
        self.upload_dir_patch.stop()
        self.tmp_dir.cleanup()

    def _build_engine(self, tts_result, assemble_result):
        engine = main.TikTokViralEngine()
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
        self.assertEqual(result["video"]["status"], "generated")
        self.assertTrue(result["video"]["download_url"])
        self.assertEqual(result["warnings"][0]["warning_code"], main.TTS_FALLBACK_WARNING_CODE)
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

        self.assertEqual(result["video"]["status"], "generated")
        self.assertEqual(result["warnings"][0]["warning_code"], main.TTS_FALLBACK_WARNING_CODE)
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
        self.assertEqual(result["status"], "success")


class FacelessVideoAssemblerFallbackCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)
        self.subtitle_path = self.tmp_path / "subtitles.srt"
        self.subtitle_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
        self.output_path = self.tmp_path / "output.mp4"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _build_assembler(self, mode):
        assembler = main.FacelessVideoAssembler()
        assembler.ffmpeg = "/usr/bin/ffmpeg"
        assembler.silent_fallback_mode = mode
        return assembler

    @patch.object(main.FacelessVideoAssembler, "ffmpeg_diagnostics", return_value={"available": True, "path": "/usr/bin/ffmpeg"})
    @patch("main.subprocess.run")
    def test_tts_429_fallback_video_only_path_success(self, mock_run, _mock_diag):
        mock_run.return_value = subprocess.CompletedProcess(args=["ffmpeg"], returncode=0, stdout="", stderr="")
        assembler = self._build_assembler("video_only")

        result = assembler.assemble(45, self.subtitle_path, self.output_path, audio_path=None)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["fallback_stage"], "video-only")
        cmd = mock_run.call_args[0][0]
        cmd_text = " ".join(cmd)
        self.assertIn("-an", cmd)
        self.assertNotIn("anullsrc", cmd_text)
        self.assertIn("+faststart", cmd)
        self.assertIn("libx264", cmd)
        self.assertIn("yuv420p", cmd)

    @patch.object(main.FacelessVideoAssembler, "ffmpeg_diagnostics", return_value={"available": True, "path": "/usr/bin/ffmpeg"})
    @patch("main.subprocess.run")
    def test_tts_429_fallback_silent_audio_mux_path_success(self, mock_run, _mock_diag):
        mock_run.return_value = subprocess.CompletedProcess(args=["ffmpeg"], returncode=0, stdout="", stderr="")
        assembler = self._build_assembler("silent_audio_mux")

        result = assembler.assemble(45, self.subtitle_path, self.output_path, audio_path=None)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["fallback_stage"], "silent-audio-mux")
        cmd = mock_run.call_args[0][0]
        cmd_text = " ".join(cmd)
        self.assertIn("anullsrc=r=44100:cl=stereo:d=45.0", cmd_text)
        self.assertIn("-shortest", cmd)
        self.assertIn("aac", cmd)
        self.assertIn("+faststart", cmd)

    @patch.object(main.FacelessVideoAssembler, "ffmpeg_diagnostics", return_value={"available": True, "path": "/usr/bin/ffmpeg"})
    @patch("main.subprocess.run")
    def test_missing_scene_input_fails(self, mock_run, _mock_diag):
        assembler = self._build_assembler("silent_audio_mux")
        missing_subtitle = self.tmp_path / "missing.srt"

        result = assembler.assemble(45, missing_subtitle, self.output_path, audio_path=None)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Video assembly failed.")
        self.assertIn("Missing required subtitle input.", result["details"])
        self.assertEqual(result["fallback_stage"], "validation")
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
