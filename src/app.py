"""
TikTok Viral Engine - Flask REST API
Provides HTTP endpoints for Railway deployment
"""

import logging
import threading
from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Thread-safe video storage
_videos_lock = threading.Lock()
_videos = []


@app.route("/", methods=["GET"])
def root():
    """Root health check"""
    return jsonify({"status": "ok", "service": "tiktok-viral-engine"})


@app.route("/health", methods=["GET"])
def health():
    """API health check"""
    return jsonify({"status": "ok"})


@app.route("/generate", methods=["POST"])
def generate():
    """Run content generation pipeline"""
    # Lazy import avoids circular dependency (main.py imports src.app at runtime)
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
        logger.error(f"❌ Generate failed: {e}")
        return jsonify({"status": "error", "message": "Content generation failed"}), 500


@app.route("/videos", methods=["GET"])
def videos():
    """Return generated videos (thread-safe)"""
    with _videos_lock:
        return jsonify({"status": "ok", "videos": list(_videos)})


@app.route("/trends", methods=["GET"])
def trends():
    """Return trending topics"""
    try:
        from src.trend_detector import TikTokTrendDetector
        detector = TikTokTrendDetector()
        trend_list = detector.fetch_trends()
        return jsonify({"status": "ok", "trends": trend_list})
    except Exception as e:
        logger.error(f"❌ Trends failed: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch trends"}), 500
