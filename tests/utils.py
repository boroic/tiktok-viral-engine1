"""
Utility Functions for TikTok Viral Engine
Helper functions for common operations
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileHandler:
    """Handle file operations"""
    
    @staticmethod
    def create_directory(path):
        """Create directory if it doesn't exist"""
        os.makedirs(path, exist_ok=True)
        logger.info(f"📁 Directory created/verified: {path}")
    
    @staticmethod
    def save_json(data: Dict, filename: str):
        """Save data to JSON file"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"💾 Saved: {filename}")
        return filename
    
    @staticmethod
    def load_json(filename: str) -> Dict:
        """Load data from JSON file"""
        if not os.path.exists(filename):
            logger.warning(f"⚠️ File not found: {filename}")
            return {}
        
        with open(filename, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def get_file_size(filename: str) -> str:
        """Get human-readable file size"""
        size = os.path.getsize(filename)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"


class DateTimeHelper:
    """Handle date and time operations"""
    
    @staticmethod
    def get_timestamp():
        """Get current timestamp"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def get_date():
        """Get current date"""
        return datetime.now().strftime("%Y-%m-%d")
    
    @staticmethod
    def get_time():
        """Get current time"""
        return datetime.now().strftime("%H:%M:%S")
    
    @staticmethod
    def is_peak_hours():
        """Check if current time is peak engagement hours"""
        hour = datetime.now().hour
        # Peak hours: 7 PM - 10 PM (19:00 - 22:00)
        return 19 <= hour <= 22


class ContentValidator:
    """Validate content before upload"""
    
    @staticmethod
    def validate_video(video_path: str) -> Dict[str, Any]:
        """Validate video file"""
        if not os.path.exists(video_path):
            return {"valid": False, "error": "Video file not found"}
        
        file_size = os.path.getsize(video_path)
        max_size = 500 * 1024 * 1024  # 500 MB
        
        if file_size > max_size:
            return {"valid": False, "error": f"Video too large: {FileHandler.get_file_size(video_path)}"}
        
        return {"valid": True, "size": FileHandler.get_file_size(video_path)}
    
    @staticmethod
    def validate_script(script: Dict) -> bool:
        """Validate script structure"""
        required_fields = ["title", "hook", "body", "cta"]
        return all(field in script for field in required_fields)
    
    @staticmethod
    def validate_hashtags(hashtags: List[str], max_count=30) -> List[str]:
        """Validate and clean hashtags"""
        # Remove duplicates and limit count
        cleaned = list(set([tag.lstrip('#').lower() for tag in hashtags]))
        return [f"#{tag}" for tag in cleaned[:max_count]]


class PerformanceTracker:
    """Track performance metrics"""
    
    def __init__(self):
        self.metrics = {}
    
    def start_timer(self, task_name: str):
        """Start timing a task"""
        self.metrics[task_name] = {"start": datetime.now()}
    
    def end_timer(self, task_name: str):
        """End timing a task"""
        if task_name in self.metrics:
            self.metrics[task_name]["end"] = datetime.now()
            duration = (self.metrics[task_name]["end"] - self.metrics[task_name]["start"]).total_seconds()
            logger.info(f"⏱️ {task_name} took {duration:.2f} seconds")
            return duration
        return None
    
    def log_metrics(self):
        """Log all metrics"""
        logger.info("📊 Performance Metrics:")
        for task, times in self.metrics.items():
            if "end" in times:
                duration = (times["end"] - times["start"]).total_seconds()
                logger.info(f"  {task}: {duration:.2f}s")


class DataProcessor:
    """Process and transform data"""
    
    @staticmethod
    def flatten_dict(nested_dict: Dict, parent_key='', sep='_') -> Dict:
        """Flatten nested dictionary"""
        items = []
        for k, v in nested_dict.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(DataProcessor.flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    @staticmethod
    def batch_list(items: List, batch_size: int) -> List[List]:
        """Split list into batches"""
        return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    
    @staticmethod
    def merge_dicts(*dicts) -> Dict:
        """Merge multiple dictionaries"""
        result = {}
        for d in dicts:
            result.update(d)
        return result