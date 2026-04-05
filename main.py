"""
TikTok Viral Engine - Main Entry Point
Orchestrates all modules for viral content generation
"""

import logging
from src.trend_detector import TikTokTrendDetector
from src.sound_analyzer import SoundAnalyzer
from src.video_analytics import VideoAnalytics
from src.script_generator import ScriptGenerator
from src.upload_handler import UploadHandler
from src.influencer_finder import InfluencerFinder
from src.api_client import APIManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TikTokViralEngine:
    """Main orchestrator for all TikTok automation"""

    def __init__(self):
        logger.info("🚀 Initializing TikTok Viral Engine...")
        self.trend_detector = TikTokTrendDetector()
        self.sound_analyzer = SoundAnalyzer()
        self.video_analytics = VideoAnalytics()
        self.script_gen = ScriptGenerator()
        self.uploader = UploadHandler()
        self.influencer_finder = InfluencerFinder()
        self.api_manager = APIManager()
        logger.info("✅ All modules initialized")

    def run_full_pipeline(self, topic: str = "viral"):
        """Execute complete viral content pipeline"""
        logger.info(f"🎬 Starting full pipeline for topic: {topic}")

        try:
            health = self.api_manager.health_check()
            logger.info(f"🏥 {health['status']}")

            trends = self.trend_detector.fetch_trends()
            logger.info(f"📊 Found {len(trends)} trends: {trends}")

            sounds = self.sound_analyzer.analyze_trending_sounds()
            logger.info(f"🎵 Analyzed {len(sounds)} trending sounds")

            script = self.api_manager.openai.generate_script(topic)
            logger.info("✍️ Generated AI script")

            hashtags = self.api_manager.openai.generate_hashtags(topic)
            logger.info(f"🏷️ Generated {len(hashtags)} hashtags")

            captions = self.api_manager.openai.generate_captions(topic)
            logger.info(f"📝 Generated {len(captions)} caption options")

            analytics = self.video_analytics.predict_performance(script)
            logger.info(f"📈 Predicted performance: {analytics['predicted_views']} views")

            influencers = self.influencer_finder.find_collaborators(trends[0])
            logger.info(f"👥 Found {len(influencers)} potential influencers")

            logger.info("✅ Content ready for upload!")

            return {
                "status": "success",
                "topic": topic,
                "script": script,
                "hashtags": hashtags,
                "captions": captions,
                "predicted_analytics": analytics,
                "influencers": influencers,
                "trends": trends,
                "sounds": sounds
            }

        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import os
    import argparse
    from flask import Flask, jsonify

    parser = argparse.ArgumentParser()
    parser.add_argument("--mock-upload", action="store_true", help="Run CLI pipeline")
    parser.add_argument("--topic", default="viral_trends", help="Topic to generate content for")
    args = parser.parse_args()

    if args.mock_upload:
        engine = TikTokViralEngine()
        engine.run_full_pipeline(topic=args.topic)
        logger.info("=" * 50)
        logger.info("🎉 PIPELINE COMPLETE!")
        logger.info("=" * 50)
    else:
        app = Flask(__name__)

        @app.get("/health")
        def health():
            return jsonify({"status": "ok"}), 200

        port = int(os.environ.get("PORT", 8080))
        logger.info(f"🚀 Starting Flask server on 0.0.0.0:{port}")
        app.run(host="0.0.0.0", port=port, debug=False)
