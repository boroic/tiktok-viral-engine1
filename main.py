from flask import Flask, jsonify, request
import os
import logging

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


app = Flask(__name__)
engine = TikTokViralEngine()


@app.get("/")
def home():
    return jsonify({"status": "ok", "service": "tiktok-viral-engine1"}), 200


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
