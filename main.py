from flask import Flask, jsonify, request, render_template, send_file
import os
import logging
import hashlib
import threading
import subprocess
import shutil
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from urllib import request as urllib_request
from urllib import error as urllib_error
import json
import re
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from src.trend_detector import TikTokTrendDetector
from src.sound_analyzer import SoundAnalyzer
from src.video_analytics import VideoAnalytics
from src.script_generator import ScriptGenerator
from src.upload_handler import UploadHandler
from src.influencer_finder import InfluencerFinder
from src.api_client import APIManager
from src.media_extractor import MediaExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def log_ffmpeg_startup_info():
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        logger.warning("ffmpeg startup check: binary not found on PATH")
        return
    try:
        proc = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )
        if proc.returncode != 0:
            details = truncate_diagnostic_text(proc.stderr or proc.stdout or "", MAX_DIAGNOSTIC_DETAILS_LENGTH)
            logger.warning("ffmpeg startup check: found at %s but not runnable (%s)", ffmpeg_path, details)
            return
        version_line = ((proc.stdout or "").strip().splitlines() or [""])[0]
        logger.info("ffmpeg startup check: %s (%s)", ffmpeg_path, version_line)
    except Exception as exc:
        logger.warning("ffmpeg startup check failed: %s", exc)

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app"))
FALLBACK_UPLOAD_DIR = Path(os.environ.get("FALLBACK_UPLOAD_DIR", "/tmp/app"))
ALLOWED_MEDIA_EXTENSIONS = {
    "jpg", "jpeg", "png", "webp", "gif",
    "mp4", "mov", "avi", "mkv", "webm"
}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
ALLOWED_MEDIA_MIME_PREFIXES = ("image/", "video/")
MAX_MEDIA_FILES = int(os.environ.get("MAX_MEDIA_FILES", "10"))
MAX_MEDIA_FILE_BYTES = int(os.environ.get("MAX_MEDIA_FILE_BYTES", str(100 * 1024 * 1024)))
MEDIA_HASH_CACHE_SIZE = int(os.environ.get("MEDIA_HASH_CACHE_SIZE", "256"))
GENERIC_TOPIC_TOKENS = {"img", "image", "vid", "video", "wa", "dsc", "pxl", "mvimg"}
MEDIA_GROUNDING_FIELDS = ("ocr_text", "transcript_text", "keyframe_summary")
CONTENT_MODE_CAPTION_ONLY = "caption_only"
CONTENT_MODE_FULL_PACK = "full_content_pack"
SUPPORTED_CONTENT_MODES = {CONTENT_MODE_CAPTION_ONLY, CONTENT_MODE_FULL_PACK}
SUPPORTED_AUTO_DURATIONS = {30, 45, 60}
SUPPORTED_VOICE_PRESETS = {"male", "female"}
SUPPORTED_STYLE_PRESETS = {"educational", "storytelling", "checklist"}
MAX_VOICEOVER_CHARS = 3000
MAX_ARTIFACTS = int(os.environ.get("MAX_GENERATED_ARTIFACTS", "200"))
MAX_TTS_DETAILS_LENGTH = 400
MAX_DIAGNOSTIC_DETAILS_LENGTH = 300
MAX_ERROR_DETAILS_LENGTH = 500
TTS_FALLBACK_WARNING_CODE = "TTS_FALLBACK_SILENT"
RECOVERABLE_TTS_ERROR_TYPES = {"rate_limited", "http_error", "exception"}


def env_flag_enabled(name: str):
    """Return True only when env var is explicitly set to 'true' (case-insensitive)."""
    return str(os.environ.get(name, "")).strip().lower() == "true"


def sanitize_for_srt(text: str):
    normalized = re.sub(r"\s+", " ", str(text or "").strip())
    return normalized[:200]


def format_srt_timestamp(seconds_float: float):
    total_ms = max(0, int(round(seconds_float * 1_000)))
    hours = total_ms // 3_600_000
    total_ms %= 3_600_000
    minutes = total_ms // 60_000
    total_ms %= 60_000
    seconds = total_ms // 1000
    millis = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def truncate_diagnostic_text(value: str, limit: int):
    """Safely stringify any value (including None) and truncate diagnostic text."""
    text = str(value or "")
    if len(text) <= limit:
        return text
    return f"{text[:limit]} ...[truncated]"


class BaseTTSProvider:
    provider_name = "none"

    def synthesize(self, text: str, voice_preset: str, destination: Path):
        raise NotImplementedError


class OpenAITTSProvider(BaseTTSProvider):
    provider_name = "openai"

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.model = os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")

    def synthesize(self, text: str, voice_preset: str, destination: Path):
        if not self.api_key:
            return {
                "status": "unavailable",
                "provider": self.provider_name,
                "error_type": "missing_api_key",
                "message": "OPENAI_API_KEY is missing. Add it to enable AI voiceover."
            }

        voice = "alloy" if voice_preset == "male" else "nova"
        payload = json.dumps({
            "model": self.model,
            "voice": voice,
            "input": text
        }).encode("utf-8")
        req = urllib_request.Request(
            "https://api.openai.com/v1/audio/speech",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        try:
            with urllib_request.urlopen(req, timeout=45) as resp:
                audio = resp.read()
                if not audio:
                    return {
                        "status": "error",
                        "provider": self.provider_name,
                        "message": "TTS provider returned empty audio."
                    }
                destination.write_bytes(audio)
                return {
                    "status": "success",
                    "provider": self.provider_name,
                    "message": "Voiceover generated successfully."
                }
        except urllib_error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                body = ""
            if exc.code == 429:
                message = "TTS quota/rate-limit reached (HTTP 429)."
                error_type = "rate_limited"
            else:
                message = f"TTS request failed with HTTP {exc.code}."
                error_type = "http_error"
            return {
                "status": "error",
                "provider": self.provider_name,
                "error_type": error_type,
                "message": message,
                "http_status": exc.code,
                "details": body[:MAX_TTS_DETAILS_LENGTH]
            }
        except Exception as exc:
            return {
                "status": "error",
                "provider": self.provider_name,
                "error_type": "exception",
                "message": f"TTS generation failed: {exc}"
            }


class FacelessVideoAssembler:
    def __init__(self):
        self.ffmpeg = shutil.which("ffmpeg")

    def ffmpeg_diagnostics(self):
        """Check ffmpeg presence/runtime and return lightweight diagnostics."""
        if not self.ffmpeg:
            return {
                "available": False,
                "path": "",
                "message": "ffmpeg binary not found on PATH."
            }
        try:
            proc = subprocess.run(
                [self.ffmpeg, "-version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5
            )
            if proc.returncode != 0:
                return {
                    "available": False,
                    "path": self.ffmpeg,
                    "message": "ffmpeg binary found but not runnable.",
                    "details": truncate_diagnostic_text((proc.stderr or proc.stdout or ""), MAX_DIAGNOSTIC_DETAILS_LENGTH)
                }
            stdout_text = (proc.stdout or "").strip()
            lines = stdout_text.splitlines()
            if not lines:
                lines = [""]
            first_line = lines[0]
            return {
                "available": True,
                "path": self.ffmpeg,
                "version": first_line
            }
        except Exception as exc:
            return {
                "available": False,
                "path": self.ffmpeg or "",
                "message": f"ffmpeg check failed: {exc}"
            }

    def ffmpeg_available(self):
        return bool(self.ffmpeg_diagnostics().get("available"))

    def _escape_subtitle_filter_path(self, subtitle_path: Path):
        raw = str(subtitle_path.resolve())
        escaped = raw.replace("\\", "\\\\")
        escaped = escaped.replace(":", r"\:")
        escaped = escaped.replace("'", r"\'")
        escaped = escaped.replace(",", r"\,")
        escaped = escaped.replace("[", r"\[")
        escaped = escaped.replace("]", r"\]")
        return escaped

    def build_subtitles(self, scene_plan, duration_seconds: int, destination: Path):
        lines = []
        safe_scenes = scene_plan if isinstance(scene_plan, list) and scene_plan else []
        if not safe_scenes:
            safe_scenes = [{
                "scene": 1,
                "voiceover_text": "Hook, value, and call to action."
            }]
        scene_duration = float(duration_seconds) / float(len(safe_scenes))
        cursor = 0.0
        for idx, scene in enumerate(safe_scenes, 1):
            start = cursor
            end = duration_seconds if idx == len(safe_scenes) else min(duration_seconds, cursor + scene_duration)
            cursor = end
            text = sanitize_for_srt(scene.get("voiceover_text", "")) or f"Scene {idx}"
            lines.append(str(idx))
            lines.append(f"{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}")
            lines.append(text)
            lines.append("")
        destination.write_text("\n".join(lines), encoding="utf-8")

    def assemble(self, duration_seconds: int, subtitle_path: Path, output_path: Path, audio_path: Path = None):
        ffmpeg_diag = self.ffmpeg_diagnostics()
        if not ffmpeg_diag.get("available"):
            return {
                "status": "unavailable",
                "message": "ffmpeg is missing or not runnable in this environment. Ensure deployment installs ffmpeg.",
                "diagnostics": ffmpeg_diag
            }

        safe_subtitle_path = self._escape_subtitle_filter_path(subtitle_path)
        filter_expr = (
            f"subtitles={safe_subtitle_path}:force_style="
            "'Fontsize=44,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,MarginV=150'"
        )
        cmd = [
            self.ffmpeg,
            "-y",
            "-f", "lavfi",
            "-i", f"color=c=0x111111:s=1080x1920:d={duration_seconds}",
        ]
        if audio_path and audio_path.exists():
            cmd.extend(["-i", str(audio_path)])
        else:
            cmd.extend(["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={duration_seconds}"])
        cmd.extend([
            "-vf", filter_expr,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            str(output_path)
        ])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
            if proc.returncode != 0:
                return {
                    "status": "error",
                    "message": "Video assembly failed.",
                    "diagnostics": ffmpeg_diag,
                    "details": truncate_diagnostic_text((proc.stderr or proc.stdout or ""), MAX_ERROR_DETAILS_LENGTH)
                }
            return {
                "status": "success",
                "message": "MP4 generated successfully.",
                "diagnostics": ffmpeg_diag
            }
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Video assembly failed: {exc}",
                "diagnostics": ffmpeg_diag
            }


class TikTokViralEngine:
    def __init__(self):
        logger.info("Initializing TikTokViralEngine")
        self.trend_detector = TikTokTrendDetector()
        self.sound_analyzer = SoundAnalyzer()
        self.video_analytics = VideoAnalytics()
        self.script_gen = ScriptGenerator()
        self.uploader = UploadHandler()
        self.influencer_finder = InfluencerFinder()
        self.api_manager = APIManager()
        self.max_topic_words = 8
        self.media_result_cache = OrderedDict()
        self.media_result_cache_size = MEDIA_HASH_CACHE_SIZE
        self.cache_lock = threading.Lock()
        self.tts_provider = OpenAITTSProvider()
        self.video_assembler = FacelessVideoAssembler()
        self.generated_artifacts = OrderedDict()
        self.artifact_lock = threading.Lock()

    def analyze_media_context(self, media_path: Path):
        suffix = media_path.suffix.lower().lstrip(".")
        stem = media_path.stem.replace("_", " ").replace("-", " ").strip()
        is_video = suffix in ALLOWED_VIDEO_EXTENSIONS
        media_type = "video" if is_video else "image"

        keywords = [part for part in stem.split() if part and not part.isdigit()]
        keywords = [part for part in keywords if part.lower() not in GENERIC_TOPIC_TOKENS]
        topic = " ".join(keywords[: self.max_topic_words]) if keywords else f"{media_type} content"

        return {
            "media_type": media_type,
            "extension": suffix,
            "filename": media_path.name,
            "topic_hint": topic,
            "stored_path": str(media_path)
        }

    def run_full_pipeline(
        self,
        topic: str = "viral_trends",
        tone: str = "balanced",
        target_audience: str = "general",
        media_grounding=None,
        content_mode: str = CONTENT_MODE_CAPTION_ONLY
    ):
        logger.info(f"Running pipeline for topic={topic}")
        normalized_mode = self._normalize_content_mode(content_mode)

        health = self.api_manager.health_check()
        trends = self.trend_detector.fetch_trends()
        sounds = self.sound_analyzer.analyze_trending_sounds()

        script = self.api_manager.openai.generate_script(
            topic,
            tone=tone,
            target_audience=target_audience,
            media_grounding=media_grounding
        )
        hashtags = self.api_manager.openai.generate_hashtags(
            topic,
            tone=tone,
            target_audience=target_audience,
            media_grounding=media_grounding
        )
        captions = self.api_manager.openai.generate_captions(
            topic,
            tone=tone,
            target_audience=target_audience,
            media_grounding=media_grounding
        )
        full_content_pack = None
        if normalized_mode == CONTENT_MODE_FULL_PACK:
            full_content_pack = self.api_manager.openai.generate_full_content_pack(
                topic,
                tone=tone,
                target_audience=target_audience,
                media_grounding=media_grounding,
                script=script,
                hashtags=hashtags,
                captions=captions
            )

        analytics = self.video_analytics.predict_performance(script)

        seed = trends[0] if isinstance(trends, list) and len(trends) > 0 else topic
        influencers = self.influencer_finder.find_collaborators(seed)

        result = {
            "status": "success",
            "api_health": health,
            "topic": topic,
            "tone": tone,
            "target_audience": target_audience,
            "script": script,
            "hashtags": hashtags,
            "captions": captions,
            "predicted_analytics": analytics,
            "influencers": influencers,
            "trends": trends,
            "sounds": sounds,
            "content_mode": normalized_mode
        }
        if full_content_pack is not None:
            result["full_content_pack"] = full_content_pack
        return result

    def _get_cached_media_result(self, cache_key: str):
        with self.cache_lock:
            if cache_key not in self.media_result_cache:
                return None
            self.media_result_cache.move_to_end(cache_key)
            return deepcopy(self.media_result_cache[cache_key])

    def _set_cached_media_result(self, cache_key: str, result):
        with self.cache_lock:
            self.media_result_cache[cache_key] = deepcopy(result)
            self.media_result_cache.move_to_end(cache_key)
            while len(self.media_result_cache) > self.media_result_cache_size:
                self.media_result_cache.popitem(last=False)

    def _normalize_optional_text(self, value, max_len=1200):
        if not isinstance(value, str):
            return ""
        compact = " ".join(value.split()).strip()
        return compact[:max_len]

    def _normalize_content_mode(self, value):
        if not isinstance(value, str):
            return CONTENT_MODE_CAPTION_ONLY
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_CONTENT_MODES:
            return CONTENT_MODE_CAPTION_ONLY
        return normalized

    def _normalize_duration(self, duration):
        try:
            parsed = int(duration)
        except Exception:
            parsed = 45
        if parsed not in SUPPORTED_AUTO_DURATIONS:
            return 45
        return parsed

    def _normalize_voice_preset(self, preset):
        value = str(preset or "female").strip().lower()
        if value not in SUPPORTED_VOICE_PRESETS:
            return "female"
        return value

    def _normalize_style_preset(self, preset):
        value = str(preset or "educational").strip().lower()
        if value not in SUPPORTED_STYLE_PRESETS:
            return "educational"
        return value

    def _build_scene_plan(self, script, duration_seconds: int, style_preset: str):
        hook = ""
        cta = ""
        body_lines = []
        if isinstance(script, dict):
            hook = self._normalize_optional_text(script.get("hook", ""), max_len=220)
            cta = self._normalize_optional_text(script.get("cta", ""), max_len=220)
            body_value = script.get("body", [])
            if isinstance(body_value, list):
                body_lines = [self._normalize_optional_text(line, max_len=220) for line in body_value if str(line or "").strip()]
            elif isinstance(body_value, str) and body_value.strip():
                body_lines = [self._normalize_optional_text(body_value, max_len=220)]
        steps = []
        if hook:
            steps.append(hook)
        steps.extend(body_lines[:3])
        if cta:
            steps.append(cta)
        if not steps:
            steps = ["Start with a clear promise.", "Deliver 3 concise value beats.", "Close with a direct CTA."]

        scene_count = max(3, min(6, len(steps)))
        if style_preset == "checklist":
            scene_count = max(scene_count, 4)
        elif style_preset == "storytelling":
            scene_count = max(scene_count, 5)
        per_scene = max(4, int(duration_seconds / scene_count))

        style_templates = {
            "educational": [
                "Bold title card + kinetic text reveal",
                "Solid background with key concept text",
                "Checklist bullets with subtle zoom",
                "Proof/result card with big numbers",
                "CTA screen with save/follow prompt",
            ],
            "storytelling": [
                "Hook statement on dark gradient background",
                "Set-up beat with animated caption blocks",
                "Conflict/insight beat with motion text",
                "Resolution beat with highlighted takeaway",
                "CTA ending card with brand color accent",
            ],
            "checklist": [
                "Checklist title card",
                "Item 1 card with kinetic numbering",
                "Item 2 card with kinetic numbering",
                "Item 3 card with kinetic numbering",
                "Final CTA card",
            ]
        }
        visuals = style_templates.get(style_preset, style_templates["educational"])
        plan = []
        cursor = 0
        for idx in range(scene_count):
            end = duration_seconds if idx == scene_count - 1 else min(duration_seconds, cursor + per_scene)
            text_value = steps[idx] if idx < len(steps) else steps[-1]
            plan.append({
                "scene": idx + 1,
                "start_second": cursor,
                "end_second": end,
                "visual_template": visuals[idx % len(visuals)],
                "on_screen_text": text_value,
                "voiceover_text": text_value
            })
            cursor = end
        return plan

    def _register_artifact(self, artifact_id: str, output_path: Path):
        with self.artifact_lock:
            self.generated_artifacts[artifact_id] = str(output_path)
            self.generated_artifacts.move_to_end(artifact_id)
            while len(self.generated_artifacts) > MAX_ARTIFACTS:
                _, old_path_str = self.generated_artifacts.popitem(last=False)
                old_path = Path(old_path_str)
                if old_path.exists():
                    try:
                        old_path.unlink()
                    except Exception:
                        pass

    def get_artifact_path(self, artifact_id: str):
        with self.artifact_lock:
            path_str = self.generated_artifacts.get(artifact_id)
            if not path_str:
                return None
            self.generated_artifacts.move_to_end(artifact_id)
        path = Path(path_str)
        return path if path.exists() else None

    def auto_create_video(
        self,
        topic: str,
        tone: str,
        target_audience: str,
        duration,
        voice_preset: str,
        style_preset: str
    ):
        normalized_topic = self._normalize_optional_text(topic, max_len=120) or "viral trends"
        normalized_tone = self._normalize_optional_text(tone, max_len=40) or "balanced"
        normalized_audience = self._normalize_optional_text(target_audience, max_len=80) or "general"
        normalized_duration = self._normalize_duration(duration)
        normalized_voice = self._normalize_voice_preset(voice_preset)
        normalized_style = self._normalize_style_preset(style_preset)

        script = self.api_manager.openai.generate_script(
            normalized_topic,
            tone=normalized_tone,
            target_audience=normalized_audience
        )
        hashtags = self.api_manager.openai.generate_hashtags(
            normalized_topic,
            tone=normalized_tone,
            target_audience=normalized_audience
        )
        captions = self.api_manager.openai.generate_captions(
            normalized_topic,
            tone=normalized_tone,
            target_audience=normalized_audience
        )
        pack = self.api_manager.openai.generate_full_content_pack(
            normalized_topic,
            tone=normalized_tone,
            target_audience=normalized_audience,
            script=script,
            hashtags=hashtags,
            captions=captions
        )
        caption_final = self._normalize_optional_text(pack.get("caption_final", ""), max_len=1200)
        if not caption_final:
            caption_final = self._normalize_optional_text(" ".join(captions) if isinstance(captions, list) else captions, max_len=1200)

        scene_plan = self._build_scene_plan(script, normalized_duration, normalized_style)
        voiceover_script = self._normalize_optional_text(pack.get("voiceover_script", ""), max_len=MAX_VOICEOVER_CHARS)
        if not voiceover_script:
            voiceover_lines = []
            for scene in scene_plan:
                text_line = scene.get("voiceover_text", "")
                if text_line:
                    voiceover_lines.append(text_line)
            voiceover_script = "\n".join(voiceover_lines)
            voiceover_script = voiceover_script[:MAX_VOICEOVER_CHARS]

        artifact_id = uuid4().hex
        base_dir = UPLOAD_STORAGE_DIR / "generated"
        base_dir.mkdir(parents=True, exist_ok=True)
        subtitle_path = base_dir / f"{artifact_id}.srt"
        audio_path = base_dir / f"{artifact_id}.mp3"
        output_path = base_dir / f"{artifact_id}.mp4"

        force_disable_tts = env_flag_enabled("DISABLE_TTS")
        if force_disable_tts:
            tts_result = {
                "status": "unavailable",
                "provider": self.tts_provider.provider_name,
                "error_type": "tts_disabled",
                "message": "Voiceover disabled via DISABLE_TTS=true."
            }
        else:
            tts_result = self.tts_provider.synthesize(voiceover_script, normalized_voice, audio_path)
        tts_error_type = str(tts_result.get("error_type") or "")
        tts_message = self._normalize_optional_text(tts_result.get("message", ""), max_len=160) or "TTS unavailable"
        fallback_warning = None
        if tts_result.get("status") != "success":
            logger.warning(
                "Auto-create video: TTS failure detected (type=%s, status=%s): %s",
                tts_error_type or "unknown",
                tts_result.get("http_status", "n/a"),
                tts_message
            )
            if tts_error_type in RECOVERABLE_TTS_ERROR_TYPES:
                fallback_warning = {
                    "warning_code": TTS_FALLBACK_WARNING_CODE,
                    "warning_message": f"Video generated without voiceover due to TTS issue: {tts_message}"
                }
                logger.info("Auto-create video: fallback mode activated (silent render)")
        self.video_assembler.build_subtitles(scene_plan, normalized_duration, subtitle_path)
        video_result = self.video_assembler.assemble(
            duration_seconds=normalized_duration,
            subtitle_path=subtitle_path,
            output_path=output_path,
            audio_path=audio_path if tts_result.get("status") == "success" else None
        )

        if video_result.get("status") == "success":
            self._register_artifact(artifact_id, output_path)
            mp4_url = f"/artifacts/{artifact_id}/download"
            video_status = "ready"
            if fallback_warning:
                video_message = fallback_warning["warning_message"]
            elif tts_result.get("status") != "success":
                video_message = "Voiceover disabled (no API credit). Generated silent video."
            else:
                video_message = "Faceless video generated successfully."
            logger.info("Auto-create video: final render success (artifact_id=%s, silent=%s)", artifact_id, tts_result.get("status") != "success")
        else:
            mp4_url = ""
            video_status = "not_generated"
            missing = []
            video_message_text = video_result.get("message", "Video assembly unavailable")
            if video_message_text:
                missing.append(video_message_text)
            if tts_result.get("status") != "success":
                tts_message = tts_result.get("message", "TTS unavailable")
                if tts_message:
                    missing.append(tts_message)
            video_message = " ".join([str(part) for part in missing if part]).strip()
            logger.error("Auto-create video: final render failed: %s", video_message_text)

        guidance = None
        if tts_result.get("status") != "success":
            if tts_result.get("error_type") == "missing_api_key":
                guidance = (
                    "Voiceover is disabled due to missing API credit/key. "
                    "Set OPENAI_API_KEY and ensure TTS access to enable voice generation. "
                    "Script, scene plan, caption, and hashtags were still generated."
                )
            elif tts_result.get("error_type") == "tts_disabled":
                guidance = (
                    "Voiceover was explicitly disabled by DISABLE_TTS=true. "
                    "Set DISABLE_TTS=false to re-enable TTS. "
                    "Script, scene plan, caption, and hashtags were still generated."
                )
            elif tts_result.get("error_type") == "rate_limited":
                guidance = (
                    "AI voiceover hit TTS quota/rate-limit (HTTP 429). "
                    "Retry later or increase quota. Script, scene plan, caption, and hashtags were still generated."
                )
            else:
                guidance = (
                    "AI voiceover is unavailable. Verify OPENAI_API_KEY and TTS provider access. "
                    "Script, scene plan, caption, and hashtags were still generated."
                )

        return {
            "status": "success",
            "mode": "auto_create_video",
            "topic": normalized_topic,
            "tone": normalized_tone,
            "target_audience": normalized_audience,
            "duration": normalized_duration,
            "voice_preset": normalized_voice,
            "style_preset": normalized_style,
            "script": script,
            "scene_plan": scene_plan,
            "voiceover_script": voiceover_script,
            "captions": captions,
            "caption_final": caption_final,
            "hashtags": hashtags,
            "full_content_pack": pack,
            "video": {
                "status": video_status,
                "message": video_message,
                "artifact_id": artifact_id if mp4_url else "",
                "download_url": mp4_url,
                "format": "mp4",
                "aspect_ratio": "9:16",
                "subtitles_burned": video_result.get("status") == "success",
                "diagnostics": video_result.get("diagnostics", {})
            },
            "tts": tts_result,
            "warnings": [fallback_warning] if fallback_warning else [],
            "guidance": guidance
        }

    def run_from_media(
        self,
        media_path: Path,
        media_hash: str = "",
        tone: str = "balanced",
        target_audience: str = "general",
        media_grounding=None,
        content_mode: str = CONTENT_MODE_CAPTION_ONLY
    ):
        media_context = self.analyze_media_context(media_path)
        topic = media_context.get("topic_hint", "viral content")
        normalized_grounding = {}
        if isinstance(media_grounding, dict):
            for field in MEDIA_GROUNDING_FIELDS:
                normalized_grounding[field] = self._normalize_optional_text(media_grounding.get(field, ""))

        # Ground topic in available media-derived text while gracefully falling back.
        topic_candidates = [
            normalized_grounding.get("keyframe_summary", ""),
            normalized_grounding.get("ocr_text", ""),
            normalized_grounding.get("transcript_text", ""),
            topic
        ]
        for candidate in topic_candidates:
            words = str(candidate).split()
            if words:
                topic = " ".join(words[: self.max_topic_words])
                break

        grounding_key = "\x1f".join([normalized_grounding.get(field, "") for field in MEDIA_GROUNDING_FIELDS])
        grounding_fingerprint = hashlib.sha256(grounding_key.encode("utf-8")).hexdigest() if grounding_key else ""
        normalized_mode = self._normalize_content_mode(content_mode)
        cache_key = (
            "\x1f".join([media_hash, topic, tone, target_audience, grounding_fingerprint, normalized_mode])
            if media_hash else ""
        )

        if cache_key:
            cached = self._get_cached_media_result(cache_key)
            if cached is not None:
                cached["media_context"] = media_context
                cached["media_hash"] = media_hash
                cached["cache"] = {"hit": True}
                return cached

        result = self.run_full_pipeline(
            topic=topic,
            tone=tone,
            target_audience=target_audience,
            media_grounding=normalized_grounding,
            content_mode=normalized_mode
        )
        if cache_key:
            self._set_cached_media_result(cache_key, result)
        result["media_context"] = media_context
        result["media_grounding"] = normalized_grounding
        result["media_hash"] = media_hash
        result["cache"] = {"hit": False}
        return result


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024
engine = TikTokViralEngine()
media_extractor = MediaExtractor()


def resolve_upload_dir():
    for candidate in (UPLOAD_DIR, FALLBACK_UPLOAD_DIR):
        probe = candidate / ".write_test"
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe.write_text("ok", encoding="utf-8")
            return candidate
        except Exception:
            continue
        finally:
            try:
                probe.unlink(missing_ok=True)
            except Exception:
                pass
    raise OSError("No writable upload directory available")


def extract_extension(filename: str):
    return Path(filename).suffix.lower().lstrip(".")


def format_bytes(num_bytes: int):
    units = ["B", "KB", "MB", "GB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024


def get_upload_size_bytes(upload):
    if upload.content_length is not None:
        return int(upload.content_length)
    stream = upload.stream
    current_pos = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(current_pos)
    return int(size)


def save_upload_and_hash(upload, destination: Path):
    hasher = hashlib.sha256()
    total_bytes = 0
    upload.stream.seek(0)
    try:
        with destination.open("wb") as target:
            while True:
                chunk = upload.stream.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_MEDIA_FILE_BYTES:
                    raise ValueError(
                        f"file too large ({format_bytes(total_bytes)} > {format_bytes(MAX_MEDIA_FILE_BYTES)})"
                    )
                hasher.update(chunk)
                target.write(chunk)
    except Exception:
        try:
            destination.unlink(missing_ok=True)
        except Exception:
            pass
        raise
    return hasher.hexdigest()


def collect_media_uploads():
    uploads = request.files.getlist("media")
    if not uploads:
        uploads = request.files.getlist("media[]")
    if not uploads:
        single = request.files.get("media")
        if single is not None:
            uploads = [single]
    return [u for u in uploads if u is not None]


def cleanup_stored_files(paths):
    for stored_path in paths:
        if stored_path.exists():
            try:
                stored_path.unlink()
            except Exception as cleanup_error:
                logger.warning(
                    "Failed to clean up uploaded media at %s: %s",
                    stored_path,
                    cleanup_error
                )


UPLOAD_STORAGE_DIR = resolve_upload_dir()


@app.get("/")
def home():
    return jsonify({"status": "ok", "service": "tiktok-viral-engine1"}), 200


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.errorhandler(RequestEntityTooLarge)
def handle_request_too_large(_error):
    max_size = app.config.get("MAX_CONTENT_LENGTH", 0)
    return jsonify({
        "status": "error",
        "message": f"request payload too large (max {format_bytes(max_size)})"
    }), 413


@app.get("/app")
def web_app():
    return render_template("index.html")


@app.post("/run")
def run_pipeline():
    try:
        data = request.get_json(silent=True) or {}
        topic = data.get("topic", "viral_trends")
        tone = data.get("tone", "balanced")
        target_audience = data.get("target_audience", "general")
        content_mode = data.get("content_mode", CONTENT_MODE_CAPTION_ONLY)

        if not isinstance(topic, str) or not topic.strip():
            return jsonify({
                "status": "error",
                "message": "topic must be a non-empty string"
            }), 400
        if not isinstance(tone, str):
            tone = "balanced"
        if not isinstance(target_audience, str):
            target_audience = "general"

        result = engine.run_full_pipeline(
            topic=topic.strip(),
            tone=tone.strip() or "balanced",
            target_audience=target_audience.strip() or "general",
            content_mode=content_mode if isinstance(content_mode, str) else CONTENT_MODE_CAPTION_ONLY
        )
        return jsonify(result), 200

    except Exception:
        logger.exception("Pipeline failed")
        return jsonify({
            "status": "error",
            "message": "internal server error"
        }), 500


@app.post("/auto-create-video")
def auto_create_video():
    try:
        data = request.get_json(silent=True) or {}
        topic = data.get("topic", "viral trends")
        tone = data.get("tone", "balanced")
        target_audience = data.get("target_audience", "general")
        duration = data.get("duration", 45)
        voice_preset = data.get("voice_preset", "female")
        style_preset = data.get("style_preset", "educational")

        if not isinstance(topic, str) or not topic.strip():
            return jsonify({
                "status": "error",
                "message": "topic must be a non-empty string"
            }), 400

        result = engine.auto_create_video(
            topic=topic,
            tone=tone if isinstance(tone, str) else "balanced",
            target_audience=target_audience if isinstance(target_audience, str) else "general",
            duration=duration,
            voice_preset=voice_preset if isinstance(voice_preset, str) else "female",
            style_preset=style_preset if isinstance(style_preset, str) else "educational"
        )
        return jsonify(result), 200
    except Exception:
        logger.exception("Auto-create video failed")
        return jsonify({
            "status": "error",
            "message": "internal server error"
        }), 500


@app.get("/artifacts/<artifact_id>/download")
def download_artifact(artifact_id):
    safe_id = str(artifact_id or "").strip().lower()
    if not re.fullmatch(r"[a-f0-9]{32}", safe_id):
        return jsonify({"status": "error", "message": "invalid artifact id"}), 400
    path = engine.get_artifact_path(safe_id)
    if path is None:
        return jsonify({"status": "error", "message": "artifact not found"}), 404
    return send_file(
        path,
        mimetype="video/mp4",
        as_attachment=True,
        download_name=f"auto-video-{safe_id}.mp4"
    )


@app.post("/run-from-media")
def run_pipeline_from_media():
    stored_paths = []
    try:
        uploads = collect_media_uploads()
        if not uploads:
            return jsonify({
                "status": "error",
                "message": "media file is required"
            }), 400

        if len(uploads) > MAX_MEDIA_FILES:
            return jsonify({
                "status": "error",
                "message": f"too many files (max {MAX_MEDIA_FILES})"
            }), 400

        tone = request.form.get("tone", "balanced")
        target_audience = request.form.get("target_audience", "general")
        content_mode = request.form.get("content_mode", CONTENT_MODE_CAPTION_ONLY)
        if not isinstance(tone, str):
            tone = "balanced"
        if not isinstance(target_audience, str):
            target_audience = "general"
        if not isinstance(content_mode, str):
            content_mode = CONTENT_MODE_CAPTION_ONLY

        manual_overrides = {}
        for field in MEDIA_GROUNDING_FIELDS:
            manual_overrides[field] = request.form.get(field, "")

        validation_errors = []
        normalized_uploads = []
        for idx, upload in enumerate(uploads):
            raw_filename = upload.filename or ""
            filename = secure_filename(raw_filename)
            if not filename:
                validation_errors.append(f"file #{idx + 1}: invalid media filename")
                continue

            suffix = extract_extension(filename)
            if suffix not in ALLOWED_MEDIA_EXTENSIONS:
                validation_errors.append(
                    f"{filename}: unsupported type '.{suffix or 'unknown'}'"
                )
                continue

            mimetype = (upload.mimetype or "").lower()
            if mimetype and not mimetype.startswith(ALLOWED_MEDIA_MIME_PREFIXES):
                validation_errors.append(
                    f"{filename}: invalid media mimetype '{mimetype}'"
                )
                continue

            size_bytes = get_upload_size_bytes(upload)
            if size_bytes > MAX_MEDIA_FILE_BYTES:
                validation_errors.append(
                    f"{filename}: file too large ({format_bytes(size_bytes)} > {format_bytes(MAX_MEDIA_FILE_BYTES)})"
                )
                continue

            normalized_uploads.append((upload, filename))

        if validation_errors:
            return jsonify({
                "status": "error",
                "message": "media validation failed",
                "errors": validation_errors
            }), 400

        results = []
        for upload, filename in normalized_uploads:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            stored_filename = f"{timestamp}_{uuid4().hex}_{filename}"
            stored_path = UPLOAD_STORAGE_DIR / stored_filename
            stored_paths.append(stored_path)
            try:
                media_hash = save_upload_and_hash(upload, stored_path)
            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": "media validation failed",
                    "errors": [
                        f"{filename}: file too large (max {format_bytes(MAX_MEDIA_FILE_BYTES)})"
                    ]
                }), 400
            extracted_grounding = media_extractor.extract_media_signals(stored_path)
            media_grounding = {}
            for field in MEDIA_GROUNDING_FIELDS:
                override = manual_overrides.get(field, "")
                media_grounding[field] = override if override else extracted_grounding.get(field, "")

            result = (
                engine.run_from_media(
                    stored_path,
                    media_hash=media_hash,
                    tone=tone.strip() or "balanced",
                    target_audience=target_audience.strip() or "general",
                    media_grounding=media_grounding,
                    content_mode=content_mode.strip().lower() or CONTENT_MODE_CAPTION_ONLY
                )
            )
            result["media_extraction"] = {
                "status": "signals_found" if any(media_grounding.get(field, "") for field in MEDIA_GROUNDING_FIELDS) else "signals_not_found",
                "signals_detected": {
                    field: bool(media_grounding.get(field, ""))
                    for field in MEDIA_GROUNDING_FIELDS
                }
            }
            results.append(result)

        if len(results) == 1:
            return jsonify(results[0]), 200

        return jsonify({
            "status": "success",
            "count": len(results),
            "results": results
        }), 200

    except Exception as e:
        logger.exception("Pipeline from media failed")
        return jsonify({
            "status": "error",
            "message": "internal server error"
        }), 500
    finally:
        cleanup_stored_files(stored_paths)


if __name__ == "__main__":
    log_ffmpeg_startup_info()
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
