import os
import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot.apihelper import ApiException
import requests
from dotenv import load_dotenv

load_dotenv('keys.env')

bot_token = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_id = int(os.getenv('PERSONAL_ID'))
personal_bot = AsyncTeleBot(bot_token)

# Спільний сет для повідомлень
messages_to_send = set()

async def async_bot_message(msg):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await personal_bot.send_message(personal_id, msg)
            return None  # Успішне надсилання, виходимо з функції
        except (requests.exceptions.ConnectionError, ApiException) as e:
            print(f"Error sending message: {e}. Attempt {attempt + 1} of {max_retries}")
            await asyncio.sleep(5)  # Затримка між спробами

    print("Failed to send message after 3 attempts. Continuing execution.")
    return None

# Функція-обробник для відправлення повідомлень з сету
async def message_handler():
    while True:
        if messages_to_send:
            async with asyncio.Lock():
                messages = list(messages_to_send)  # Копіюємо повідомлення для відправки
                messages_to_send.clear()  # Очищуємо сет

            print(f'Okay we need to send this messages: {messages}. messages_to_send set (after clearance): {messages_to_send}')

            for msg in messages:
                await async_bot_message(msg)  # Відправляємо кожне повідомлення

        await asyncio.sleep(0.1)  # Перевіряємо нові повідомлення кожні 0.1 секунди