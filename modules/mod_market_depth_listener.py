import os
import asyncio
import json
import websockets
import telebot
from datetime import datetime
from dotenv import load_dotenv
from modules.mod_levels_search import tracked_levels, dropped_levels
from modules.global_stopper import global_stop, sent_messages
from modules.telegram_handler import send_msg

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
        top_level_border = level + level * ((atr * atr_dis_mpl) / 100)
        bot_level_border = level - level * ((atr * atr_dis_mpl) / 100)
        asks_to_level = {price: volume for price, volume in asks.items() if bot_level_border <= price <= top_level_border}

        if len(asks_to_level) > 2:
            first_volume_price, first_volume_volume = sorted(asks_to_level.items(), key=lambda x: x[1])[-1]
            second_volume_price, second_volume_volume = sorted(asks_to_level.items(), key=lambda x: x[1])[-2]
            third_volume_price, third_volume_volume = sorted(asks_to_level.items(), key=lambda x: x[1])[-3]

            distance_to_max = round(abs(best_ask - first_volume_price) / (first_volume_price / 100), 2)
            next_vol = max(first_volume_volume / second_volume_volume, second_volume_volume / third_volume_volume)

            max_vol_verified = first_volume_volume >= avg_vol * avg_vol_mpl
            price_dist_to_max = distance_to_max <= best_price_dist
            next_vol_verified = next_vol >= sec_vol_mpl

            msg = (f'✅ {coin} ({market_type})\n'
                   f'current price: {best_ask}\n'
                   f'level: {level}\n'
                   f'max.vol: {first_volume_price}, {round(first_volume_volume / 1000, 2)}k\n'
                   f'({round(next_vol, 2)} x sec.vol, {round(first_volume_volume / avg_vol, 2)} x avg.vol)')

            if next_vol_verified and max_vol_verified and price_dist_to_max:
                if (coin, m, level) not in sent_messages:
                    send_msg(msg)
                    sent_messages.append((coin, m, level))
                    print(msg)
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
        top_level_border = level + level * ((atr * atr_dis_mpl) / 100)
        bot_level_border = level - level * ((atr * atr_dis_mpl) / 100)
        bids_to_level = {price: volume for price, volume in bids.items() if bot_level_border <= price <= top_level_border}

        if len(bids_to_level) > 2:
            first_volume_price, first_volume_volume = sorted(bids_to_level.items(), key=lambda x: x[1])[-1]
            second_volume_price, second_volume_volume = sorted(bids_to_level.items(), key=lambda x: x[1])[-2]
            third_volume_price, third_volume_volume = sorted(bids_to_level.items(), key=lambda x: x[1])[-3]

            distance_to_max = round(abs(best_bid - first_volume_price) / (first_volume_price / 100), 2)
            next_vol = max(first_volume_volume / second_volume_volume, second_volume_volume / third_volume_volume)

            max_vol_verified = first_volume_volume >= avg_vol * avg_vol_mpl
            price_dist_to_max = distance_to_max <= best_price_dist
            next_vol_verified = next_vol >= sec_vol_mpl

            msg = (f'✅ {coin} ({market_type})\n'
                   f'current price: {best_bid}\n'
                   f'level: {level}\n'
                   f'max.vol: {first_volume_price}, {round(first_volume_volume / 1000, 2)}k\n'
                   f'({round(next_vol, 2)} x sec.vol, {round(first_volume_volume / avg_vol, 2)} x avg.vol)')

            if next_vol_verified and max_vol_verified and price_dist_to_max:
                if (coin, m, level) not in sent_messages:
                    send_msg(msg)
                    sent_messages.append((coin, m, level))
                    print(msg)
                    return None

    return None


async def connect_and_listen(stream_url):
    while not global_stop.is_set():
        # trying to connect to websocket
        try:
            async with websockets.connect(stream_url) as websocket:

                while not global_stop.is_set():

                    async with levels_lock:
                        init_tracked_levels = tracked_levels.copy()
                        init_dropped_levels = dropped_levels.copy()

                    t = datetime.now().strftime('%H:%M')
                    if os.getenv(f'levels_check') != t:
                        os.environ[f'levels_check'] = t
                        print(f'{datetime.now().strftime("%H:%M:%S")} Dropped: {len(init_dropped_levels)}, Tracked by WS: {len(init_tracked_levels)}')
                        os.environ['msg_tracked_levels'] = f"{datetime.now().strftime('%d.%m.%y %H:%M')}\nTracked levels: {len(tracked_levels)}"

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
                                send_msg(f"Broken data returned for {coin}.")

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
                        send_msg("Connection closed.")
                        await asyncio.sleep(10)
                        break  # Break the inner loop to reconnect

        except (websockets.exceptions.InvalidStatusCode, websockets.exceptions.ConnectionClosedError) as e:
            send_msg(f"Connection error: {e}. Script is stopped")
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
