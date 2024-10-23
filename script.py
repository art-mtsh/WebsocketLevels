import os
import telebot
import asyncio
from dotenv import load_dotenv
from modules.get_pairsV5 import get_pairs, split_list
from modules.mod_market_depth_listener import listen_market_depth
from modules.mod_levels_search import levels_threads, dropped_levels, tracked_levels
from modules.global_stopper import global_stop, stopper_setter, sent_messages

# import logging
# from main_log_config import setup_logger
# setup_logger()

bot_token = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_bot = telebot.TeleBot(bot_token)
personal_id = int(os.getenv('PERSONAL_ID'))

tracked_levels_lock = asyncio.Lock()
semaphore = asyncio.Semaphore(5)

async def limited_task(task, *args):
    async with semaphore:
        return await task(*args)

async def monitor_time_and_control_threads():
    while True:
        print(f"New loop is started.")
        pairs_lists = get_pairs()

        levels_task = asyncio.create_task(limited_task(levels_threads, pairs_lists))
        stopper_task = asyncio.create_task(limited_task(stopper_setter))
        listener_task = asyncio.create_task(limited_task(listen_market_depth, pairs_lists))

        await stopper_task
        await levels_task
        await listener_task

        print('All asyncs done their work! Cleaning levels...')
        async with tracked_levels_lock:
            dropped_levels.clear()
            tracked_levels.clear()
            global_stop.clear()
            sent_messages.clear()



if __name__ == '__main__':
    load_dotenv('params.env')
    asyncio.run(monitor_time_and_control_threads())
