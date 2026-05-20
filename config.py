import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    CHATBOT_DATA_PATH = os.path.join(os.path.dirname(__file__), "Chatbot2.md")
    
    MODEL_NAME = "google/gemini-2.0-flash-lite-001" 
    TEMPERATURE = 0.7
    
    LEADS_FILE = os.path.join(os.path.dirname(__file__), "leads.json")
    LARAVEL_API_URL = os.getenv("LARAVEL_API_URL", "https://freedomdental.ie/api/chatbot/lead")
    
    @classmethod
    def ensure_leads_file(cls):
        if not os.path.exists(cls.LEADS_FILE) or os.path.getsize(cls.LEADS_FILE) == 0:
            import json
            with open(cls.LEADS_FILE, 'w') as f:
                json.dump([], f)

config = Config()
config.ensure_leads_file()
