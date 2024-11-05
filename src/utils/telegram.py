import os
import logging
import telebot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('TelegramBot')

class TelegramBot:
    def __init__(self, message_handler):
        """
        Initialize Telegram bot
        
        Args:
            message_handler: Callback function to handle incoming messages
                           Should accept (chat_id, message_text) and return response text
        """
        self.BOT_TOKEN = os.environ.get('BOT_TOKEN')
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable not set")
            
        self.bot = telebot.TeleBot(self.BOT_TOKEN)
        self.message_handler = message_handler
        self._setup_handlers()

    def _setup_handlers(self):
        @self.bot.message_handler(func=lambda msg: True)
        def handle_message(message):
            logger.info(f"Received message from chat_id: {message.chat.id}")
            try:
                response = self.message_handler(message.chat.id, message.text)
                self.bot.send_message(message.chat.id, response)
                logger.info(f"Sent response to chat_id: {message.chat.id}")
            except Exception as e:
                logger.error(f"Error handling message: {str(e)}", exc_info=True)
                self.bot.send_message(message.chat.id, "Sorry, I encountered an error. Please try again.")

    def start(self):
        """Start the Telegram bot"""
        logger.info("Starting bot...")
        self.bot.infinity_polling()
