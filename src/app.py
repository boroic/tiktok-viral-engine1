"""
TikTok Viral Engine - Flask REST API
Provides HTTP endpoints for Railway deployment
"""

import logging
import threading
from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Thread-safe list of generated videos
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
    """Run the full content pipeline and return results."""
    from main import TikTokViralEngine

    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "viral_trends")

    engine = TikTokViralEngine()
    result = engine.run_full_pipeline(topic=topic)

    if result.get("status") == "success":
        video_entry = {
            "topic": topic,
            "script": result.get("script"),
            "hashtags": result.get("hashtags"),
            "captions": result.get("captions"),
            "predicted_analytics": result.get("predicted_analytics"),
        }
        with _videos_lock:
            _videos.append(video_entry)

    return jsonify(result)


@app.route("/videos")
def videos():
    """Return all generated videos."""
    with _videos_lock:
        return jsonify({"videos": list(_videos)})


@app.route("/trends")
def trends():
    """Return current trending hashtags."""
    from src.trend_detector import TikTokTrendDetector

    detector = TikTokTrendDetector()
    trending = detector.fetch_trends()
    return jsonify({"trends": trending})
