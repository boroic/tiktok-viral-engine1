"""
TikTok Viral Engine - Flask REST API
Provides HTTP endpoints for Railway deployment
"""

import os
import logging
import threading
from flask import Flask, jsonify, request

from src.trend_detector import TikTokTrendDetector
from src.video_analytics import VideoAnalytics
from src.api_client import APIManager

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Thread-safe in-memory store for generated videos
_generated_videos = []
_videos_lock = threading.Lock()

# Initialize modules once
_trend_detector = TikTokTrendDetector()
_video_analytics = VideoAnalytics()
_api_manager = APIManager()


@app.route("/", methods=["GET"])
def index():
    """Health check / root endpoint"""
    return jsonify({"status": "ok", "service": "TikTok Viral Engine"})


@app.route("/health", methods=["GET"])
def health():
    """API health endpoint"""
    return jsonify({"status": "ok"})


@app.route("/generate", methods=["POST"])
def generate():
    """Generate TikTok content for a topic"""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    topic = data.get("topic", "viral_trends")

    try:
        script = _api_manager.openai.generate_script(topic)
        hashtags = _api_manager.openai.generate_hashtags(topic)
        captions = _api_manager.openai.generate_captions(topic)
        analytics = _video_analytics.predict_performance(script)

        with _videos_lock:
            video_id = f"v_{len(_generated_videos) + 1}"
            video_entry = {
                "id": video_id,
                "topic": topic,
                "script": script,
                "hashtags": hashtags,
                "captions": captions,
                "performance": analytics["predicted_views"],
            }
            _generated_videos.append(video_entry)

        return jsonify({
            "script": script,
            "hashtags": hashtags,
            "captions": captions,
            "performance": analytics["predicted_views"],
        })
    except Exception as e:
        logger.error(f"Generate endpoint failed: {e}")
        return jsonify({"error": "Content generation failed"}), 500


@app.route("/videos", methods=["GET"])
def videos():
    """List all generated videos"""
    with _videos_lock:
        return jsonify({"videos": list(_generated_videos)})


@app.route("/trends", methods=["GET"])
def trends():
    """Get current trending topics"""
    try:
        current_trends = _trend_detector.fetch_trends()
        return jsonify({"trends": current_trends})
    except Exception as e:
        logger.error(f"Trends endpoint failed: {e}")
        return jsonify({"error": "Failed to fetch trends"}), 500


def create_app():
    """Application factory"""
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
