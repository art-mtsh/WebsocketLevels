import os
import requests
import telebot
from dotenv import load_dotenv
from threading import Thread

# import logging
# from main_log_config import setup_logger
# setup_logger()

load_dotenv('keys.env')

bot_token = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_bot = telebot.TeleBot(bot_token)
personal_id = int(os.getenv('PERSONAL_ID'))

excluded = ['OMGUSDT', 'BTCUSDT', 'ETHUSDT', 'VANRYUSDT', 'BTCUSDT_250328', 'ETHUSDT_250328']


def calculate_pairs(pairs_dict, shared_results):
    ts_filter_s = float(os.getenv('TICKSIZE_FILTER_SPOT', 0.05))
    ts_filter_f = float(os.getenv('TICKSIZE_FILTER_FUTURES', 0.03))
    atr_filter = float(os.getenv('ATR_FILTER', 0.2))

    for symbol, ts in pairs_dict.items():

        request_limit_length = 99
        frame = '1m'
        futures_klines = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={frame}&limit={request_limit_length}'
        try:
            klines = requests.get(futures_klines)
            if klines.status_code == 200:
                response_length = len(klines.json()) if klines.json() is not None else 0
                if response_length == request_limit_length:
                    binance_candle_data = klines.json()
                    high = [float(i[2]) for i in binance_candle_data]
                    low = [float(i[3]) for i in binance_candle_data]
                    close = [float(i[4]) for i in binance_candle_data]

                    x_atr_per = [(high[-c] - low[-c]) / (close[-c] / 100) for c in range(request_limit_length)]
                    x_atr_per = sum(x_atr_per) / len(x_atr_per)
                    ts_percent_futures = float(ts[0]) / (close[-1] / 100)
                    ts_percent_spot = float(ts[1]) / (close[-1] / 100) if ts[1] else 0

                    if ts_percent_futures <= ts_filter_f and ts_percent_spot <= ts_filter_s and x_atr_per >= atr_filter:
                        result = [symbol, ts_percent_futures, ts_percent_spot, x_atr_per]
                        shared_results.append(result)

        except Exception as e:
            personal_message = f"⛔️ Error in downloading klines (get_pairs) for {symbol}: {e} {futures_klines}"
            personal_bot.send_message(personal_id, personal_message)
        # time.sleep(0)  # Throttle API requests to avoid overloading the system


def split_list(input_list: list, num_parts: int):
    if num_parts > len(input_list):
        num_parts = len(input_list)

    avg = len(input_list) // num_parts
    remainder = len(input_list) % num_parts
    result = []
    start = 0

    for i in range(num_parts):
        end = start + avg + (1 if i < remainder else 0)
        result.append(input_list[start:end])
        start = end

    return result


def split_dict(input_dict: dict, num_parts: int):
    avg = len(input_dict) // num_parts
    remainder = len(input_dict) % num_parts
    result = []
    start = 0

    for i in range(num_parts):
        end = start + avg + (1 if i < remainder else 0)
        result.append({k: input_dict[k] for k in list(input_dict)[start:end]})
        start = end

    return result


def get_pairs():
    personal_bot.send_message(personal_id, f"⚙️ Searching for pairs.")

    ts_dict = {}

    # ------ GET TOTAL COINS LIST ------
    futures_exchange_info_url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    response = requests.get(futures_exchange_info_url)
    response_data = response.json().get("symbols")

    for data in response_data:
        symbol = data['symbol']
        status = data['status']
        tick_size = data['filters'][0]['tickSize']
        if data['quoteAsset'] == "USDT" and symbol not in excluded and status == 'TRADING':
            ts_dict[symbol] = [float(tick_size), None]

    spot_exchange_info_url = "https://api.binance.com/api/v3/exchangeInfo"
    response = requests.get(spot_exchange_info_url)
    response_data = response.json().get("symbols")
    for data in response_data:
        symbol = data['symbol']
        status = data['status']
        tick_size = data['filters'][0]['tickSize']
        if symbol in ts_dict.keys() and status == 'TRADING':
            ts_dict[symbol][1] = float(tick_size)

    # ------ SPLIT COINS LIST TO 40 CHUNKS ------
    init_parts = int(os.getenv('INITIAL_THREADS_FOR_COINS_LIST', 50))
    list_of_dicts = split_dict(ts_dict, init_parts)

    # ------ GET LIST OF PAIRS WITH THEIR TS's AND ATR's ------
    shared_results = []
    pairs_threads = []

    for dict_of_pairs in list_of_dicts:
        pair_thread = Thread(target=calculate_pairs, args=(dict_of_pairs, shared_results))
        pairs_threads.append(pair_thread)
        pair_thread.start()

    for pair_thread in pairs_threads:
        pair_thread.join()  # Ensure all threads have finished

    # ------ FILTER COINS BY TS's AND ATR's ------
    result = [res for res in shared_results]
    result = sorted(result, key=lambda x: x[3], reverse=True)

    msg = f"⚙️ Pairs got: {len(result)}/{len(ts_dict)}: {result[-1][0]} ({round(result[-1][3], 2)}%) ... {result[0][0]} ({round(result[0][3], 2)}%)"
    personal_bot.send_message(personal_id, msg)

    return result


# if __name__ == '__main__':
#     get_pairs()


def combined_klines(symbol, frame, request_limit_length, market_type: str):
    futures_klines = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={frame}&limit={request_limit_length}'
    spot_klines = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={frame}&limit={request_limit_length}'

    url = futures_klines if market_type == "futures" else spot_klines
    response = requests.get(url)

    if response.status_code == 200:

        response_length = len(response.json()) if response.json() != None else 0

        if response_length == request_limit_length:
            binance_candle_data = response.json()
            c_time = list(float(i[0]) for i in binance_candle_data)
            c_open = list(float(i[1]) for i in binance_candle_data)
            c_high = list(float(i[2]) for i in binance_candle_data)
            c_low = list(float(i[3]) for i in binance_candle_data)
            c_close = list(float(i[4]) for i in binance_candle_data)
            c_volume = list(float(i[5]) for i in binance_candle_data)
            buy_volume = list(float(i[9]) for i in binance_candle_data)
            sell_volume = [c_volume[0] - buy_volume[0]]

            avg_vol = sum(c_volume) / len(c_volume)

            if len(c_open) != len(c_high) != len(c_low) != len(c_close) != len(c_volume):
                msg = (f"⛔️ Length error for klines data for {symbol} ({market_type}), status code {response.status_code}\n"
                       f"{url}")
                # if market_type == 'f': personal_bot.send_message(personal_id, msg)
                if market_type == 'f': print(msg)
            else:
                return [c_time, c_open, c_high, c_low, c_close, avg_vol, buy_volume, sell_volume]

        else:
            msg = (f"⛔️ Not enough ({response_length}/{request_limit_length}) klines data for {symbol} ({market_type}), status code {response.status_code}\n"
                   f"{url}")
            # if market_type == 'f': personal_bot.send_message(personal_id, msg)
            if market_type == 'f': print(msg)

    elif response.status_code == 429:
        msg = f"⛔️ {symbol} ({market_type}) LIMITS REACHED !!!! 429 CODE !!!!"
        # personal_bot.send_message(personal_id, msg)
        print(msg)

    else:
        msg = (f"⛔️ No klines data for {symbol} ({market_type}), status code {response.status_code}\n"
               f"{url}")
        # if market_type == 'f': personal_bot.send_message(personal_id, msg)
        if market_type == 'f': print(msg)
