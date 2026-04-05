"""
TikTok Viral Engine - Main Entry Point
Orchestrates all modules for viral content generation
"""

from sound_analyzer import SoundAnalyzer
from video_analytics import VideoAnalytics
from script_generator import ScriptGenerator
from upload_handler import UploadHandler
from influencer_finder import InfluencerFinder
from trend_detector import TikTokTrendDetector

class TikTokViralEngine:
    """Main orchestrator for all TikTok automation"""
    
    def __init__(self):
        self.trend_detector = TikTokTrendDetector()
        self.sound_analyzer = SoundAnalyzer()
        self.video_analytics = VideoAnalytics()
        self.script_gen = ScriptGenerator()
        self.uploader = UploadHandler()
        self.influencer_finder = InfluencerFinder()
    
    def run_full_pipeline(self):
        """Execute complete viral content pipeline"""
        print("🚀 Starting TikTok Viral Engine...")
        
        # 1. Detect trends
        trends = self.trend_detector.fetch_trends()
        print(f"📊 Found {len(trends)} trends")
        
        # 2. Analyze sounds
        sounds = self.sound_analyzer.analyze_trending_sounds()
        print(f"🎵 Analyzed {len(sounds)} trending sounds")
        
        # 3. Generate script
        script = self.script_gen.generate_script(trends[0])
        print(f"✍️ Generated script: {script}")
        
        # 4. Predict performance
        analytics = self.video_analytics.predict_performance(script)
        print(f"📈 Predicted performance: {analytics}")
        
        # 5. Find influencers
        influencers = self.influencer_finder.find_collaborators(trends[0])
        print(f"👥 Found {len(influencers)} potential influencers")
        
        # 6. Upload
        result = self.uploader.upload_video("sample_video.mp4")
        print(f"✅ Upload status: {result}")

if __name__ == "__main__":
    engine = TikTokViralEngine()
    engine.run_full_pipeline()