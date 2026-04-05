"""
Unit tests for UploadHandler upload functionality
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Make sure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.upload_handler import UploadHandler, MOCK_VIDEO_ID, MOCK_UPLOAD_URL


class TestMockUpload(unittest.TestCase):
    """Tests for UploadHandler in mock mode"""

    def setUp(self):
        self.handler = UploadHandler(mock_mode=True)

    # ------------------------------------------------------------------
    # upload_video
    # ------------------------------------------------------------------

    def test_upload_video_success(self):
        """Mock upload returns a success status"""
        result = self.handler.upload_video("video.mp4")
        self.assertEqual(result["status"], "success")

    def test_upload_video_returns_mock_video_id(self):
        """Mock upload returns the canonical mock video_id"""
        result = self.handler.upload_video("video.mp4")
        self.assertEqual(result["video_id"], MOCK_VIDEO_ID)

    def test_upload_video_returns_mock_url(self):
        """Mock upload returns the canonical mock URL"""
        result = self.handler.upload_video("video.mp4")
        self.assertEqual(result["url"], MOCK_UPLOAD_URL)

    def test_upload_video_contains_upload_time(self):
        """Mock upload response includes an upload timestamp"""
        result = self.handler.upload_video("video.mp4")
        self.assertIn("upload_time", result)
        self.assertIsInstance(result["upload_time"], str)
        self.assertTrue(len(result["upload_time"]) > 0)

    def test_upload_video_mock_flag_set(self):
        """Result is flagged as a mock response"""
        result = self.handler.upload_video("video.mp4")
        self.assertTrue(result.get("mock"))

    def test_upload_video_caption_stored(self):
        """Caption passed to upload_video is echoed back in the response"""
        caption = "Check this out! 🔥"
        result = self.handler.upload_video("video.mp4", caption=caption)
        self.assertEqual(result["caption"], caption)

    def test_upload_video_hashtags_stored(self):
        """Hashtags passed to upload_video are echoed back in the response"""
        hashtags = ["#viral", "#fyp", "#tiktok"]
        result = self.handler.upload_video("video.mp4", hashtags=hashtags)
        self.assertEqual(result["hashtags"], hashtags)

    def test_upload_video_appended_to_history(self):
        """Successful upload is tracked in uploaded_videos list"""
        self.handler.upload_video("clip1.mp4")
        self.handler.upload_video("clip2.mp4")
        self.assertEqual(len(self.handler.uploaded_videos), 2)

    # ------------------------------------------------------------------
    # get_upload_status
    # ------------------------------------------------------------------

    def test_get_upload_status_returns_published(self):
        """Mock status check reports the video as published"""
        status = self.handler.get_upload_status(MOCK_VIDEO_ID)
        self.assertEqual(status["status"], "published")

    def test_get_upload_status_contains_video_id(self):
        """Status response echoes back the requested video_id"""
        status = self.handler.get_upload_status(MOCK_VIDEO_ID)
        self.assertEqual(status["video_id"], MOCK_VIDEO_ID)

    def test_get_upload_status_contains_engagement_fields(self):
        """Mock status response includes engagement metrics"""
        status = self.handler.get_upload_status(MOCK_VIDEO_ID)
        for field in ("views", "likes", "comments", "shares"):
            self.assertIn(field, status, f"Missing engagement field: {field}")
            self.assertIsInstance(status[field], int)

    def test_get_upload_status_mock_flag_set(self):
        """Status response is flagged as mock"""
        status = self.handler.get_upload_status(MOCK_VIDEO_ID)
        self.assertTrue(status.get("mock"))

    # ------------------------------------------------------------------
    # batch_upload
    # ------------------------------------------------------------------

    def test_batch_upload_returns_all_results(self):
        """batch_upload returns one result per video in the list"""
        videos = ["a.mp4", "b.mp4", "c.mp4"]
        results = self.handler.batch_upload(videos)
        self.assertEqual(len(results), len(videos))

    def test_batch_upload_all_success(self):
        """Every result in a batch upload has status 'success'"""
        results = self.handler.batch_upload(["x.mp4", "y.mp4"])
        for result in results:
            self.assertEqual(result["status"], "success")


class TestRealUploadMode(unittest.TestCase):
    """Tests for UploadHandler in real (non-mock) mode"""

    def setUp(self):
        self.handler = UploadHandler(mock_mode=False)

    def test_upload_video_not_flagged_as_mock(self):
        """In real mode the response is not flagged as mock"""
        result = self.handler.upload_video("video.mp4")
        self.assertFalse(result.get("mock"))

    def test_upload_video_contains_required_fields(self):
        """Real mode upload response still contains required fields"""
        result = self.handler.upload_video("video.mp4")
        for field in ("status", "video_id", "url", "upload_time"):
            self.assertIn(field, result, f"Missing required field: {field}")

    def test_get_upload_status_not_flagged_as_mock(self):
        """In real mode the status response is not flagged as mock"""
        status = self.handler.get_upload_status("v12345abc")
        self.assertFalse(status.get("mock"))


if __name__ == "__main__":
    unittest.main()
