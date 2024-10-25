import os
import asyncio
import json
import websockets
import telebot
from datetime import datetime
from dotenv import load_dotenv

from modules.mod_levels_search import tracked_levels, dropped_levels
from modules.global_stopper import global_stop, sent_messages

# import logging
# from main_log_config import setup_logger
# setup_logger()

load_dotenv('keys.env')

bot_token = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_bot = telebot.TeleBot(bot_token)
personal_id = int(os.getenv('PERSONAL_ID'))

levels_lock = asyncio.Lock()


def process_ask(coin, market_type, asks: dict, level, avg_vol, atr) -> tuple or None:
    best_ask: float = list(asks.keys())[0]

    m = datetime.now().strftime('%M')

    avg_vol_mpl = float(os.getenv('AVG_VOL_MPL', 4))
    sec_vol_mpl = float(os.getenv('SEC_VOL_MPL', 2))
    atr_dis_mpl = float(os.getenv('ATR_DIS_MPL', 0.5))
    best_price_dist = float(os.getenv('BEST_PRICE_DIST', 0.1))

    if best_ask > level:
        return True
    else:
        asks_to_level = {price: volume for price, volume in asks.items() if price <= level}
        first_volume_price, first_volume_volume = sorted(asks_to_level.items(), key=lambda x: x[1])[-1]
        distance_to_max = round(abs(best_ask - first_volume_price) / (first_volume_price / 100), 2)

        if len(asks_to_level) > 2:
            second_volume_price, second_volume_volume = sorted(asks_to_level.items(), key=lambda x: x[1])[-2]
            third_volume_price, third_volume_volume = sorted(asks_to_level.items(), key=lambda x: x[1])[-3]
            next_vol_verified = max(first_volume_volume / second_volume_volume, second_volume_volume / third_volume_volume)
        elif len(asks_to_level) > 1:
            second_volume_price, second_volume_volume = sorted(asks_to_level.items(), key=lambda x: x[1])[-2]
            next_vol_verified = first_volume_volume / second_volume_volume
        elif len(asks_to_level) == 1:
            next_vol_verified = sec_vol_mpl
        else:
            personal_bot.send_message(personal_id, 'SOME SHIT')
            next_vol_verified = 0

        max_vol_verified = first_volume_volume >= avg_vol * avg_vol_mpl
        max_vol_close_to_level = level >= first_volume_price >= level - level * ((atr * atr_dis_mpl) / 100)
        price_dist_to_max = distance_to_max <= best_price_dist

        msg = (f'{coin} ({market_type})\n'
               f'first_volume_volume: {first_volume_price}, {round(first_volume_volume / 1000, 2)}k\n'
               f'sec_vol_mpl: x{round(next_vol_verified, 2)}\n'
               f'max_vol_verified: {int(first_volume_volume / 1000)}k ({round(first_volume_volume / avg_vol, 2)} x avg.vol)\n'
               f'max_vol_close_to_level: {level}\n'
               f'max_dist_ver: {distance_to_max}% to max vol\n')

        if next_vol_verified >= sec_vol_mpl and max_vol_verified and max_vol_close_to_level and price_dist_to_max:
            if (coin, m, level) not in sent_messages:
                personal_bot.send_message(personal_id, '✅ TRADE\n' + msg)
                sent_messages.append((coin, m, level))
                print('✅ TRADE\n' + msg)
                return None

    return None


def process_bid(coin, market_type, bids: dict, level, avg_vol, atr) -> tuple or None:
    best_bid: float = list(bids.keys())[-1]

    m = datetime.now().strftime('%M')

    avg_vol_mpl = float(os.getenv('AVG_VOL_MPL', 4))
    sec_vol_mpl = float(os.getenv('SEC_VOL_MPL', 2))
    atr_dis_mpl = float(os.getenv('ATR_DIS_MPL', 0.5))
    best_price_dist = float(os.getenv('BEST_PRICE_DIST', 0.1))

    if best_bid < level:
        return True
    else:
        bids_to_level = {price: volume for price, volume in bids.items() if price >= level}
        first_volume_price, first_volume_volume = sorted(bids_to_level.items(), key=lambda x: x[1])[-1]
        distance_to_max = round(abs(best_bid - first_volume_price) / (first_volume_price / 100), 2)

        if len(bids_to_level) > 2:
            second_volume_price, second_volume_volume = sorted(bids_to_level.items(), key=lambda x: x[1])[-2]
            third_volume_price, third_volume_volume = sorted(bids_to_level.items(), key=lambda x: x[1])[-3]
            next_vol_verified = max(first_volume_volume / second_volume_volume, second_volume_volume / third_volume_volume)
        elif len(bids_to_level) > 1:
            second_volume_price, second_volume_volume = sorted(bids_to_level.items(), key=lambda x: x[1])[-2]
            next_vol_verified = first_volume_volume / second_volume_volume
        elif len(bids_to_level) == 1:
            next_vol_verified = sec_vol_mpl
        else:
            personal_bot.send_message(personal_id, 'SOME SHIT')
            next_vol_verified = 0

        max_vol_verified = first_volume_volume >= avg_vol * avg_vol_mpl
        max_vol_close_to_level = level <= first_volume_price <= level + level * ((atr * atr_dis_mpl) / 100)
        price_dist_to_max = distance_to_max <= best_price_dist

        msg = (f'{coin} ({market_type})\n'
               f'first_volume_volume: {first_volume_price}, {round(first_volume_volume / 1000, 2)}k\n'
               f'sec_vol_mpl: x{round(next_vol_verified, 2)}\n'
               f'max_vol_verified: {int(first_volume_volume / 1000)}k ({round(first_volume_volume / avg_vol, 2)} x avg.vol)\n'
               f'max_vol_close_to_level: {level}\n'
               f'max_dist_ver: {distance_to_max}% to max vol\n')

        if next_vol_verified >= sec_vol_mpl and max_vol_verified and max_vol_close_to_level and price_dist_to_max:
            if (coin, m, level) not in sent_messages:
                personal_bot.send_message(personal_id, '✅ TRADE\n' + msg)
                sent_messages.append((coin, m, level))
                print('✅ TRADE\n' + msg)
                return None

    return None


async def connect_and_listen(stream_url):
    while not global_stop.is_set():
        # trying to connect to websocket
        try:
            async with websockets.connect(stream_url) as websocket:
                personal_bot.send_message(personal_id, "Connected to the WebSocket...")

                while not global_stop.is_set():

                    async with levels_lock:
                        init_tracked_levels = tracked_levels.copy()
                        init_dropped_levels = dropped_levels.copy()

                    t = datetime.now().strftime('%H:%M')
                    if os.getenv(f'levels_check') != t:
                        os.environ[f'levels_check'] = t
                        print(f'{t} Dropped: {len(init_dropped_levels)}, Tracked by WS: {len(init_tracked_levels)}')

                    try:
                        message = await websocket.recv()
                        if global_stop.is_set():
                            break
                        response = json.loads(message)

                        coin = response['stream'].split('@')[0].upper()
                        data = response['data']

                        if any(key[0] == coin for key in init_tracked_levels):
                            if 'bids' in data.keys():
                                m_type = 'spot'
                                bids, asks = data['bids'][::-1], data['asks']
                                bids, asks = {float(v[0]): float(v[1]) for v in bids}, {float(v[0]): float(v[1]) for v in asks}
                            elif 'b' in data.keys():
                                m_type = 'futures'
                                bids, asks = data['b'][::-1], data['a']
                                bids, asks = {float(v[0]): float(v[1]) for v in bids}, {float(v[0]): float(v[1]) for v in asks}
                            else:
                                personal_bot.send_message(personal_id, f"Broken data returned for {coin}.")

                            for key, value in init_tracked_levels.items():
                                symbol, timeframe, market_type, origin_level, futures_according_level, side, avg_vol, atr = key[0], key[1], key[2], key[3], key[4], key[5], value[0], value[1]

                                if market_type == m_type and coin == symbol and key not in init_dropped_levels:

                                    if side == 'up':
                                        if process_ask(coin, market_type, asks, origin_level, avg_vol, atr):
                                            dropped_levels.add(key)
                                            print(f'{coin} ({m_type}), level added to dropped. Ask {list(asks.keys())[0]} > {origin_level} (level)')

                                    elif side == 'dn':
                                        if process_bid(coin, market_type, bids, origin_level, avg_vol, atr):
                                            dropped_levels.add(key)
                                            print(f'{coin} ({m_type}), level added to dropped. Bid {list(bids.keys())[-1]} < {origin_level} (level)')

                    except websockets.exceptions.ConnectionClosed:
                        personal_bot.send_message(personal_id, "Connection closed.")
                        await asyncio.sleep(10)
                        break  # Break the inner loop to reconnect

        except (websockets.exceptions.InvalidStatusCode, websockets.exceptions.ConnectionClosedError) as e:
            personal_bot.send_message(personal_id, f"Connection error: {e}. Script is stopped")
            await asyncio.sleep(10)  # Wait before retrying


async def listen_market_depth(symbols_with_levels):
    print(f"Starting websockets asyncio.")

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

    print(f"Websockets asyncio done its work.")
