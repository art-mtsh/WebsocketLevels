import os
import asyncio
import json
from time import sleep

import websockets
import logging
import telebot
from datetime import datetime
from dotenv import load_dotenv
from main_log_config import setup_logger
from modules.mod_levels_search import tracked_levels, dropped_levels
from modules.global_stopper import global_stop, sent_messages

setup_logger()
load_dotenv('keys.env')

bot_token = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_bot = telebot.TeleBot(bot_token)
personal_id = int(os.getenv('PERSONAL_ID'))

def process_depth(m_type, coin, bids: dict, asks: dict, dropped_levels: set, tracked) -> tuple or None:
    best_bid: float = list(bids.keys())[-1]
    best_ask: float = list(bids.keys())[0]

    for key, value in tracked.items():
        symbol, timeframe, market_type, origin_level, futures_according_level, side, avg_vol, atr = key[0], key[1], key[2], key[3], key[4], key[5], value[0], value[1]
        level = origin_level if market_type == 'spot' else futures_according_level
        current_distance = abs(level - (best_ask + best_bid) / 2) / (level / 100)
        current_distance = round(current_distance, 2)
        h, m = datetime.now().strftime('%H'), datetime.now().strftime('%M')

        if symbol == coin and market_type == m_type and key not in dropped_levels:
            avg_vol_mpl = float(os.getenv('AVG_VOL_MPL'))
            sec_vol_mpl = float(os.getenv('SEC_VOL_MPL'))
            atr_dis_mpl = float(os.getenv('ATR_DIS_MPL'))
            best_price_dist = float(os.getenv('BEST_PRICE_DIST'))

            if side == 'up':
                if best_ask > level:
                    return key
                else:
                    max_volume_price, max_volume_volume = sorted(asks.items(), key=lambda x: x[1])[-1]
                    second_volume_price, second_volume_volume = sorted(asks.items(), key=lambda x: x[1])[-2]
                    distance_to_max = round(abs(best_ask - max_volume_price) / (max_volume_price / 100), 2)

                    max_vol_verified = max_volume_volume >= avg_vol * avg_vol_mpl
                    sec_vol_verified = max_volume_volume >= second_volume_volume * sec_vol_mpl
                    max_vol_close_to_level = level >= max_volume_price >= level - level * ((atr * atr_dis_mpl) / 100)
                    price_dist_to_max = distance_to_max <= best_price_dist

                    msg = (f'{symbol} ({market_type})\n'
                           f'{"☑️" if max_vol_verified else "◻️"} max_vol_verified: {int(max_volume_volume / 1000)}k ({round(max_volume_volume / avg_vol, 2)} x avg.vol)\n'
                           f'{"☑️" if max_vol_close_to_level else "◻️"} max_vol_close_to_level: {level}\n'
                           f'{"☑️" if price_dist_to_max else "◻️"} max_dist_ver: {distance_to_max}% to max vol\n')

                    if max_vol_verified and max_vol_close_to_level and price_dist_to_max and sec_vol_verified:
                        if (symbol, h, level, 111) not in sent_messages:
                            personal_bot.send_message(personal_id, '✅ TRADE\n' + msg)
                            sent_messages.append((symbol, h, level, 111))
                            print('✅ TRADE\n' + msg)

            if side == 'dn':
                if best_bid < level:
                    return key
                else:
                    max_volume_price, max_volume_volume = sorted(bids.items(), key=lambda x: x[1])[-1]
                    second_volume_price, second_volume_volume = sorted(bids.items(), key=lambda x: x[1])[-2]
                    distance_to_max = round(abs(best_bid - max_volume_price) / (max_volume_price / 100), 2)

                    max_vol_verified = max_volume_volume >= avg_vol * avg_vol_mpl
                    sec_vol_verified = max_volume_volume >= second_volume_volume * sec_vol_mpl
                    max_vol_close_to_level = level <= max_volume_price <= level + level * ((atr * atr_dis_mpl) / 100)
                    price_dist_to_max = distance_to_max <= best_price_dist

                    msg = (f'{symbol} ({market_type})\n'
                           f'{"☑️" if max_vol_verified else "◻️"} max_vol_verified: {int(max_volume_volume / 1000)}k ({round(max_volume_volume / avg_vol, 2)} x avg.vol)\n'
                           f'{"☑️" if max_vol_close_to_level else "◻️"} max_vol_close_to_level: {level}\n'
                           f'{"☑️" if price_dist_to_max else "◻️"} max_dist_ver: {distance_to_max}% to max vol\n')

                    if max_vol_verified and max_vol_close_to_level and price_dist_to_max and sec_vol_verified:
                        if (symbol, h, level, 444) not in sent_messages:
                            personal_bot.send_message(personal_id, '✅ TRADE\n' + msg)
                            sent_messages.append((symbol, h, level, 444))
                            print('✅ TRADE\n' + msg)

            if side not in ['up', 'dn']:
                print('Wrong side! : ', side)


async def connect_and_listen(stream_url):
    # trying to connect to websocket
    try:
        async with websockets.connect(stream_url) as websocket:
            logging.info(f"⚙️ Connected to the WebSocket {stream_url}")

            while not global_stop.is_set():
                tr_levels = tracked_levels.copy()

                if os.getenv(f'levels_check') != datetime.now().strftime('%M%S'):
                    os.environ[f'levels_check'] = datetime.now().strftime('%M%S')
                    print(f'Dropped levels: ({len(dropped_levels)}), Tracked levels: ({len(tr_levels)})')

                # trying to get new data
                try:
                    message = await websocket.recv()
                    if global_stop.is_set():
                        break
                    response = json.loads(message)
                    levels_symbols = set([s[0] for s in tr_levels.keys()])
                    coin = response['stream'].split('@')[0].upper()
                    data = response['data']

                    # spot
                    if 'bids' in data.keys() and coin in levels_symbols:
                        m_type = 'spot'
                        bids, asks = data['bids'][::-1], data['asks']
                        bids, asks = {float(v[0]): float(v[1]) for v in bids}, {float(v[0]): float(v[1]) for v in asks}
                        if de := process_depth(m_type, coin, bids, asks, dropped_levels, tr_levels):
                            dropped_levels.add(de)
                            logging.debug(f'Level added to dropped levels: {de}')
                    # futures
                    elif 'b' in data.keys() and coin in levels_symbols:
                        m_type = 'futures'
                        bids, asks = data['b'][::-1], data['a']
                        bids, asks = {float(v[0]): float(v[1]) for v in bids}, {float(v[0]): float(v[1]) for v in asks}
                        if de := process_depth(m_type, coin, bids, asks, dropped_levels, tr_levels):
                            dropped_levels.add(de)
                            logging.debug(f'Level added to dropped levels: {de}')

                except websockets.exceptions.ConnectionClosed:
                    personal_bot.send_message(personal_id, "Connection closed.")
                    await asyncio.sleep(10)
                    break  # Break the inner loop to reconnect

    except (websockets.exceptions.InvalidStatusCode, websockets.exceptions.ConnectionClosedError) as e:
        personal_bot.send_message(personal_id, f"Connection error: {e}. Script is stopped")
        exit()


async def listen_market_depth(symbols_with_levels):
    logging.info(f"⚙️ Starting websockets asyncio.")

    spot_channels = []
    futures_channels = []

    for symbol, ts_percent_futures, ts_percent_spot, x_atr_per in symbols_with_levels:
        if float(ts_percent_futures) != 0:
            futures_channels.append(f'{symbol.lower()}@depth20')
        if float(ts_percent_spot) != 0:
            spot_channels.append(f"{symbol.lower()}@depth20")

    spot_url = f'wss://stream.binance.com:9443/stream?streams=' + '/'.join(spot_channels) if spot_channels else None
    futures_url = f'wss://fstream.binance.com/stream?streams=' + '/'.join(futures_channels) if futures_channels else None

    tasks = []
    if spot_url:
        tasks.append(asyncio.create_task(connect_and_listen(spot_url)))
    if futures_url:
        tasks.append(asyncio.create_task(connect_and_listen(futures_url)))

    for task in tasks:
        await task

    logging.info(f"⚙️ Websockets asyncio done its work.")
