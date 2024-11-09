import os
import time
import telebot
from dotenv import load_dotenv


def send_msg(msg):
    bot_token = os.getenv('PERSONAL_TELEGRAM_TOKEN')
    personal_bot = telebot.TeleBot(bot_token)
    personal_id = int(os.getenv('PERSONAL_ID'))

    # Sending message with retry mechanism
    max_retries = 5
    delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            personal_bot.send_message(personal_id, msg)
            break  # Exit loop if the message was sent successfully
        except ConnectionError as e:
            if attempt < max_retries - 1:
                print(f"Connection error: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                print(f"Failed to send message after {max_retries} attempts. Error: {e}")
