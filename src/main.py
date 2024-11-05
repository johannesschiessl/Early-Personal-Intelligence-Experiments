from openai import OpenAI
from utils.telegram import TelegramBot
from utils.conversations import Conversations

class Assistant:
    def __init__(self):
        self.client = OpenAI()
        self.conversations = Conversations()
        self.system_prompt = """You are a helpful AI assistant. You aim to provide clear, 
        accurate, and helpful responses while maintaining a friendly and professional tone."""
        
    def handle_message(self, chat_id: int, message: str) -> str:
        """Process incoming messages and return AI response"""
        self.conversations.add(chat_id, "user", message)
        
        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.conversations.get(chat_id))
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message.content
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
    