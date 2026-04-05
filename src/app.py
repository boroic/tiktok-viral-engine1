"""
TikTok Viral Engine - Flask REST API
Provides HTTP endpoints for content generation and management
"""

import os
import threading
import logging
from flask import Flask, jsonify, request

from src.trend_detector import TikTokTrendDetector
from src.script_generator import ScriptGenerator
from src.video_analytics import VideoAnalytics
from src.api_client import APIManager

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Thread-safe in-memory video storage
_videos = []
_videos_lock = threading.Lock()

# Module-level instances (shared across requests)
_api_manager = APIManager()
_analytics_engine = VideoAnalytics()
_trend_detector = TikTokTrendDetector()


@app.route("/")
def root():
    """Root health check"""
    return jsonify({"status": "ok", "service": "TikTok Viral Engine"})


@app.route("/health")
def health():
    """API health endpoint"""
    return jsonify({"status": "ok"})


@app.route("/generate", methods=["POST"])
def generate():
    """Generate TikTok content for a given topic"""
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "viral_trends")

    try:
        script = _api_manager.openai.generate_script(topic)
        hashtags = _api_manager.openai.generate_hashtags(topic)
        captions = _api_manager.openai.generate_captions(topic)
        analytics = _analytics_engine.predict_performance(script)

        result = {
            "script": script,
            "hashtags": hashtags,
            "captions": captions,
            "performance": analytics.get("predicted_views", 250000),
        }

        with _videos_lock:
            _videos.append(result)

        return jsonify(result)

    except Exception as exc:
        logger.error("Generate failed: %s", exc)
        return jsonify({"error": "Content generation failed"}), 500


@app.route("/videos")
def videos():
    """List all generated videos"""
    with _videos_lock:
        return jsonify({"videos": list(_videos)})


@app.route("/trends")
def trends():
    """Get current trending topics"""
    try:
        trend_list = _trend_detector.fetch_trends()
        return jsonify({"trends": trend_list})
    except Exception as exc:
        logger.error("Trends fetch failed: %s", exc)
        return jsonify({"error": "Failed to fetch trends"}), 500
