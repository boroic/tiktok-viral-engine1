from flask import Flask, jsonify, request, render_template
import os
import logging
import hashlib
import threading
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from src.trend_detector import TikTokTrendDetector
from src.sound_analyzer import SoundAnalyzer
from src.video_analytics import VideoAnalytics
from src.script_generator import ScriptGenerator
from src.upload_handler import UploadHandler
from src.influencer_finder import InfluencerFinder
from src.api_client import APIManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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

    def run_full_pipeline(self, topic: str = "viral_trends"):
        logger.info(f"Running pipeline for topic={topic}")

        health = self.api_manager.health_check()
        trends = self.trend_detector.fetch_trends()
        sounds = self.sound_analyzer.analyze_trending_sounds()

        script = self.api_manager.openai.generate_script(topic)
        hashtags = self.api_manager.openai.generate_hashtags(topic)
        captions = self.api_manager.openai.generate_captions(topic)

        analytics = self.video_analytics.predict_performance(script)

        seed = trends[0] if isinstance(trends, list) and len(trends) > 0 else topic
        influencers = self.influencer_finder.find_collaborators(seed)

        return {
            "status": "success",
            "api_health": health,
            "topic": topic,
            "script": script,
            "hashtags": hashtags,
            "captions": captions,
            "predicted_analytics": analytics,
            "influencers": influencers,
            "trends": trends,
            "sounds": sounds
        }

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

    def run_from_media(self, media_path: Path, media_hash: str = ""):
        media_context = self.analyze_media_context(media_path)
        topic = media_context.get("topic_hint", "viral content")
        cache_key = f"{media_hash}:{topic}" if media_hash else ""

        if cache_key:
            cached = self._get_cached_media_result(cache_key)
            if cached is not None:
                cached["media_context"] = media_context
                cached["media_hash"] = media_hash
                cached["cache"] = {"hit": True}
                return cached

        result = self.run_full_pipeline(topic=topic)
        if cache_key:
            self._set_cached_media_result(cache_key, result)
        result["media_context"] = media_context
        result["media_hash"] = media_hash
        result["cache"] = {"hit": False}
        return result


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024
engine = TikTokViralEngine()


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

        if not isinstance(topic, str) or not topic.strip():
            return jsonify({
                "status": "error",
                "message": "topic must be a non-empty string"
            }), 400

        result = engine.run_full_pipeline(topic=topic.strip())
        return jsonify(result), 200

    except Exception:
        logger.exception("Pipeline failed")
        return jsonify({
            "status": "error",
            "message": "internal server error"
        }), 500


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
            except ValueError as validation_error:
                return jsonify({
                    "status": "error",
                    "message": "media validation failed",
                    "errors": [f"{filename}: {validation_error}"]
                }), 400
            results.append(engine.run_from_media(stored_path, media_hash=media_hash))

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
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
