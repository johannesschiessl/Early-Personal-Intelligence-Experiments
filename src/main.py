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
        }
        
        # message_scheduler will be set after initialization
        self.message_scheduler = None
        self.logger.info("Assistant initialization complete")

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
        
        You can store new memories using the store_memory function. Remember things about the user and context.
        
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
                        "memory_content": {
                            "type": "string",
                            "description": "The content to store as a memory"
                        }
                    },
                    "required": ["memory_content"]
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
        }]

    def store_memory(self, memory_content: str) -> Dict:
        """Store a new memory and return its ID"""
        memory_id = self.memory_manager.add_memory(memory_content)
        return {"memory_id": memory_id, "content": memory_content}

    def chat(self, message: str) -> str:
        self.logger.info("Processing new chat message")
        self.conversation_history.append({"role": "user", "content": message})
        
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

# Initialize the Telegram bot first
BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

# Then initialize the assistant with the bot
assistant = Assistant()

# Now update the Assistant's __init__ method to set the message scheduler after creation
assistant.message_scheduler = MessageScheduler(bot)

@bot.message_handler(func=lambda msg: True)
def chat(message):
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
    bot.infinity_polling()

if __name__ == "__main__":
    main()
