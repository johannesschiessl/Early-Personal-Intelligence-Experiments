from openai import OpenAI
from utils.telegram import TelegramBot
from utils.conversations import Conversations
from utils.read_memories import read_memories
from tools.memories import Memory
import logging
import json

logging.basicConfig(
    filename='tool_calls.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class Assistant:
    def __init__(self):
        self.client = OpenAI()
        self.conversations = Conversations()
        self.memory = Memory()
        
    @property
    def system_prompt(self) -> str:
        """Dynamic system prompt that includes available tools and memories"""
        base_prompt = """You are a helpful AI assistant. You aim to provide clear, 
        accurate, and helpful responses while maintaining a friendly and professional tone.
        
        Available Tools:
        1. Memory Tool:
           - To create/update a memory: memory(mode='w', id='unique_id', content='memory content')
           - To delete a memory: memory(mode='d', id='unique_id')
           
           When creating memory_ids, use descriptive names like 'user_preferences', 'learning_style', etc.
           Always include the relevant context in the memory_id.
        """
        return base_prompt

    def _get_tools(self) -> list:
        """Define available tools for the assistant"""
        return [{
            "type": "function",
            "function": {
                "name": "memory",
                "description": "Store, update or delete memories",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": ["w", "d"],
                            "description": "Write ('w') or delete ('d') mode"
                        },
                        "id": {
                            "type": "string",
                            "description": "Unique identifier for the memory (e.g., 'user_preferences')"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to store (required for write mode)"
                        }
                    },
                    "required": ["mode", "id"]
                }
            }
        }]
        
    def handle_message(self, chat_id: int, message: str) -> str:
        """Process incoming messages and return AI response"""
        self.conversations.add(chat_id, "user", message)
        
        try:
            memories = read_memories(chat_id)
            memories_prompt = "\nExisting Memories:\n"
            for memory_id, content in memories.items():
                memories_prompt += f"- {memory_id}: {content}\n"
            
            messages = [
                {"role": "system", "content": self.system_prompt + memories_prompt}
            ]
            messages.extend(self.conversations.get(chat_id))
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=self._get_tools(),
                tool_choice="auto",
                max_tokens=500
            )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                logging.info(f"Chat ID {chat_id} - Tool calls detected: {len(tool_calls)}")
                messages.append({
                    "role": "assistant",
                    "content": response_message.content,
                    "tool_calls": tool_calls
                })
                
                for tool_call in tool_calls:
                    if tool_call.function.name == "memory":
                        args = json.loads(tool_call.function.arguments)
                        logging.info(
                            f"Chat ID {chat_id} - Memory tool call:\n"
                            f"Function: {tool_call.function.name}\n"
                            f"Arguments: {json.dumps(args, indent=2)}"
                        )
                        
                        result = self.memory(
                            mode=args["mode"],
                            memory_id=args["id"],
                            chat_id=chat_id,
                            content=args.get("content")
                        )
                        
                        logging.info(
                            f"Chat ID {chat_id} - Memory tool result:\n"
                            f"{json.dumps(result, indent=2)}"
                        )
                        
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": "memory",
                            "content": json.dumps(result)
                        })
                
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=500
                )
                assistant_message = response.choices[0].message.content
            else:
                assistant_message = response_message.content
            
            self.conversations.add(chat_id, "assistant", assistant_message)
            return assistant_message
            
        except Exception as e:
            print(f"Error getting AI response: {str(e)}")
            return "Sorry, I encountered an error. Please try again."

def main():
    assistant = Assistant()
    bot = TelegramBot(message_handler=assistant.handle_message)
    bot.start()

if __name__ == "__main__":
    main()
    