import os
import time
from telebot import TeleBot

# Initialize bot
bot_token = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_bot = TeleBot(bot_token, parse_mode='HTML', threaded=True)


def send_msg(msg):
    personal_id = int(os.getenv('PERSONAL_ID'))
    max_retries = 5
    delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            personal_bot.send_message(personal_id, msg)
            break
        except ConnectionError as e:
            if attempt < max_retries - 1:
                print(f"Connection error: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                print(f"Failed to send message after {max_retries} attempts. Error: {e}")

@personal_bot.message_handler(commands=['start'])
def send_welcome(message):
    if int(time.time()) - message.date > 5: return
    chat_id = message.chat.id
    personal_bot.send_message(chat_id, 'Welcome to bot!')

@personal_bot.message_handler(commands=['last_update'])
def handle_last_update(message):
    if int(time.time()) - message.date > 5: return
    chat_id = message.chat.id
    personal_bot.send_message(chat_id, os.getenv('msg_last_update', 'Not found!'))

@personal_bot.message_handler(commands=['tracked_levels'])
def handle_tracked_levels(message):
    if int(time.time()) - message.date > 5: return
    chat_id = message.chat.id
    personal_bot.send_message(chat_id, os.getenv('msg_tracked_levels', 'Not found!'))

@personal_bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    personal_bot.send_message(chat_id, 'No messages allowed!')

def poll():
    while True:
        try:
            personal_bot.polling()
        except Exception as e:
            print(f"Polling error: {e}. Restarting polling in 5 seconds...")
            time.sleep(5)
