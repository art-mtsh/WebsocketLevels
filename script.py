import os
import time
import sys
import telebot
import threading
from dotenv import load_dotenv
from datetime import datetime
from threading import Thread, Event
from modules.modules import klines, order_book
from modules.get_pairsV5 import get_pairs
from modules.bot_handling import start_bot
from modules.depth_check import depth_check
from modules.clean_old_pngs import clean_old_files

PERSONAL_TELEGRAM_TOKEN = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_bot = telebot.TeleBot(PERSONAL_TELEGRAM_TOKEN)
personal_id = int(os.getenv('PERSONAL_ID'))

stop_event = Event()

os.environ['BINANCE_SENT'] = ""
os.environ['FILTERED'] = ""
os.environ['IN_WORK'] = ""
os.environ['RELOAD_TIMESTAMP'] = ""
os.environ['BOT_STATE'] = "run"


def search(symbol):
    levels_f = {}
    levels_s = {}

    static_f = []
    static_s = []

    f_tits_levels = set()
    s_tits_levels = set()

    c_room = int(os.getenv('STARTING_ROOM'))  # стартова кімната з пошуку двох точок

    while not stop_event.is_set():
        if os.getenv('BOT_STATE') == "run":
            for market_type in ["f", "s"]:
                market_type_verbose = 'FUTURES' if market_type == 'f' else 'SPOT'

                depth = order_book(symbol, 500, market_type)
                the_klines = klines(symbol, "1m", 100, market_type)

                if depth and the_klines:

                    c_time, c_open, c_high, c_low, c_close, avg_vol = the_klines[0], the_klines[1], the_klines[2], the_klines[3], the_klines[4], the_klines[5]
                    depth = depth[1]  # [ціна, об'єм]

                    avg_atr_per = [(c_high[-c] - c_low[-c]) / (c_close[-c] / 100) for c in range(30)]
                    avg_atr_per = float('{:.2f}'.format(sum(avg_atr_per) / len(avg_atr_per)))

                    tits_levels = f_tits_levels if market_type == 'f' else s_tits_levels
                    # пошук екстремуму, а потім сайзу на ньому
                    for i in range(c_room, len(c_time)):

                        check_list = c_high[-i: -1]
                        max_indices = [i for i, v in enumerate(check_list) if v == max(check_list)]

                        if len(max_indices) > 1 and max(check_list) not in check_list[:5]:
                            for g in range(1, len(max_indices)):
                                # Get the sublist between the two max values
                                window = check_list[max_indices[g - 1] + 1:max_indices[g]]
                                # Check if there are 2 or more smaller values in the window
                                if len(window) >= 5 and all(v <= max(check_list) for v in window):
                                    tits_levels.add(max(check_list))

                        check_list = c_low[-i: -1]
                        min_indices = [i for i, v in enumerate(check_list) if v == min(check_list)]

                        if len(min_indices) > 1 and min(check_list) not in check_list[:5]:
                            for g in range(1, len(min_indices)):
                                # Get the sublist between the two max values
                                window = check_list[min_indices[g - 1] + 1:min_indices[g]]
                                # Check if there are 2 or more smaller values in the window
                                if len(window) >= 5 and all(v >= min(check_list) for v in window):
                                    tits_levels.add(min(check_list))

            #                 the_level = min(check_list)
            #                 d = depth_check(symbol, the_level, i, depth, c_time, avg_vol, c_close, avg_atr_per, market_type, market_type_verbose, levels_f, levels_s, static_f, static_s)
            #                 if isinstance(d, dict):
            #                     levels_f.update(d) if market_type == "f" else levels_s.update(d)
            #                 elif isinstance(d, float):
            #                     static_f.append(d) if market_type == "f" else static_s.append(d)
            #
            #     elif market_type == "f" and (depth is None or the_klines is None):
            #         personal_message = f"⛔️ Main file. Error in {symbol} ({market_type}) data!"
            #         print(personal_message)
            #         personal_bot.send_message(personal_id, personal_message)
            #
            # time_log = int(os.getenv('TIME_LOG'))
            # if time_log > 0:
            #     print(f"{datetime.now().strftime('%H:%M:%S')} {symbol} levels: {len(levels_f)}/{len(levels_s)}")
            #     sys.stdout.flush()

            if s_tits_levels:
                print(symbol, ' spot: ', s_tits_levels)
            if f_tits_levels:
                print(symbol, ' futures: ', f_tits_levels)

            reload_time = int(os.getenv('RELOAD_TIME', 60))
            time.sleep(reload_time)

def monitor_time_and_control_threads():
    global stop_event
    while True:
        current_minute = int(datetime.now().strftime('%M'))
        if current_minute != 59:
            tr = len([thread.name for thread in threading.enumerate() if thread.is_alive()])
            personal_message = (f"⚙️ ({tr} threads) Current time is {datetime.now().strftime('%H:%M:%S')}. We starting!")
            print(personal_message)

            stop_event.clear()
            clean_old_files('.', prefix='FT_')
            pairs = get_pairs()

            the_threads = []
            for pair in pairs:
                thread = Thread(target=search, args=(pair,))
                thread.start()
                the_threads.append(thread)

            tr = len([thread.name for thread in threading.enumerate() if thread.is_alive()])
            personal_message = (f"⚙️ ({tr} threads) Search started!")
            print(personal_message)

            while not int(datetime.now().strftime('%M')) == 59:
                time.sleep(1)

            tr = len([thread.name for thread in threading.enumerate() if thread.is_alive()])
            personal_message = (f"⚙️ ({tr} threads) Current time is {datetime.now().strftime('%H:%M:%S')}. Signal to stop threads sent.")
            print(personal_message)

            # stop_event.set()
            # for thread in the_threads:
            #     thread.join()

            tr = len([thread.name for thread in threading.enumerate() if thread.is_alive()])
            personal_message = (f"⚙️ ({tr} threads) All thread have been stopped. Waiting to restart.")
            print(personal_message)

            time.sleep(60)

        time.sleep(1)


if __name__ == '__main__':
    load_dotenv('params.env')
    load_dotenv('.env')

    bot_thread = Thread(target=start_bot)
    bot_thread.start()

    monitor_time_and_control_threads()
