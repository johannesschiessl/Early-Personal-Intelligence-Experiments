import os
import json
import logging
from typing import Dict, List
from pathlib import Path
import telebot
from openai import OpenAI
from memory_manager import MemoryManager
from code_executor import CodeExecutor
from url_handler import URLHandler
from datetime import datetime
from message_scheduler import MessageScheduler
from calendar_handler import CalendarHandler
from daily_summary import DailySummary
import schedule
import time
import threading
import base64
import requests
from io import BytesIO

# Add logging configuration at the top level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('assistant.log'),
        logging.StreamHandler()
    ]
)

class Assistant:
    def __init__(self):
        self.logger = logging.getLogger('Assistant')
        self.logger.info("Initializing Assistant...")
        
        # Initialize OpenAI client with API key from environment variable
        self.client = OpenAI()
        
        self.memory_manager = MemoryManager()
        self.code_executor = CodeExecutor()
        self.url_handler = URLHandler()
        
        self.conversation_history = []
        self.DATA_DIR = Path("data")
        
        # Ensure data directory and memories exist
        self.DATA_DIR.mkdir(exist_ok=True)
        if not os.path.exists("memories.json"):
            self.logger.info("Creating new memories.json file")
            with open("memories.json", "w") as f:
                json.dump({}, f)
        
        self.tools = self._get_tools()
        self.available_functions = {
            "store_memory": self.store_memory,
            "file": self.handle_file,
            "execute_code": self.code_executor.execute_code,
            "open_url": self.url_handler.open_url,
            "schedule_message": self.schedule_message,
            "add_calendar_event": self.add_calendar_event,
            "list_calendar_events": self.list_calendar_events,
            "edit_calendar_event": self.edit_calendar_event,
            "delete_calendar_event": self.delete_calendar_event,
        }
        
        # message_scheduler will be set after initialization
        self.message_scheduler = None
        self.logger.info("Assistant initialization complete")

        self.calendar_handler = CalendarHandler()
        self.daily_summary = DailySummary(self)

    def handle_file(self, path: str, content: str = None, mode: str = "r") -> Dict:
        """Handle file operations in the data directory"""
        self.logger.info(f"File operation requested - Path: {path}, Mode: {mode}")
        full_path = self.DATA_DIR / path.lstrip("/")
        
        if mode == "w":
            full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if mode == "r":
                if not full_path.exists():
                    self.logger.warning(f"File not found: {path}")
                    return {"error": "File not found"}
                return {"content": full_path.read_text()}
            
            elif mode == "w":
                full_path.write_text(content)
                self.logger.info(f"Successfully wrote to file: {path}")
                return {"success": True, "path": str(full_path.relative_to(self.DATA_DIR))}
                
            elif mode == "d":
                if not full_path.exists():
                    self.logger.warning(f"File not found for deletion: {path}")
                    return {"error": "File not found"}
                full_path.unlink()
                self.logger.info(f"Successfully deleted file: {path}")
                return {"success": True, "message": f"Deleted {path}"}
                
        except Exception as e:
            self.logger.error(f"Error in file operation: {str(e)}", exc_info=True)
            return {"error": str(e)}

    def get_existing_files(self) -> List[str]:
        """Get list of all files in data directory including subdirectories"""
        files = []
        for path in self.DATA_DIR.rglob("*"):
            if path.is_file():
                files.append(str(path.relative_to(self.DATA_DIR)))
        return files

    def get_current_datetime(self) -> str:
        """Get current day, date and time in formatted string"""
        return datetime.now().strftime("%A, %B %d, %Y %H:%M")

    def get_system_instructions(self):
        memories = self.memory_manager.get_all_memories()
        existing_files = self.get_existing_files()
        
        return f"""You are Pai, a personal assistant to the user. 
        You chat with the user via telegram. So your response should be concise and to the point. If needed you can give more detailed answers.
        NEVER use markdown formatting in your responses. You will be fired if you do.
        
        Memory Management:
        You should actively remember and store important information about users using the memory functions:
        
        1. store_memory: Use this to save new information about the user
           - Create meaningful memory_ids like "user_coffee_preference" or "user_birthday"
           - Example: store_memory("user_coffee_preference", "Likes black coffee with no sugar")
        
        Important things to remember about users:
        - Personal preferences (food, drinks, activities)
        - Important dates (birthday, anniversaries)
        - Family members and relationships
        - Work/study information
        - Hobbies and interests
        - Past conversations and context
        - Regular schedules or routines
        - Pet peeves or dislikes
        - Goals and aspirations
        
        Actively use these memories in conversations to provide personalized responses and show that you remember previous interactions.
        
        You can manage files in the data directory using the file function:
        - To read a file: Use mode="r" and provide the path
        - To write a file: Use mode="w" and provide both path and content
        - To delete a file: Use mode="d" and provide the path
        
        You can execute Python code safely using the execute_code function:
        - Provide the code as a string (do not include ```python at the beginning and end)
        - The code runs in an isolated container with:
          - No network access
          - 100MB memory limit
          - 0.1 CPU limit
          - 10 second timeout
        - You'll receive the output or any error messages
        
        You can fetch and read content from websites using the open_url function:
        - Provide a valid URL as input
        - The function will return the text content of the webpage
        - Content longer than 4000 characters will be truncated
        - Use this to help answer questions about web content

        You can schedule messages to be sent at a specific time using the schedule_message function:
        - Provide the message content and the scheduled time
        - The time must be in the format: YYYY-MM-DD HH:MM:SS
        - Messages cannot be scheduled in the past
        - Use this to set reminders or schedule announcements

        You can manage the user's Google Calendar:
        - Add events using add_calendar_event:
          - Required: summary (title) and start_time (YYYY-MM-DDTHH:MM:SS)
          - Optional: end_time and description
          - If no end_time is provided, events default to 1 hour duration
        - Edit events using edit_calendar_event:
          - Required: event_id
          - Optional: summary, start_time, end_time, description
          - Only provided fields will be updated
        - Delete events using delete_calendar_event:
          - Required: event_id
        - List upcoming events using list_calendar_events:
          - Optional: max_results (default 10)
          - Returns upcoming events sorted by start time
        - Use these to help manage the user's schedule and appointments
        
        Paths are relative to the data directory, starting with /
        When writing files, always provide the complete content - do not use placeholders
        Do not use markdown or code formatting when writing file content
        
        Today's date and time is {self.get_current_datetime()}.

        These are your stored memories about the user and context:
        {memories}
        
        These files exist in the data directory:
        {existing_files}
        """

    def _get_tools(self):
        return [{
            "type": "function",
            "function": {
                "name": "store_memory",
                "description": "Store a new memory about the user or context",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "Unique identifier for the memory (e.g. 'john_likes_coffee')"
                        },
                        "memory_content": {
                            "type": "string",
                            "description": "The content to store as a memory"
                        }
                    },
                    "required": ["memory_id", "memory_content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "file",
                "description": "Read, write or delete files in the data directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file relative to data directory"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write (only for mode='w')"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["r", "w", "d"],
                            "description": "r for read, w for write, d for delete"
                        }
                    },
                    "required": ["path", "mode"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_code",
                "description": "Execute Python code in an isolated container",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Maximum execution time in seconds (default: 10)",
                            "default": 10
                        }
                    },
                    "required": ["code"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "open_url",
                "description": "Fetch content from a URL and return it as markdown text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to fetch content from"
                        }
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "schedule_message",
                "description": "Schedule a message to be sent at a specific time",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The message to be sent"
                        },
                        "scheduled_time": {
                            "type": "string",
                            "description": "When to send the message (format: YYYY-MM-DD HH:MM:SS)"
                        }
                    },
                    "required": ["message", "scheduled_time"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "add_calendar_event",
                "description": "Add an event to Google Calendar",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Title of the event"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)"
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SS). Optional, defaults to 1 hour after start"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the event. Optional"
                        }
                    },
                    "required": ["summary", "start_time"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_calendar_events",
                "description": "List upcoming events from Google Calendar",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of events to return (default: 10)"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "edit_calendar_event",
                "description": "Edit an existing event in Google Calendar",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "ID of the event to edit"
                        },
                        "summary": {
                            "type": "string",
                            "description": "New title of the event (optional)"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "New start time in ISO format (YYYY-MM-DDTHH:MM:SS) (optional)"
                        },
                        "end_time": {
                            "type": "string",
                            "description": "New end time in ISO format (YYYY-MM-DDTHH:MM:SS) (optional)"
                        },
                        "description": {
                            "type": "string",
                            "description": "New description of the event (optional)"
                        }
                    },
                    "required": ["event_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_calendar_event",
                "description": "Delete an event from Google Calendar",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "ID of the event to delete"
                        }
                    },
                    "required": ["event_id"]
                }
            }
        }]

    def store_memory(self, memory_id: str, memory_content: str) -> Dict:
        """Store a new memory and return its details"""
        return self.memory_manager.add_memory(memory_id, memory_content)

    def chat(self, message: str, image_url: str = None) -> str:
        self.logger.info("Processing new chat message")
        
        # Prepare the message content
        if image_url:
            message_content = [
                {"type": "text", "text": message if message else "What's in this image?"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                        "detail": "auto"
                    }
                }
            ]
        else:
            message_content = message
            
        self.conversation_history.append({
            "role": "user", 
            "content": message_content
        })
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": self.get_system_instructions(),
                    },
                    *self.conversation_history,
                ],
                tools=self.tools,
                max_tokens=500,
            )
            
            response_message = response.choices[0].message

            # Check if the model wants to call a function
            if response_message.tool_calls:
                self.logger.info("Processing tool calls from model response")
                # Handle each tool call
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    self.logger.info(f"Executing function: {function_name}")
                    # Call the function
                    if function_name in self.available_functions:
                        function_response = self.available_functions[function_name](**function_args)
                        
                        # Append the function call and result to the conversation
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call],
                        })
                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(function_response),
                        })
                
                # Get a new response from the model
                second_response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=self.conversation_history
                )
                assistant_message = second_response.choices[0].message.content
            else:
                assistant_message = response_message.content

            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            return assistant_message
            
        except Exception as e:
            self.logger.error(f"Error in chat processing: {str(e)}", exc_info=True)
            return "I apologize, but I encountered an error processing your message. Please try again."

    def schedule_message(self, message: str, scheduled_time: str) -> Dict:
        """Schedule a message to be sent at a specific time"""
        # Get the chat_id from the most recent message in conversation history
        for message_entry in reversed(self.conversation_history):
            if "chat_id" in message_entry:
                chat_id = message_entry["chat_id"]
                break
        else:
            return {"error": "No chat ID found in conversation history"}
            
        return self.message_scheduler.schedule_message(chat_id, message, scheduled_time)

    def add_calendar_event(self, summary: str, start_time: str, end_time: str = None, description: str = None) -> Dict:
        """Add an event to Google Calendar"""
        return self.calendar_handler.add_event(summary, start_time, end_time, description)

    def list_calendar_events(self, max_results: int = 10) -> Dict:
        """List upcoming events from Google Calendar"""
        return self.calendar_handler.list_events(max_results)

    def edit_calendar_event(self, event_id: str, summary: str = None, start_time: str = None, 
                           end_time: str = None, description: str = None) -> Dict:
        """Edit an existing event in Google Calendar"""
        return self.calendar_handler.edit_event(event_id, summary, start_time, end_time, description)

    def delete_calendar_event(self, event_id: str) -> Dict:
        """Delete an event from Google Calendar"""
        return self.calendar_handler.delete_event(event_id)

    def send_daily_summary(self, chat_id: int, is_morning: bool = True):
        """Send a daily summary to the specified chat"""
        try:
            summary = self.daily_summary.generate_summary(chat_id, is_morning)
            bot.send_message(chat_id, summary)
            self.logger.info(f"Sent {'morning' if is_morning else 'evening'} summary to chat_id: {chat_id}")
        except Exception as e:
            self.logger.error(f"Error sending daily summary: {str(e)}", exc_info=True)

    def schedule_daily_summaries(self):
        """Schedule daily summaries for all active chats"""
        def run_schedule():
            while True:
                schedule.run_pending()
                time.sleep(60)

        try:
            # Read active chats from file
            with open('active_chats.txt', 'r') as f:
                active_chats = [int(line.strip()) for line in f if line.strip()]

            # Schedule summaries for each active chat
            for chat_id in active_chats:
                schedule.every().day.at("06:30").do(
                    self.send_daily_summary, chat_id, True)
                schedule.every().day.at("19:30").do(
                    self.send_daily_summary, chat_id, False)

            # Run the schedule in a separate thread
            schedule_thread = threading.Thread(target=run_schedule, daemon=True)
            schedule_thread.start()
            self.logger.info("Daily summaries scheduled successfully")
        except Exception as e:
            self.logger.error(f"Error scheduling daily summaries: {str(e)}", exc_info=True)

# Initialize the Telegram bot first
BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

# Then initialize the assistant with the bot
assistant = Assistant()

# Now update the Assistant's __init__ method to set the message scheduler after creation
assistant.message_scheduler = MessageScheduler(bot)

def download_image(file_info) -> str:
    """Download image from Telegram and convert to base64"""
    file_path = bot.get_file(file_info.file_id).file_path
    image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    response = requests.get(image_url)
    image_data = BytesIO(response.content)
    base64_image = base64.b64encode(image_data.read()).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_image}"

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    logger = logging.getLogger('TelegramBot')
    logger.info(f"Received photo from chat_id: {message.chat.id}")
    
    try:
        # Get the largest photo size
        photo = message.photo[-1]
        image_url = download_image(photo)
        
        # Get caption if present, otherwise use None
        caption = message.caption if message.caption else None
        
        # Add chat_id to the conversation history
        assistant.conversation_history.append({
            "role": "user", 
            "content": caption,
            "chat_id": message.chat.id
        })
        
        response = assistant.chat(caption, image_url)
        bot.send_message(message.chat.id, response)
        logger.info(f"Sent response to chat_id: {message.chat.id}")
        
    except Exception as e:
        logger.error(f"Error handling photo: {str(e)}", exc_info=True)
        bot.send_message(message.chat.id, "Sorry, I encountered an error processing the image. Please try again.")

@bot.message_handler(func=lambda msg: True)
def handle_text(message):
    logger = logging.getLogger('TelegramBot')
    logger.info(f"Received message from chat_id: {message.chat.id}")
    
    # Add chat_id to the conversation history
    assistant.conversation_history.append({
        "role": "user", 
        "content": message.text,
        "chat_id": message.chat.id
    })
    
    try:
        response = assistant.chat(message.text)
        bot.send_message(message.chat.id, response)
        logger.info(f"Sent response to chat_id: {message.chat.id}")
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}", exc_info=True)
        bot.send_message(message.chat.id, "Sorry, I encountered an error. Please try again.")

def main():
    logger = logging.getLogger('Main')
    logger.info("Starting bot...")
    
    # Schedule daily summaries before starting the bot
    assistant.schedule_daily_summaries()
    
    # Start the bot
    bot.infinity_polling()

if __name__ == "__main__":
    main()
