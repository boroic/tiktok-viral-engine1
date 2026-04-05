from flask import Flask, jsonify, request, render_template
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
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

UPLOAD_DIR = Path("/app")
FALLBACK_UPLOAD_DIR = Path("/tmp/app")
ALLOWED_MEDIA_EXTENSIONS = {
    "jpg", "jpeg", "png", "webp", "gif",
    "mp4", "mov", "avi", "mkv", "webm"
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

    def analyze_media_context(self, media_path: Path):
        suffix = media_path.suffix.lower().lstrip(".")
        stem = media_path.stem.replace("_", " ").replace("-", " ").strip()
        is_video = suffix in {"mp4", "mov", "avi", "mkv", "webm"}
        media_type = "video" if is_video else "image"

        keywords = [part for part in stem.split() if part]
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

    def run_from_media(self, media_path: Path):
        media_context = self.analyze_media_context(media_path)
        topic = media_context.get("topic_hint", "viral content")
        result = self.run_full_pipeline(topic=topic)
        result["media_context"] = media_context
        return result


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024
engine = TikTokViralEngine()


def resolve_upload_dir():
    for candidate in (UPLOAD_DIR, FALLBACK_UPLOAD_DIR):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except Exception:
            continue
    raise OSError("No writable upload directory available")


UPLOAD_STORAGE_DIR = resolve_upload_dir()


@app.get("/")
def home():
    return jsonify({"status": "ok", "service": "tiktok-viral-engine1"}), 200


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


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

    except Exception as e:
        logger.exception("Pipeline failed")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.post("/run-from-media")
def run_pipeline_from_media():
    try:
        upload = request.files.get("media")
        if upload is None or upload.filename is None or not upload.filename.strip():
            return jsonify({
                "status": "error",
                "message": "media file is required"
            }), 400

        filename = secure_filename(upload.filename)
        if not filename:
            return jsonify({
                "status": "error",
                "message": "invalid media filename"
            }), 400

        suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if suffix not in ALLOWED_MEDIA_EXTENSIONS:
            return jsonify({
                "status": "error",
                "message": "unsupported media type"
            }), 400

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        stored_filename = f"{timestamp}_{filename}"
        stored_path = UPLOAD_STORAGE_DIR / stored_filename
        upload.save(stored_path)

        result = engine.run_from_media(stored_path)
        return jsonify(result), 200

    except Exception as e:
        logger.exception("Pipeline from media failed")
        return jsonify({
            "status": "error",
            "message": "internal server error"
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
