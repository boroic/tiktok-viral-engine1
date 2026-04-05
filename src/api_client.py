"""API Client - Manage external API integrations"""

from src.script_generator import ScriptGenerator

class APIManager:
    def __init__(self):
        self.tiktok = None
        self.openai = ScriptGenerator()
    
    def health_check(self):
        return {"status": "ok"}