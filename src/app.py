"""
TikTok Viral Engine - Flask REST API
HTTP server for Railway deployment
"""

import logging
import threading
from flask import Flask, jsonify, request
from src.trend_detector import TikTokTrendDetector

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Thread-safe storage for generated videos
_videos = []
_videos_lock = threading.Lock()


@app.route("/")
def index():
    return jsonify({"status": "ok", "service": "TikTok Viral Engine"})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/generate", methods=["POST"])
def generate():
    """Run content pipeline and return results"""
    from main import TikTokViralEngine
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "viral_trends")
    try:
        engine = TikTokViralEngine()
        result = engine.run_full_pipeline(topic=topic)
        if result.get("status") == "success":
            with _videos_lock:
                _videos.append(result)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ /generate failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/videos")
def videos():
    """Return all generated videos"""
    with _videos_lock:
        return jsonify({"videos": list(_videos)})


@app.route("/trends")
def trends():
    """Return current trending hashtags"""
    try:
        detector = TikTokTrendDetector()
        trend_list = detector.fetch_trends()
        return jsonify({"trends": trend_list})
    except Exception as e:
        logger.error(f"❌ /trends failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
