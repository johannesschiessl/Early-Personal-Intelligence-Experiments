from openai import OpenAI
from utils.telegram import TelegramBot

class Assistant:
    def __init__(self):
        self.client = OpenAI()
        
    def handle_message(self, chat_id: int, message: str) -> str:
        """Process incoming messages and return AI response"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": message
                }],
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error getting AI response: {str(e)}")
            return "Sorry, I encountered an error. Please try again."

def main():
    assistant = Assistant()
    
    bot = TelegramBot(message_handler=assistant.handle_message)
    
    bot.start()

if __name__ == "__main__":
    main()
    