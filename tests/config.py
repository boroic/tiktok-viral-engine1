"""
Configuration Manager for TikTok Viral Engine
Manages API keys, settings, and environment variables
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration"""
    
    # API Keys
    TIKTOK_API_KEY = os.getenv("TIKTOK_API_KEY", "your-tiktok-api-key")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
    TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "your-twitter-api-key")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "your-youtube-api-key")
    
    # TikTok Settings
    TIKTOK_UPLOAD_FOLDER = "uploads/"
    TIKTOK_OUTPUT_FOLDER = "output/"
    MAX_VIDEO_DURATION = 600  # 10 minutes in seconds
    MIN_VIDEO_DURATION = 15   # 15 seconds minimum
    
    # Upload Settings
    BATCH_SIZE = 5
    UPLOAD_RETRY_ATTEMPTS = 3
    UPLOAD_TIMEOUT = 300  # 5 minutes
    
    # Content Settings
    DEFAULT_LANGUAGE = "en"
    DEFAULT_CONTENT_TYPE = "viral"
    MIN_ENGAGEMENT_THRESHOLD = 0.05  # 5%
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tiktok_engine.db")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = "logs/tiktok_engine.log"
    
    # Scheduler
    SCHEDULE_ENABLED = True
    UPLOAD_SCHEDULE = "0 19 * * *"  # 7 PM daily
    TREND_CHECK_INTERVAL = 3600  # 1 hour
    
    # Feature Flags
    ENABLE_AI_SCRIPTS = True
    ENABLE_INFLUENCER_MATCHING = True
    ENABLE_ANALYTICS = True
    ENABLE_AUTO_UPLOAD = False  # Disabled by default for safety
    
    @classmethod
    def from_env(cls, env_name="development"):
        """Load config based on environment"""
        if env_name == "production":
            return ProductionConfig()
        elif env_name == "testing":
            return TestingConfig()
        return DevelopmentConfig()


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    ENABLE_AUTO_UPLOAD = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    ENABLE_AUTO_UPLOAD = True


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"
    ENABLE_AUTO_UPLOAD = False