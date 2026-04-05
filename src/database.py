"""
Database Models and ORM Setup
SQLAlchemy models for persistent storage
"""

import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import Config

logger = logging.getLogger(__name__)

# Create base for models
Base = declarative_base()

class VideoMetadata(Base):
    """Video metadata model"""
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True)
    video_id = Column(String(255), unique=True)
    title = Column(String(500))
    caption = Column(Text)
    hashtags = Column(Text)  # JSON string
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    upload_date = Column(DateTime, default=datetime.now)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Video {self.video_id}>"


class TrendData(Base):
    """Trend tracking model"""
    __tablename__ = "trends"
    
    id = Column(Integer, primary_key=True)
    hashtag = Column(String(255), unique=True)
    engagement_rate = Column(Float)
    growth_rate = Column(Float)
    video_count = Column(Integer)
    tracked_date = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Trend {self.hashtag}>"


class ScriptHistory(Base):
    """AI-generated scripts history"""
    __tablename__ = "scripts"
    
    id = Column(Integer, primary_key=True)
    topic = Column(String(500))
    script_content = Column(Text)
    created_date = Column(DateTime, default=datetime.now)
    used = Column(Integer, default=0)
    performance = Column(Float, default=0.0)
    
    def __repr__(self):
        return f"<Script {self.topic}>"


class DatabaseManager:
    """Database management class"""
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or Config.DATABASE_URL
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"📦 Database initialized: {self.db_url}")
    
    def create_tables(self):
        """Create all database tables"""
        logger.info("📝 Creating database tables...")
        Base.metadata.create_all(self.engine)
        logger.info("✅ Tables created successfully")
    
    def save_video(self, video_data: dict) -> bool:
        """Save video metadata"""
        session = self.Session()
        try:
            video = VideoMetadata(**video_data)
            session.add(video)
            session.commit()
            logger.info(f"💾 Saved video: {video_data.get('video_id')}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Failed to save video: {e}")
            return False
        finally:
            session.close()
    
    def get_videos(self, limit: int = 10) -> list:
        """Get recent videos"""
        session = self.Session()
        try:
            videos = session.query(VideoMetadata).order_by(
                VideoMetadata.upload_date.desc()
            ).limit(limit).all()
            return videos
        finally:
            session.close()
    
    def save_trend(self, trend_data: dict) -> bool:
        """Save trend data"""
        session = self.Session()
        try:
            trend = TrendData(**trend_data)
            session.add(trend)
            session.commit()
            logger.info(f"📊 Saved trend: {trend_data.get('hashtag')}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Failed to save trend: {e}")
            return False
        finally:
            session.close()
    
    def save_script(self, script_data: dict) -> bool:
        """Save generated script"""
        session = self.Session()
        try:
            script = ScriptHistory(**script_data)
            session.add(script)
            session.commit()
            logger.info(f"✍️ Saved script: {script_data.get('topic')}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Failed to save script: {e}")
            return False
        finally:
            session.close()
    
    def get_top_trending(self, limit: int = 10) -> list:
        """Get top trending hashtags"""
        session = self.Session()
        try:
            trends = session.query(TrendData).order_by(
                TrendData.engagement_rate.desc()
            ).limit(limit).all()
            return trends
        finally:
            session.close()