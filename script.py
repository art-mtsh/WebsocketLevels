import logging
import asyncio
from dotenv import load_dotenv
from modules.get_pairsV5 import get_pairs, split_list
from modules.mod_market_depth_listener import listen_market_depth
from main_log_config import setup_logger
from modules.mod_levels_search import levels_threads, dropped_levels, tracked_levels
from modules.global_stopper import global_stop, stopper_setter, sent_messages

setup_logger()

# Define the lock
tracked_levels_lock = asyncio.Lock()

async def monitor_time_and_control_threads():
    while True:
        logging.info(f"⚙️ New loop is started.")
        pairs_lists = get_pairs()
        levels_pairs = split_list(pairs_lists, 10)

        levels_task = asyncio.create_task(levels_threads(levels_pairs))
        stopper_task = asyncio.create_task(stopper_setter())
        listener_task = asyncio.create_task(listen_market_depth(pairs_lists))

        await stopper_task
        await levels_task
        await listener_task

        logging.info('⚙️ All asyncs done their work! Cleaning levels...')
        async with tracked_levels_lock:
            dropped_levels.clear()
            tracked_levels.clear()
            global_stop.clear()
            sent_messages.clear()


if __name__ == '__main__':
    load_dotenv('params.env')
    asyncio.run(monitor_time_and_control_threads())
