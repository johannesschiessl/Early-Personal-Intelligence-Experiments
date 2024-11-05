import json
from datetime import datetime
from pathlib import Path
import threading
import time
from typing import Dict, Any
import telebot
from utils.conversations import Conversations

class MessageSchedule:
    def __init__(self, bot: telebot.TeleBot):
        self.bot = bot
        self.conversations = Conversations()
        self.data_dir = Path("data")
        self.schedule_file = self.data_dir / "scheduled_messages.json"
        self._init_data_store()
        
        self.scheduler_thread = threading.Thread(target=self._process_schedule, daemon=True)
        self.scheduler_thread.start()
    
    def _init_data_store(self):
        """Initialize the data storage"""
        self.data_dir.mkdir(exist_ok=True)
        if not self.schedule_file.exists():
            self._save_messages({})
        self.scheduled_messages = self._load_messages()
    
    def _load_messages(self) -> dict:
        """Load scheduled messages from JSON file"""
        with open(self.schedule_file, 'r') as f:
            return json.load(f)
    
    def _save_messages(self, messages: dict):
        """Save scheduled messages to JSON file"""
        with open(self.schedule_file, 'w') as f:
            json.dump(messages, f, indent=2)
    
    def add(self, chat_id: int, message: str, scheduled_time: str) -> Dict[str, Any]:
        """
        Schedule a new message
        scheduled_time should be in ISO format: YYYY-MM-DD HH:MM:SS
        """
        try:
            scheduled_datetime = datetime.strptime(scheduled_time, "%Y-%m-%d %H:%M:%S")
            
            if scheduled_datetime < datetime.now():
                return {"error": "Cannot schedule messages in the past"}
            
            chat_id_str = str(chat_id)
            if chat_id_str not in self.scheduled_messages:
                self.scheduled_messages[chat_id_str] = []
            
            new_message = {
                "message": message,
                "scheduled_time": scheduled_time,
                "status": "pending"
            }
            
            self.scheduled_messages[chat_id_str].append(new_message)
            self._save_messages(self.scheduled_messages)
            
            return {
                "success": True,
                "message": "Successfully scheduled message",
                "scheduled_time": scheduled_time
            }
            
        except ValueError as e:
            return {"error": f"Invalid datetime format: {str(e)}"}
    
    def _process_schedule(self):
        """Background thread to check and send scheduled messages"""
        while True:
            current_time = datetime.now()
            
            for chat_id, messages in self.scheduled_messages.items():
                chat_id = int(chat_id)
                
                for message in messages[:]:
                    if message["status"] == "pending":
                        scheduled_time = datetime.strptime(
                            message["scheduled_time"], 
                            "%Y-%m-%d %H:%M:%S"
                        )
                        
                        if current_time >= scheduled_time:
                            try:
                                self.bot.send_message(chat_id, message["message"])
                                
                                self.conversations.add(
                                    chat_id, 
                                    "assistant", 
                                    message["message"]
                                )
                                
                                message["status"] = "sent"
                                self._save_messages(self.scheduled_messages)
                                
                            except Exception as e:
                                message["status"] = "failed"
                                message["error"] = str(e)
                                self._save_messages(self.scheduled_messages)
            
            time.sleep(30) 