import sys
import time
from datetime import datetime
import websocket
import json
import threading
from queue import Queue
import telebot

TOKEN3 = '6077915522:AAFuMUVPhw-cEaX4gCuPOa-chVwwMTpsUz8'
bot3 = telebot.TeleBot(TOKEN3)

message_queue = Queue()

symbols = ["REEFUSDT", "ALTUSDT", "REZUSDT", "LISTAUSDT", "IOUSDT"]

# divs_log_1 = [0]
# divs_log_2 = [0]
# divs_log_3 = [0]
# divs_log_4 = [0]
# divs_log_5 = [0]

process_is_running = True


def on_message_binance(ws, message):
    global process_is_running

    now = datetime.now()
    last_second_digit = int(now.strftime('%M'))

    data = json.loads(message)
    data = data.get('data')
    symbol = data.get('s')
    bids = data.get('b')[0][0]  # найвища ціна
    asks = data.get('a')[0][0]  # найнижча ціна

    print(f"Binance {symbol} ask {asks}, bid {bids}")
    # message_queue.put(("Binance", symbol, bids, asks))

    if last_second_digit == 0:
        process_is_running = False
        ws.close()


# def process_messages():
#     last_message_time = None
#     last_message_text = [0, 0, 0, 0, 0]
#
#     data_storage = {
#         f'Binance-{symbols[0]}': [1, 1],
#         f'Binance-{symbols[1]}': [1, 1],
#         f'Binance-{symbols[2]}': [1, 1],
#         f'Binance-{symbols[3]}': [1, 1],
#         f'Binance-{symbols[4]}': [1, 1],
#         f'Bybit-{symbols[0]}': [1, 1],
#         f'Bybit-{symbols[1]}': [1, 1],
#         f'Bybit-{symbols[2]}': [1, 1],
#         f'Bybit-{symbols[3]}': [1, 1],
#         f'Bybit-{symbols[4]}': [1, 1],
#     }
#
#     symbol1_min_diver = 100
#     symbol2_min_diver = 100
#     symbol3_min_diver = 100
#     symbol4_min_diver = 100
#     symbol5_min_diver = 100
#
#     while process_is_running:
#
#         divs_storage = {
#             f'{symbols[0]}': [
#                 data_storage.get(f'Binance-{symbols[0]}')[0] - data_storage.get(f'Bybit-{symbols[0]}')[1],
#                 data_storage.get(f'Bybit-{symbols[0]}')[0] - data_storage.get(f'Binance-{symbols[0]}')[1]
#             ],
#             f'{symbols[1]}': [
#                 data_storage.get(f'Binance-{symbols[1]}')[0] - data_storage.get(f'Bybit-{symbols[1]}')[1],
#                 data_storage.get(f'Bybit-{symbols[1]}')[0] - data_storage.get(f'Binance-{symbols[1]}')[1]
#             ],
#             f'{symbols[2]}': [
#                 data_storage.get(f'Binance-{symbols[2]}')[0] - data_storage.get(f'Bybit-{symbols[2]}')[1],
#                 data_storage.get(f'Bybit-{symbols[2]}')[0] - data_storage.get(f'Binance-{symbols[2]}')[1]
#             ],
#             f'{symbols[3]}': [
#                 data_storage.get(f'Binance-{symbols[3]}')[0] - data_storage.get(f'Bybit-{symbols[3]}')[1],
#                 data_storage.get(f'Bybit-{symbols[3]}')[0] - data_storage.get(f'Binance-{symbols[3]}')[1]
#             ],
#             f'{symbols[4]}': [
#                 data_storage.get(f'Binance-{symbols[4]}')[0] - data_storage.get(f'Bybit-{symbols[4]}')[1],
#                 data_storage.get(f'Bybit-{symbols[4]}')[0] - data_storage.get(f'Binance-{symbols[4]}')[1]
#             ],
#         }
#
#         try:
#             source, symbol, bid, ask = message_queue.get()
#
#             bid = bid if bid != 0 else data_storage.get(f"{source}-{symbol}")[0]
#             ask = ask if ask != 0 else data_storage.get(f"{source}-{symbol}")[1]
#
#             data_storage.update({f"{source}-{symbol}": [float(bid), float(ask)]})
#
#         except Exception as e:
#             print(f"Error processing message: {e}")
#
#         finally:
#             message_queue.task_done()
#
#         symbol1_max_diver = max(divs_storage.get(f'{symbols[0]}')) / (max([max(data_storage.get(f'Binance-{symbols[0]}')),
#                                                                            max(data_storage.get(f'Bybit-{symbols[0]}'))]) / 100)
#         symbol2_max_diver = max(divs_storage.get(f'{symbols[1]}')) / (max([max(data_storage.get(f'Binance-{symbols[1]}')),
#                                                                            max(data_storage.get(f'Bybit-{symbols[1]}'))]) / 100)
#         symbol3_max_diver = max(divs_storage.get(f'{symbols[2]}')) / (max([max(data_storage.get(f'Binance-{symbols[2]}')),
#                                                                            max(data_storage.get(f'Bybit-{symbols[2]}'))]) / 100)
#         symbol4_max_diver = max(divs_storage.get(f'{symbols[3]}')) / (max([max(data_storage.get(f'Binance-{symbols[3]}')),
#                                                                            max(data_storage.get(f'Bybit-{symbols[3]}'))]) / 100)
#         symbol5_max_diver = max(divs_storage.get(f'{symbols[4]}')) / (max([max(data_storage.get(f'Binance-{symbols[4]}')),
#                                                                            max(data_storage.get(f'Bybit-{symbols[4]}'))]) / 100)
#
#         symbol1_max_diver = float('{:.2f}'.format(symbol1_max_diver))
#         symbol2_max_diver = float('{:.2f}'.format(symbol2_max_diver))
#         symbol3_max_diver = float('{:.2f}'.format(symbol3_max_diver))
#         symbol4_max_diver = float('{:.2f}'.format(symbol4_max_diver))
#         symbol5_max_diver = float('{:.2f}'.format(symbol5_max_diver))
#
#         if symbol1_min_diver > symbol1_max_diver:
#             symbol1_min_diver = symbol1_max_diver
#
#         if symbol2_min_diver > symbol2_max_diver:
#             symbol2_min_diver = symbol2_max_diver
#
#         if symbol3_min_diver > symbol3_max_diver:
#             symbol3_min_diver = symbol3_max_diver
#
#         if symbol4_min_diver > symbol4_max_diver:
#             symbol4_min_diver = symbol4_max_diver
#
#         if symbol5_min_diver > symbol5_max_diver:
#             symbol5_min_diver = symbol5_max_diver
#
#         result = f"{datetime.now().strftime('%H:%M:%S')}, " \
#                  f"{symbols[0]}: {symbol1_max_diver}% (min {symbol1_min_diver}%), " \
#                  f"{symbols[1]}: {symbol2_max_diver}% (min {symbol2_min_diver}%), " \
#                  f"{symbols[2]}: {symbol3_max_diver}% (min {symbol3_min_diver}%), " \
#                  f"{symbols[3]}: {symbol4_max_diver}% (min {symbol4_min_diver}%), " \
#                  f"{symbols[4]}: {symbol5_max_diver}% (min {symbol5_min_diver}%)"
#
#         sys.stdout.write('\r{}'.format(result))
#         sys.stdout.flush()
#
#         fee = 0.18
#         spread = 0.14
#         slippage = 0.3
#         profit = 0.2
#         alert = fee + spread + slippage + profit
#
#         if last_message_time is None or (datetime.now() - last_message_time).seconds >= 30:
#
#             if symbol1_max_diver >= alert or \
#                     symbol2_max_diver >= alert or \
#                     symbol3_max_diver >= alert or \
#                     symbol4_max_diver >= alert or \
#                     symbol5_max_diver >= alert:
#                 bot3.send_message(662482931, f"{datetime.now().strftime('%H:%M:%S')}, \n"
#                                              f"{symbols[0]}: {symbol1_max_diver}% (min {symbol1_min_diver}%), \n"
#                                              f"{symbols[1]}: {symbol2_max_diver}% (min {symbol2_min_diver}%), \n"
#                                              f"{symbols[2]}: {symbol3_max_diver}% (min {symbol3_min_diver}%), \n"
#                                              f"{symbols[3]}: {symbol4_max_diver}% (min {symbol4_min_diver}%), \n"
#                                              f"{symbols[4]}: {symbol5_max_diver}% (min {symbol5_min_diver}%)")
#
#                 last_message_time = datetime.now()
#                 last_message_text = [symbol1_max_diver, symbol2_max_diver, symbol3_max_diver, symbol4_max_diver, symbol5_max_diver]
#
#             if last_message_text[0] - symbol1_max_diver >= alert or \
#                     last_message_text[1] - symbol2_max_diver >= alert or \
#                     last_message_text[2] - symbol3_max_diver >= alert or \
#                     last_message_text[3] - symbol4_max_diver >= alert or \
#                     last_message_text[4] - symbol5_max_diver >= alert:
#                 bot3.send_message(662482931, f"{datetime.now().strftime('%H:%M:%S')}, \n"
#                                              f"{symbols[0]}: {symbol1_max_diver}% (min {symbol1_min_diver}%), \n"
#                                              f"{symbols[1]}: {symbol2_max_diver}% (min {symbol2_min_diver}%), \n"
#                                              f"{symbols[2]}: {symbol3_max_diver}% (min {symbol3_min_diver}%), \n"
#                                              f"{symbols[3]}: {symbol4_max_diver}% (min {symbol4_min_diver}%), \n"
#                                              f"{symbols[4]}: {symbol5_max_diver}% (min {symbol5_min_diver}%)")
#
#                 last_message_time = datetime.now()
#                 last_message_text = [symbol1_max_diver, symbol2_max_diver, symbol3_max_diver, symbol4_max_diver, symbol5_max_diver]


def on_error(ws, error):
    # print("WebSocket Error:", error)
    pass


def on_close(ws, close_status_code, close_msg):
    # print(f"WebSocket connection closed with code {close_status_code}")
    pass


def on_open_binance(ws):
    # print("Binance WebSocket Opened")
    pass


if __name__ == "__main__":
    url_binance = f"wss://fstream.binance.com/stream?streams=" \
                  f"{symbols[0].lower()}@depth5@100ms/" \
                  f"{symbols[1].lower()}@depth5@100ms/" \
                  f"{symbols[2].lower()}@depth5@100ms/" \
                  f"{symbols[3].lower()}@depth5@100ms/" \
                  f"{symbols[4].lower()}@depth5@100ms"

    ws_binance = websocket.WebSocketApp(url_binance, on_message=on_message_binance, on_error=on_error, on_close=on_close)
    ws_binance.on_open = on_open_binance

    # Create proc for WebSocket connections and message processing
    binance_thread = threading.Thread(target=ws_binance.run_forever)
    # message_processing_thread = threading.Thread(target=process_messages)

    # Start the proc
    binance_thread.start()
    # message_processing_thread.start()

    # Wait for all proc to finish
    binance_thread.join()
    # message_processing_thread.join()

# time.sleep(10)
#
# binance_thread.
# bybit_thread.close()
# message_processing_thread.close()
