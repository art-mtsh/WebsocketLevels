import os
import threading
import logging
import asyncio
import time
import telebot
from datetime import datetime
from dotenv import load_dotenv
from modules.get_pairsV5 import combined_klines
from main_log_config import setup_logger
from modules.global_stopper import global_stop
from modules.get_pairsV5 import split_list

setup_logger()

tracked_levels = {}
dropped_levels = set()
load_dotenv('keys.env')

bot_token = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_bot = telebot.TeleBot(bot_token)
personal_id = int(os.getenv('PERSONAL_ID'))


def upper_levels_check(c_high, i, w, complexity):
    check_list = c_high[-i: -1]
    check_list_max = max(check_list)
    max_indices = [b for b, v in enumerate(check_list[4:-w - 1]) if v == check_list_max]

    if len(max_indices) > 1:
        for g in range(1, len(max_indices)):
            window = check_list[max_indices[g - 1] + 1:max_indices[g]]
            if len(window) >= w:  # and all(v <= check_list_max for v in window):
                return check_list_max

    wiggle_room = float(os.getenv('WIGGLE_ROOM_ONE', 0.04)) / 100
    max_indices = [b for b, v in enumerate(check_list[4:-w - 1]) if check_list_max >= v >= check_list_max - check_list_max * wiggle_room]
    if len(max_indices) > 1 and complexity > 1:
        for g in range(1, len(max_indices)):
            window = check_list[max_indices[g - 1] + 1:max_indices[g]]
            if len(window) >= w and all(v <= check_list_max for v in window):
                return check_list_max

    wiggle_room = float(os.getenv('WIGGLE_ROOM_TWO', 0.08)) / 100
    max_indices = [b for b, v in enumerate(check_list[4:-w - 1]) if check_list_max >= v >= check_list_max - check_list_max * wiggle_room]
    if len(max_indices) > 2 and complexity > 2:
        for g in range(1, len(max_indices)):
            window = check_list[max_indices[g - 1] + 1:max_indices[g]]
            if len(window) >= w and all(v <= check_list_max for v in window):
                return check_list_max


def lower_levels_check(c_low, i, w, complexity):
    check_list = c_low[-i: -1]
    check_list_min = min(check_list)
    min_indices = [b for b, v in enumerate(check_list[4:-w - 1]) if v == check_list_min]

    if len(min_indices) > 1:
        for g in range(1, len(min_indices)):
            window = check_list[min_indices[g - 1] + 1:min_indices[g]]
            if len(window) >= w:  # and all(v >= check_list_min for v in window):
                return check_list_min

    wiggle_room = float(os.getenv('WIGGLE_ROOM_ONE', 0.04)) / 100
    min_indices = [b for b, v in enumerate(check_list[4:-w - 1]) if check_list_min <= v <= check_list_min + check_list_min * wiggle_room]
    if len(min_indices) > 1 and complexity > 1:
        for g in range(1, len(min_indices)):
            window = check_list[min_indices[g - 1] + 1:min_indices[g]]
            if len(window) >= w and all(v >= check_list_min for v in window):
                return check_list_min

    wiggle_room = float(os.getenv('WIGGLE_ROOM_TWO', 0.08)) / 100
    min_indices = [b for b, v in enumerate(check_list[4:-w - 1]) if check_list_min <= v <= check_list_min + check_list_min * wiggle_room]
    if len(min_indices) > 2 and complexity > 2:
        for g in range(1, len(min_indices)):
            window = check_list[min_indices[g - 1] + 1:min_indices[g]]
            if len(window) >= w and all(v >= check_list_min for v in window):
                return check_list_min


def levels_search(coins, complexity):
    for coin_data in coins:
        symbol, ts_percent_futures, ts_percent_spot, x_atr_per = coin_data[0], coin_data[1], coin_data[2], coin_data[3]

        minute_spot_avg_volume = 0.0
        minute_futures_avg_volume = 0.0
        c_room = int(os.getenv('STARTING_ROOM'))  # стартова кімната з пошуку двох точок
        frames = {'1m': 5, '5m': 1, '15m': 1}

        for timeframe, window in frames.items():
            spot_klines = combined_klines(symbol, timeframe, 99, 'spot') if ts_percent_spot != 0 else None
            futu_klines = combined_klines(symbol, timeframe, 99, 'futures') if ts_percent_futures != 0 else None

            if spot_klines:
                s_high, s_low, s_close, avg_vol = spot_klines[2], spot_klines[3], spot_klines[4], spot_klines[5]
                if timeframe == '1m':
                    minute_spot_avg_volume = int(avg_vol)
                for i in range(c_room, len(s_high)):
                    upper = upper_levels_check(s_high, i, window, complexity)
                    lower = lower_levels_check(s_low, i, window, complexity)
                    if upper and futu_klines and (symbol, timeframe, 'spot', upper, max(futu_klines[2][-i: -1]), 'up') not in tracked_levels.keys():
                        tracked_levels[(symbol, timeframe, 'spot', upper, max(futu_klines[2][-i: -1]), 'up')] = minute_spot_avg_volume, x_atr_per

                    if lower and futu_klines and (symbol, timeframe, 'spot', lower, min(futu_klines[3][-i: -1]), 'dn') not in tracked_levels.keys():
                        tracked_levels[(symbol, timeframe, 'spot', lower, min(futu_klines[3][-i: -1]), 'dn')] = minute_spot_avg_volume, x_atr_per

            if not futu_klines:
                logging.error(f"⛔️ Main file. Error in {symbol} futures klines data!")
            else:
                f_high, f_low, f_close, avg_vol = futu_klines[2], futu_klines[3], futu_klines[4], futu_klines[5]
                if timeframe == '1m':
                    minute_futures_avg_volume = int(avg_vol)
                for i in range(c_room, len(f_high)):
                    upper = upper_levels_check(f_high, i, window, complexity)
                    lower = lower_levels_check(f_low, i, window, complexity)
                    if upper and (symbol, timeframe, 'futures', upper, upper, 'up') not in tracked_levels.keys():
                        tracked_levels[(symbol, timeframe, 'futures', upper, upper, 'up')] = minute_futures_avg_volume, x_atr_per

                    if lower and (symbol, timeframe, 'futures', lower, lower, 'dn') not in tracked_levels.keys():
                        tracked_levels[(symbol, timeframe, 'futures', lower, lower, 'dn')] = minute_futures_avg_volume, x_atr_per

        time.sleep(5)  # every 6 seconds 10 threads do 3 requests with 3 weights, which is 900- weights per minute


async def levels_threads(coins_list):
    complexity = 1 if len(coins_list) >= 50 else 2 if len(coins_list) >= 25 else 3
    logging.info(f"⚙️ Starting levels asyncio. Complexity: {complexity} ({len(coins_list)} coins)")
    coins_list = split_list(coins_list, 10)

    the_threads = []
    for coins in coins_list:
        thread = threading.Thread(target=levels_search, args=(coins, complexity,))
        thread.start()
        the_threads.append(thread)
    for thread in the_threads:
        await asyncio.to_thread(thread.join)
    msg = f'⚙️ Found {len(tracked_levels)} levels'

    logging.info(msg)
    # personal_bot.send_message(personal_id, msg)
    await asyncio.sleep(60)

    while not global_stop.is_set():
        m, s = datetime.now().strftime('%M'), datetime.now().strftime('%S')
        if int(m) % 5 == 0 and int(s) == 0:
            logging.info(f"⚙️ Refreshing levels. Complexity: {complexity} ({len(coins_list)} coins)")
            copy_levels = tracked_levels.copy()

            the_threads = []
            for coins in coins_list:
                thread = threading.Thread(target=levels_search, args=(coins, complexity,))
                thread.start()
                the_threads.append(thread)
            for thread in the_threads:
                await asyncio.to_thread(thread.join)
            msg = f'⚙️ Added {len(tracked_levels) - len(copy_levels)} levels, now tracked levels count: {len(tracked_levels)}'
            logging.info(msg)
            # personal_bot.send_message(personal_id, msg)
        await asyncio.sleep(0.1)

    logging.info(f"⚙️ Levels asyncio done its work.")
