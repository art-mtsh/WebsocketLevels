import os
import asyncio
import json
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


def process_depth(m_type, coin, bids: dict, asks: dict, dropped_levels: set) -> tuple or None:
    wiggle_room = float(os.getenv('WIGGLE_ROOM', 0.02)) / 100

    best_bid: float = list(bids.keys())[-1]
    best_ask: float = list(bids.keys())[0]

    for key, value in tracked_levels.items():
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
                    potential_stop = max_volume_price + (max_volume_price * best_price_dist) / 100
                    potential_take = best_bid - abs(potential_stop - best_bid) - 0.001 * best_bid

                    level_in_ask = level in asks.keys()
                    volume_verified = max_volume_volume >= avg_vol * avg_vol_mpl
                    relative_volume_verified = max_volume_volume >= second_volume_volume * sec_vol_mpl
                    distance_verified = current_distance <= atr * atr_dis_mpl
                    entry_position = round(abs(best_ask - max_volume_price) / (max_volume_price / 100), 2) <= best_price_dist

                    msg = (f'{symbol} ({market_type}) SELL\n'
                           f'Level in asks ({level}) -> {level_in_ask}\n'
                           f'MaxVol/AvgVol: {int(max_volume_volume)}k >= {int(avg_vol)}k * {avg_vol_mpl} -> {volume_verified}\n'
                           f'MaxVol/SecVol: {int(max_volume_volume)}k >= {int(second_volume_volume)}k * {sec_vol_mpl} -> {relative_volume_verified}\n'
                           f'Dist to level: {current_distance}% <= {round(atr, 2)}% * {atr_dis_mpl} -> {distance_verified}\n'
                           f'Dist to max.vol: {round(abs(best_ask - max_volume_price) / (max_volume_price / 100), 2)}% <= {best_price_dist}% -> {entry_position}\n\n'
                           f'Entry: {best_bid}\n'
                           f'Stop: {potential_stop}\n'
                           f'Take: {potential_take}')

                    if level_in_ask and volume_verified and relative_volume_verified and distance_verified and entry_position:
                        if ((symbol, h, level, 'sell')) not in sent_messages:
                            personal_bot.send_message(personal_id, '✅ TRADE\n' + msg)
                            sent_messages.append((symbol, h, level, 'sell'))
                            print('✅ TRADE\n' + msg)
                    elif level_in_ask:
                        if (symbol, h, m, level, 'level_in_ask') not in sent_messages:
                            # personal_bot.send_message(personal_id, 'NOT A TRADE\n' + msg)
                            sent_messages.append((symbol, h, m, level, 'level_in_ask'))
                            print('NOT A TRADE\n' + msg)

                    elif volume_verified and entry_position:
                        if (symbol, h, m, level, 'top_volume_found_dn') not in sent_messages:
                            msg = (f'{symbol} ({market_type})\n'
                                   f'We close to max vol {max_volume_volume} ({max_volume_price} in {round(abs(best_ask - max_volume_price) / (max_volume_price / 100), 2)}%)'
                                   f'Avg volume: {avg_vol} ({int((abs(best_ask - max_volume_price) / (max_volume_price / 100)) / avg_vol)} times smaller than max)')
                            personal_bot.send_message(personal_id, 'NOT A TRADE\n' + msg)
                            sent_messages.append((symbol, h, m, level, 'top_volume_found_dn'))
                    # else:
                    #     print(f'{symbol} level {level} {side} in {current_distance}%')
            if side == 'dn':
                if best_bid < level:
                    return key
                else:
                    max_volume_price, max_volume_volume = sorted(bids.items(), key=lambda x: x[1])[-1]
                    second_volume_price, second_volume_volume = sorted(bids.items(), key=lambda x: x[1])[-2]
                    potential_stop = max_volume_price - (max_volume_price * best_price_dist) / 100
                    potential_take = best_ask + abs(best_ask - potential_stop) + 0.001 * best_ask

                    level_in_bid = level in bids.keys()
                    volume_verified = max_volume_volume >= avg_vol * avg_vol_mpl
                    relative_volume_verified = max_volume_volume >= second_volume_volume * sec_vol_mpl
                    distance_verified = current_distance <= atr * atr_dis_mpl
                    entry_position = round(abs(best_bid - max_volume_price) / (max_volume_price / 100), 2) <= best_price_dist

                    msg = (f'{symbol} ({market_type}) BUY\n'
                           f'Level in bids ({level}) -> {level_in_bid}\n'
                           f'MaxVol/AvgVol: {int(max_volume_volume)}k >= {int(avg_vol)}k * {avg_vol_mpl} -> {volume_verified}\n'
                           f'MaxVol/SecVol: {int(max_volume_volume)}k >= {int(second_volume_volume)}k * {sec_vol_mpl} -> {relative_volume_verified}\n'
                           f'Dist to level: {current_distance}% <= {round(atr, 2)}% * {atr_dis_mpl} -> {distance_verified}\n'
                           f'Dist to max.vol: {round(abs(best_bid - max_volume_price) / (max_volume_price / 100), 2)}% <= {best_price_dist}% -> {entry_position}\n\n'
                           f'Entry: {best_bid}\n'
                           f'Stop: {potential_stop}\n'
                           f'Take: {potential_take}')

                    if level_in_bid and volume_verified and relative_volume_verified and distance_verified and entry_position:
                        if ((symbol, h, level, 'buy')) not in sent_messages:
                            personal_bot.send_message(personal_id, '✅ TRADE\n' + msg)
                            sent_messages.append((symbol, h, level, 'buy'))
                            print('✅ TRADE\n' + msg)
                    elif level_in_bid:
                        if (symbol, h, m, level, 'level_in_bid') not in sent_messages:
                            # personal_bot.send_message(personal_id, 'NOT A TRADE\n' + msg)
                            sent_messages.append((symbol, h, m, level, 'level_in_bid'))
                            print('NOT A TRADE\n' + msg)

                    elif volume_verified and entry_position:
                        if (symbol, h, m, level, 'top_volume_found_up') not in sent_messages:
                            msg = (f'{symbol} ({market_type})\n'
                                   f'We close to max vol {max_volume_volume} ({max_volume_price} in {round(abs(best_bid - max_volume_price) / (max_volume_price / 100), 2)}%)'
                                   f'Avg volume: {avg_vol} ({int((abs(best_bid - max_volume_price) / (max_volume_price / 100)) / avg_vol)} times smaller than max)')
                            personal_bot.send_message(personal_id, 'NOT A TRADE\n' + msg)
                            sent_messages.append((symbol, h, m, level, 'top_volume_found_up'))

                    # else:
                    #     print(f'{symbol} level {level} {side} in {current_distance}%')

            if side not in ['up', 'dn']:
                print('Wrong side! : ', side)




async def connect_and_listen(stream_url):
    try:
        async with websockets.connect(stream_url) as websocket:
            logging.info(f"⚙️ Connected to the WebSocket {stream_url}")
            while not global_stop.is_set():
                if os.getenv(f'levels_check') != datetime.now().strftime('%M%S'):
                    os.environ[f'levels_check'] = datetime.now().strftime('%M%S')
                    print(f'Dropped levels: ({len(dropped_levels)}), Tracked levels: ({len(tracked_levels)})')
                try:
                    message = await websocket.recv()
                    if global_stop.is_set():
                        break
                    response = json.loads(message)
                    levels_symbols = set([s[0] for s in tracked_levels.keys()])
                    coin = response['stream'].split('@')[0].upper()
                    data = response['data']

                    # spot
                    if 'bids' in data.keys() and coin in levels_symbols:
                        m_type = 'spot'
                        bids, asks = data['bids'][::-1], data['asks']
                        bids, asks = {float(v[0]): float(v[1]) for v in bids}, {float(v[0]): float(v[1]) for v in asks}
                        if de := process_depth(m_type, coin, bids, asks, dropped_levels):
                            dropped_levels.add(de)
                            logging.debug(f'Level added to dropped levels: {de}')
                    # futures
                    elif 'b' in data.keys() and coin in levels_symbols:
                        m_type = 'futures'
                        bids, asks = data['b'][::-1], data['a']
                        bids, asks = {float(v[0]): float(v[1]) for v in bids}, {float(v[0]): float(v[1]) for v in asks}
                        if de := process_depth(m_type, coin, bids, asks, dropped_levels):
                            dropped_levels.add(de)
                            logging.debug(f'Level added to dropped levels: {de}')


                except websockets.exceptions.ConnectionClosed:
                    logging.warning("Connection closed. Attempting to reconnect...")
                    break  # Break the inner loop to reconnect

            await asyncio.sleep(5)  # Wait before trying to reconnect

    except (websockets.exceptions.InvalidStatusCode, websockets.exceptions.ConnectionClosedError) as e:
        logging.error(f"Connection error: {e}. Reconnecting...")
        await asyncio.sleep(5)  # Wait before trying to reconnect


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

    for task in tasks:
        task.cancel()
        await task

    logging.info(f"⚙️ Websockets asyncio done its work.")
