import json
import os
from typing import List, Dict

class Conversations:
    def __init__(self):
        self.history: Dict[str, List[Dict]] = {}
        
        os.makedirs('data', exist_ok=True)
        self.load()
        
    def load(self):
        """Load conversation history from JSON file"""
        try:
            if os.path.exists('data/conversation_history.json'):
                with open('data/conversation_history.json', 'r') as f:
                    self.history = json.load(f)
        except Exception as e:
            print(f"Error loading conversation history: {str(e)}")
            self.history = {}
            
    def save(self):
        """Save conversation history to JSON file"""
        try:
            with open('data/conversation_history.json', 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Error saving conversation history: {str(e)}")
    
    def get(self, chat_id: int) -> List[Dict]:
        """Get conversation history for a specific chat"""
        return self.history.get(str(chat_id), [])
    
    def add(self, chat_id: int, role: str, content: str):
        """Add a message to the conversation history"""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.history:
            self.history[chat_id_str] = []
            
        self.history[chat_id_str].append({
            "role": role,
            "content": content
        })
        self.save() 