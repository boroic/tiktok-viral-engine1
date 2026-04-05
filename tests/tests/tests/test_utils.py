"""
Unit tests for utility functions
"""

import unittest
import json
import os
from utils import FileHandler, ContentValidator, DateTimeHelper

class TestFileHandler(unittest.TestCase):
    """Test FileHandler utilities"""
    
    def setUp(self):
        self.test_dir = "test_temp"
        self.test_file = f"{self.test_dir}/test.json"
    
    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)
    
    def test_create_directory(self):
        """Test directory creation"""
        FileHandler.create_directory(self.test_dir)
        self.assertTrue(os.path.exists(self.test_dir))
    
    def test_save_load_json(self):
        """Test JSON save and load"""
        data = {"test": "data", "number": 123}
        FileHandler.save_json(data, self.test_file)
        loaded = FileHandler.load_json(self.test_file)
        self.assertEqual(data, loaded)


class TestContentValidator(unittest.TestCase):
    """Test content validation"""
    
    def test_validate_hashtags(self):
        """Test hashtag validation"""
        tags = ["#viral", "#tiktok", "#viral"]  # Duplicate
        validated = ContentValidator.validate_hashtags(tags)
        self.assertEqual(len(validated), 2)
        self.assertTrue(all(tag.startswith("#") for tag in validated))


if __name__ == "__main__":
    unittest.main()