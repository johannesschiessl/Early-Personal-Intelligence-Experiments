import json
from datetime import datetime
from pathlib import Path
import threading
import time
from typing import Dict, Any
import telebot

class MessageScheduler:
    def __init__(self, bot: telebot.TeleBot):
        self.bot = bot
        self.schedule_file = Path("scheduled_messages.json")
        self.load_messages()
        
        # Start the scheduler thread
        self.scheduler_thread = threading.Thread(target=self._schedule_checker, daemon=True)
        self.scheduler_thread.start()
    
    def load_messages(self):
        """Load scheduled messages from JSON file"""
        if not self.schedule_file.exists():
            self.scheduled_messages = []
            self._save_messages()
        else:
            with open(self.schedule_file, 'r') as f:
                self.scheduled_messages = json.load(f)
    
    def _save_messages(self):
        """Save scheduled messages to JSON file"""
        with open(self.schedule_file, 'w') as f:
            json.dump(self.scheduled_messages, f, indent=2)
    
    def schedule_message(self, chat_id: int, message: str, scheduled_time: str) -> Dict[str, Any]:
        """
        Schedule a new message
        scheduled_time should be in ISO format: YYYY-MM-DD HH:MM:SS
        """
        try:
            # Validate the datetime format
            scheduled_datetime = datetime.strptime(scheduled_time, "%Y-%m-%d %H:%M:%S")
            
            # Don't schedule messages in the past
            if scheduled_datetime < datetime.now():
                return {"error": "Cannot schedule messages in the past"}
            
            new_message = {
                "chat_id": chat_id,
                "message": message,
                "scheduled_time": scheduled_time,
                "status": "pending"
            }
            
            self.scheduled_messages.append(new_message)
            self._save_messages()
            
            return {
                "success": True,
                "scheduled_message": new_message
            }
            
        except ValueError as e:
            return {"error": f"Invalid datetime format: {str(e)}"}
    
    def _schedule_checker(self):
        """Background thread to check and send scheduled messages"""
        while True:
            current_time = datetime.now()
            
            # Check each message
            for message in self.scheduled_messages[:]:  # Create a copy to iterate
                if message["status"] == "pending":
                    scheduled_time = datetime.strptime(message["scheduled_time"], "%Y-%m-%d %H:%M:%S")
                    
                    if current_time >= scheduled_time:
                        try:
                            # Send the message
                            self.bot.send_message(
                                message["chat_id"],
                                message["message"]
                            )
                            # Mark as sent
                            message["status"] = "sent"
                            self._save_messages()
                        except Exception as e:
                            message["status"] = "failed"
                            message["error"] = str(e)
                            self._save_messages()
            
            # Sleep for 30 seconds before next check
            time.sleep(30) 