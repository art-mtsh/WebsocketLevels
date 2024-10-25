import os
import threading
import asyncio
import time
from modules.bot_handler import messages_to_send
from datetime import datetime
from modules.get_pairsV5 import combined_klines
from modules.global_stopper import global_stop
from modules.get_pairsV5 import split_list

tracked_levels = {}
dropped_levels = set()


def upper_levels_check(c_high: list, c_close: float, x_atr_per, i: int, w: int):
    check_list = c_high[-i: -1]
    check_list_max = max(check_list)
    distance_validated = abs(check_list_max - c_close) / (c_close / 100) <= x_atr_per * 5

    if distance_validated:
        max_indices = [b for b, v in enumerate(check_list[4:-w - 1]) if v == check_list_max]

        if len(max_indices) > 1:
            for g in range(1, len(max_indices)):
                window = check_list[max_indices[g - 1] + 1:max_indices[g]]
                if len(window) >= w:  # and all(v <= check_list_max for v in window):
                    return check_list_max

        wiggle_room = float(os.getenv('WIGGLE_ROOM_ONE', 0.04)) / 100
        max_indices = [b for b, v in enumerate(check_list[4:-w - 1]) if check_list_max >= v >= check_list_max - check_list_max * wiggle_room]
        if len(max_indices) > 1:
            for g in range(1, len(max_indices)):
                window = check_list[max_indices[g - 1] + 1:max_indices[g]]
                if len(window) >= w and all(v <= check_list_max for v in window):
                    return check_list_max

        wiggle_room = float(os.getenv('WIGGLE_ROOM_TWO', 0.08)) / 100
        max_indices = [b for b, v in enumerate(check_list[4:-w - 1]) if check_list_max >= v >= check_list_max - check_list_max * wiggle_room]
        if len(max_indices) > 2:
            for g in range(1, len(max_indices)):
                window = check_list[max_indices[g - 1] + 1:max_indices[g]]
                if len(window) >= w and all(v <= check_list_max for v in window):
                    return check_list_max


def lower_levels_check(c_low: list, c_close: float, x_atr_per, i: int, w: int):
    check_list = c_low[-i: -1]
    check_list_min = min(check_list)
    distance_validated = abs(check_list_min - c_close) / (c_close / 100) <= x_atr_per * 5

    if distance_validated:
        min_indices = [b for b, v in enumerate(check_list[4:-w - 1]) if v == check_list_min]

        if len(min_indices) > 1:
            for g in range(1, len(min_indices)):
                window = check_list[min_indices[g - 1] + 1:min_indices[g]]
                if len(window) >= w:  # and all(v >= check_list_min for v in window):
                    return check_list_min

        wiggle_room = float(os.getenv('WIGGLE_ROOM_ONE', 0.04)) / 100
        min_indices = [b for b, v in enumerate(check_list[4:-w - 1]) if check_list_min <= v <= check_list_min + check_list_min * wiggle_room]
        if len(min_indices) > 1:
            for g in range(1, len(min_indices)):
                window = check_list[min_indices[g - 1] + 1:min_indices[g]]
                if len(window) >= w and all(v >= check_list_min for v in window):
                    return check_list_min

        wiggle_room = float(os.getenv('WIGGLE_ROOM_TWO', 0.08)) / 100
        min_indices = [b for b, v in enumerate(check_list[4:-w - 1]) if check_list_min <= v <= check_list_min + check_list_min * wiggle_room]
        if len(min_indices) > 2:
            for g in range(1, len(min_indices)):
                window = check_list[min_indices[g - 1] + 1:min_indices[g]]
                if len(window) >= w and all(v >= check_list_min for v in window):
                    return check_list_min


def levels_search(coins, wait_time):
    for coin_data in coins:
        symbol, ts_percent_futures, ts_percent_spot, x_atr_per = coin_data[0], coin_data[1], coin_data[2], coin_data[3]

        minute_spot_avg_volume = 0.0
        minute_futures_avg_volume = 0.0
        c_room = int(os.getenv('STARTING_ROOM'))  # стартова кімната з пошуку двох точок
        frames = {'1m': 5, '5m': 1, '15m': 1}

        for timeframe, window in frames.items():
            futu_klines = combined_klines(symbol, timeframe, 99, 'futures') if ts_percent_futures != 0 else None
            spot_klines = combined_klines(symbol, timeframe, 99, 'spot') if ts_percent_spot != 0 else None

            if not futu_klines:
                messages_to_send.add(f'Ticksize for {symbol}(futures) is missing!')
                continue
            elif isinstance(futu_klines, str):
                messages_to_send.add(futu_klines)
                continue
            else:
                f_high, f_low, f_close, avg_vol = futu_klines[2], futu_klines[3], futu_klines[4], futu_klines[5]
                if timeframe == '1m':
                    minute_futures_avg_volume = int(avg_vol)
                for i in range(c_room, len(f_high)):
                    upper = upper_levels_check(f_high, f_close[-1], x_atr_per, i, window)
                    lower = lower_levels_check(f_low, f_close[-1], x_atr_per, i, window)
                    if upper:
                        if not any(key[3] == upper for key in tracked_levels):
                            tracked_levels[(symbol, timeframe, "futures", upper, upper, "up")] = minute_futures_avg_volume, x_atr_per
                    if lower:
                        if not any(key[3] == lower for key in tracked_levels):
                            tracked_levels[(symbol, timeframe, "futures", lower, lower, "dn")] = minute_futures_avg_volume, x_atr_per

            if not spot_klines:
                print(f'Ticksize for {symbol}(spot) is missing!')
                continue
            elif isinstance(spot_klines, str):
                print(spot_klines)
                continue
            else:
                s_high, s_low, s_close, avg_vol = spot_klines[2], spot_klines[3], spot_klines[4], spot_klines[5]
                if timeframe == '1m':
                    minute_spot_avg_volume = int(avg_vol)
                for i in range(c_room, len(s_high)):
                    upper = upper_levels_check(s_high, s_close[-1], x_atr_per, i, window)
                    lower = lower_levels_check(s_low, s_close[-1], x_atr_per, i, window)
                    if upper:
                        if not any(key[3] == upper for key in tracked_levels):
                            tracked_levels[(symbol, timeframe, "spot", upper, max(futu_klines[2][-i: -1]), "up")] = minute_spot_avg_volume, x_atr_per
                    if lower:
                        if not any(key[3] == lower for key in tracked_levels):
                            tracked_levels[(symbol, timeframe, "spot", lower, min(futu_klines[3][-i: -1]), "dn")] = minute_spot_avg_volume, x_atr_per

        time.sleep(wait_time)


levels_lock = asyncio.Lock()


async def levels_threads(coins_top_list):
    coins_list = split_list(coins_top_list, 10)
    request_weight = len(coins_top_list) * 9
    wait_time = 1 if request_weight <= 1100 else 5

    the_threads = []
    for coins in coins_list:
        thread = threading.Thread(target=levels_search, args=(coins, wait_time,))
        thread.start()
        the_threads.append(thread)
    for thread in the_threads:
        await asyncio.to_thread(thread.join)

    await asyncio.sleep(60)

    while not global_stop.is_set():
        m, s = datetime.now().strftime('%M'), datetime.now().strftime('%S')
        if int(m) % 5 == 0 and int(s) == 0:

            async with levels_lock:
                tracked_levels.clear()
                dropped_levels.clear()
            print('Levels are cleared.')

            the_threads = []
            for coins in coins_list:
                thread = threading.Thread(target=levels_search, args=(coins, wait_time,))
                thread.start()
                the_threads.append(thread)
            for thread in the_threads:
                await asyncio.to_thread(thread.join)

            await asyncio.sleep(60)

        await asyncio.sleep(0.1)

    print(f"Levels asyncio done its work.")
