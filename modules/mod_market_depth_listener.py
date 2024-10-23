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

tracked_levels_lock = asyncio.Lock()


def process_depth(coin, market_type, bids: dict, asks: dict, level, side, avg_vol, atr) -> tuple or None:
    best_bid: float = list(bids.keys())[-1]
    best_ask: float = list(bids.keys())[0]

    h, m = datetime.now().strftime('%H'), datetime.now().strftime('%M')

    avg_vol_mpl = float(os.getenv('AVG_VOL_MPL'))
    sec_vol_mpl = float(os.getenv('SEC_VOL_MPL'))
    atr_dis_mpl = float(os.getenv('ATR_DIS_MPL'))
    best_price_dist = float(os.getenv('BEST_PRICE_DIST'))

    if side == 'up':
        if best_ask > level:
            return True
        else:
            max_volume_price, max_volume_volume = sorted(asks.items(), key=lambda x: x[1])[-1]
            second_volume_price, second_volume_volume = sorted(asks.items(), key=lambda x: x[1])[-2]
            distance_to_max = round(abs(best_ask - max_volume_price) / (max_volume_price / 100), 2)

            max_vol_verified = max_volume_volume >= avg_vol * avg_vol_mpl
            sec_vol_verified = max_volume_volume >= second_volume_volume * sec_vol_mpl
            max_vol_close_to_level = level >= max_volume_price >= level - level * ((atr * atr_dis_mpl) / 100)
            price_dist_to_max = distance_to_max <= best_price_dist

            msg = (f'{coin} ({market_type})\n'
                   f'{"☑️" if max_vol_verified else "◻️"} max_vol_verified: {int(max_volume_volume / 1000)}k ({round(max_volume_volume / avg_vol, 2)} x avg.vol)\n'
                   f'{"☑️" if max_vol_close_to_level else "◻️"} max_vol_close_to_level: {level}\n'
                   f'{"☑️" if price_dist_to_max else "◻️"} max_dist_ver: {distance_to_max}% to max vol\n')

            if max_vol_verified and max_vol_close_to_level and price_dist_to_max and sec_vol_verified:
                if (coin, h, level, 111) not in sent_messages:
                    personal_bot.send_message(personal_id, '✅ TRADE\n' + msg)
                    sent_messages.append((coin, h, level, 111))
                    print('✅ TRADE\n' + msg)

    if side == 'dn':
        if best_bid < level:
            return True
        else:
            max_volume_price, max_volume_volume = sorted(bids.items(), key=lambda x: x[1])[-1]
            second_volume_price, second_volume_volume = sorted(bids.items(), key=lambda x: x[1])[-2]
            distance_to_max = round(abs(best_bid - max_volume_price) / (max_volume_price / 100), 2)

            max_vol_verified = max_volume_volume >= avg_vol * avg_vol_mpl
            sec_vol_verified = max_volume_volume >= second_volume_volume * sec_vol_mpl
            max_vol_close_to_level = level <= max_volume_price <= level + level * ((atr * atr_dis_mpl) / 100)
            price_dist_to_max = distance_to_max <= best_price_dist

            msg = (f'{coin} ({market_type})\n'
                   f'{"☑️" if max_vol_verified else "◻️"} max_vol_verified: {int(max_volume_volume / 1000)}k ({round(max_volume_volume / avg_vol, 2)} x avg.vol)\n'
                   f'{"☑️" if max_vol_close_to_level else "◻️"} max_vol_close_to_level: {level}\n'
                   f'{"☑️" if price_dist_to_max else "◻️"} max_dist_ver: {distance_to_max}% to max vol\n')

            if max_vol_verified and max_vol_close_to_level and price_dist_to_max and sec_vol_verified:
                if (coin, h, level, 444) not in sent_messages:
                    personal_bot.send_message(personal_id, '✅ TRADE\n' + msg)
                    sent_messages.append((coin, h, level, 444))
                    print('✅ TRADE\n' + msg)

    if side not in ['up', 'dn']:
        print('Wrong side! : ', side)


async def connect_and_listen(stream_url):
    while not global_stop.is_set():
        # trying to connect to websocket
        try:
            async with websockets.connect(stream_url) as websocket:
                personal_bot.send_message(personal_id, "Connected to the WebSocket...")

                while not global_stop.is_set():

                    async with tracked_levels_lock:
                        init_tracked_levels = tracked_levels.copy()
                        tr_levels = {}
                        if init_tracked_levels:
                            for key in init_tracked_levels.keys():
                                if key not in dropped_levels:
                                    tr_levels[key] = init_tracked_levels[key]

                    t = datetime.now().strftime('%H:%M')
                    if os.getenv(f'levels_check') != t:
                        os.environ[f'levels_check'] = t
                        print(f'{t} Initially tracked levels: {len(init_tracked_levels)}, Dropped: {len(dropped_levels)}, Tracked by WS: {len(tr_levels)}')

                    try:
                        message = await websocket.recv()
                        if global_stop.is_set():
                            break
                        response = json.loads(message)

                        coin = response['stream'].split('@')[0].upper()
                        data = response['data']

                        if any(key[0] == coin for key in tr_levels):
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

                            for key, value in tr_levels.items():
                                symbol, timeframe, market_type, origin_level, futures_according_level, side, avg_vol, atr = key[0], key[1], key[2], key[3], key[4], key[5], value[0], value[1]

                                if market_type == m_type and coin == symbol and key not in dropped_levels:

                                    if process_depth(coin, market_type, bids, asks, origin_level, side, avg_vol, atr):
                                        dropped_levels.add(key)
                                        print(f'Level added to dropped levels: {key}')

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

    print(f"⚙️ Websockets asyncio done its work.")
