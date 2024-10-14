import threading
import asyncio
from datetime import datetime
import logging
from main_log_config import setup_logger

setup_logger()

global_stop = threading.Event()
sent_messages = []

async def stopper_setter():
    while True:  # Keep running in a loop
        h, m, s = datetime.now().strftime('%H'), datetime.now().strftime('%M'), datetime.now().strftime('%S')
        if int(h) == 16 and int(m) == 48 and int(s) == 0 and not global_stop.is_set():
            logging.info(f"⚙️ STOPPER SET!")
            global_stop.set()
            break  # Break out of the loop after setting the stopper
        await asyncio.sleep(0.1)  # Use asyncio sleep for non-blocking behavior
