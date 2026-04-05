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
        
        # Initialize modules
        self.trend_detector = TikTokTrendDetector()
        self.sound_analyzer = SoundAnalyzer()
        self.video_analytics = VideoAnalytics()
        self.script_gen = ScriptGenerator()
        self.uploader = UploadHandler()
        self.influencer_finder = InfluencerFinder()
        
        # Initialize API Manager
        self.api_manager = APIManager()
        
        logger.info("✅ All modules initialized")
    
    def run_full_pipeline(self, topic: str = "viral"):
        """Execute complete viral content pipeline"""
        logger.info(f"🎬 Starting full pipeline for topic: {topic}")
        
        try:
            # 1. Health check
            health = self.api_manager.health_check()
            logger.info(f"🏥 {health['status']}")
            
            # 2. Detect trends
            trends = self.trend_detector.fetch_trends()
            logger.info(f"📊 Found {len(trends)} trends: {trends}")
            
            # 3. Analyze sounds
            sounds = self.sound_analyzer.analyze_trending_sounds()
            logger.info(f"🎵 Analyzed {len(sounds)} trending sounds")
            
            # 4. Generate script using AI
            script = self.api_manager.openai.generate_script(topic)
            logger.info(f"✍️ Generated AI script")
            
            # 5. Generate hashtags
            hashtags = self.api_manager.openai.generate_hashtags(topic)
            logger.info(f"🏷️ Generated {len(hashtags)} hashtags")
            
            # 6. Generate captions
            captions = self.api_manager.openai.generate_captions(topic)
            logger.info(f"📝 Generated {len(captions)} caption options")
            
            # 7. Predict performance
            analytics = self.video_analytics.predict_performance(script)
            logger.info(f"📈 Predicted performance: {analytics['predicted_views']} views")
            
            # 8. Find influencers
            influencers = self.influencer_finder.find_collaborators(trends[0])
            logger.info(f"👥 Found {len(influencers)} potential influencers")
            
            # 9. Ready for upload
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
    
    def quick_generate(self, topic: str):
        """Quick content generation"""
        logger.info(f"⚡ Quick generate for: {topic}")
        return self.api_manager.full_workflow(topic)
    
    def upload_content(self, video_path: str, caption: str, hashtags: list):
        """Upload content to TikTok"""
        logger.info(f"📤 Uploading: {video_path}")
        result = self.api_manager.tiktok.upload_video(video_path, caption, hashtags)
        return result
    
    def get_analytics(self, video_id: str):
        """Get video analytics"""
        logger.info(f"📊 Getting analytics for: {video_id}")
        return self.api_manager.tiktok.get_analytics(video_id)


if __name__ == "__main__":
    # Initialize engine
    engine = TikTokViralEngine()
    
    # Run full pipeline
    result = engine.run_full_pipeline(topic="viral_trends")
    
    logger.info("=" * 50)
    logger.info("🎉 PIPELINE COMPLETE!")
    logger.info("=" * 50)