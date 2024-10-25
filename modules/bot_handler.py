import os
import time
import telebot
from telebot.apihelper import ApiException
import requests

bot_token = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_id = int(os.getenv('PERSONAL_ID'))
personal_bot = telebot.TeleBot(bot_token)

def bot_message(msg):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            personal_bot.send_message(personal_id, msg)
            return None  # Успішне надсилання, виходимо з функції
        except (requests.exceptions.ConnectionError, ApiException) as e:
            print(f"Error sending message: {e}. Attempt {attempt + 1} of {max_retries}")
            time.sleep(5)  # Затримка між спробами

    print("Failed to send message after 3 attempts. Continuing execution.")
    return None
