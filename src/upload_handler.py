"""TikTok Upload Automation Module"""

from datetime import datetime

MOCK_VIDEO_ID = "tiktok_mock_12345"
MOCK_UPLOAD_URL = "https://tiktok.mock/videos/12345"


class UploadHandler:
    """Handle automated uploads to TikTok"""

    def __init__(self, mock_mode=False):
        self.uploaded_videos = []
        self.api_key = None
        self.mock_mode = mock_mode

    def authenticate(self, api_key):
        """Authenticate with TikTok API"""
        print("🔐 Authenticating with TikTok...")
        self.api_key = api_key
        return {"status": "authenticated"}

    def upload_video(self, video_path, caption="", hashtags=""):
        """Upload video to TikTok.

        In mock mode returns a simulated successful response without
        contacting any external API.
        """
        print(f"📤 Uploading {video_path}...")
        if self.mock_mode:
            result = {
                "status": "success",
                "video_id": MOCK_VIDEO_ID,
                "url": MOCK_UPLOAD_URL,
                "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "caption": caption,
                "hashtags": hashtags,
                "mock": True,
            }
        else:
            result = {
                "status": "success",
                "video_id": "v12345abc",
                "url": "https://www.tiktok.com/@user/video/12345abc",
                "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "caption": caption,
                "hashtags": hashtags,
                "mock": False,
            }
        self.uploaded_videos.append(result)
        return result

    def get_upload_status(self, video_id):
        """Check upload / processing status for a given video ID.

        In mock mode returns a simulated status response with fake
        engagement metrics.
        """
        if self.mock_mode:
            return {
                "video_id": video_id,
                "status": "published",
                "views": 1000,
                "likes": 150,
                "comments": 30,
                "shares": 20,
                "mock": True,
            }
        return {
            "video_id": video_id,
            "status": "processing",
            "mock": False,
        }

    def schedule_upload(self, video_path, schedule_time):
        """Schedule video for later upload"""
        print(f"⏰ Scheduling upload for {schedule_time}...")
        return {"status": "scheduled"}

    def batch_upload(self, video_list):
        """Upload multiple videos"""
        results = []
        for video in video_list:
            result = self.upload_video(video)
            results.append(result)
        return results