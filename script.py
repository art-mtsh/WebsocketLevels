import sys
import traceback
import asyncio
from dotenv import load_dotenv
from modules.get_pairsV5 import get_pairs
from modules.mod_market_depth_listener import listen_market_depth
from modules.mod_levels_search import levels_threads, dropped_levels, tracked_levels
from modules.global_stopper import global_stop, stopper_setter, sent_messages
from modules.telegram_handler import send_msg

levels_lock = asyncio.Lock()
semaphore = asyncio.Semaphore(5)


# Define the global exception handler
def global_exception_handler(exctype, value, tb):
    # Format the error message
    error_message = ''.join(traceback.format_exception(exctype, value, tb))

    # Send the error message to Telegram
    try:
        send_msg(f"An error occurred:\n{error_message}")
    except Exception as notify_error:
        # In case of failure to send the message, print it to stderr
        print(f"Failed to notify via bot: {notify_error}", file=sys.stderr)

    # Also print the error to stderr for logging purposes
    sys.__excepthook__(exctype, value, tb)


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
        async with levels_lock:
            dropped_levels.clear()
            tracked_levels.clear()
            global_stop.clear()
            sent_messages.clear()


if __name__ == '__main__':
    sys.excepthook = global_exception_handler
    load_dotenv('params.env')
    load_dotenv('keys.env')
    asyncio.run(monitor_time_and_control_threads())
