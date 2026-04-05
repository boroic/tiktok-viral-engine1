"""API Client - Manage external API integrations"""

class APIManager:
    def __init__(self):
        self.tiktok = None
        self.openai = None
    
    def health_check(self):
        return {"status": "ok"}