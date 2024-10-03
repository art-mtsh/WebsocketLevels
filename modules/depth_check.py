import os
from .screenshoterV3 import screenshoter_send


def depth_check(symbol, the_level, i, depth, c_time, avg_vol, c_close, avg_atr_per, market_type, market_type_verbose, levels_f, levels_s, static_f, static_s):
    d_room = int(os.getenv('DEPTH_ROOM_UPDN'))  # вікно зверху і знизу стакану
    atr_dis = float(os.getenv('ATR_DIST'))  # мультиплікатор відстані до сайзу в ATR
    size_mpl = float(os.getenv('SIZE_MPL'))  # мультиплікатор максимального сайзу
    vol_mpl = float(os.getenv('VOL_MPL'))  # мультиплікатор відносності об'єму

    depth_prices = [v[0] for v in depth]
    depth_volumes = [v[1] for v in depth]

    if the_level in depth_prices[d_room:-d_room]:
        level_index = depth_prices.index(the_level)
        level_size = depth_volumes[level_index]

        # сайзи між ціною щільності -10 та ціною щільності
        lower_sizes = [depth[k][1] for k in range(level_index - d_room, level_index)]
        # сайзи між ціною щільності +10 та ціною щільності
        higher_sizes = [depth[k][1] for k in range(level_index + 1, level_index + d_room + 1)]
        # дистанція до ціни
        distance_per = abs(the_level - c_close[-1]) / (c_close[-1] / 100)
        distance_per = float('{:.2f}'.format(distance_per))

        top_volume_validated = all([level_size >= dom * size_mpl for dom in lower_sizes + higher_sizes])
        distance_validated = distance_per <= atr_dis * avg_atr_per
        avg_volume_validated = level_size >= avg_vol * vol_mpl

        if top_volume_validated and distance_validated and avg_volume_validated:

            levels_dict = levels_f if market_type == "f" else levels_s
            static_dict = static_f if market_type == "f" else static_s
            direction = '🔼' if the_level >= c_close[-1] else '🔽'

            if the_level not in levels_dict.keys():
                # levels_dict.update({c_high[-i]: c_time[-i]})
                return {the_level: c_time[-i]}
            else:
                if levels_dict.get(the_level) == c_time[-i]:
                    message_for_screen = f"""
🐘 Size on extremum!
{market_type_verbose} #{symbol}

current price: {c_close[-1]}
average vol: {round(avg_vol / 1000, 1)}K coins

size price: {the_level} {direction} {round(distance_per, 2)}% from current price
size vol: {round(level_size / 1000, 1)}K coins

<b>size/avg.vol: {round(level_size / avg_vol, 1)}</b>

<i>Повідомлення не є торговою рекомендацією.</i>
@UA_sizes_bot
"""
                    screenshoter_send(symbol, market_type, the_level, message_for_screen)
                    if the_level not in static_dict:
                        # static_dict.append(c_high[-i])
                        return the_level


def size_only(symbol, start, end, depth, c_close, market_type, static_f, static_s, size_mpl, atr_dis, avg_atr_per, avg_vol, vol_mpl, levels_f_volumes, levels_s_volumes, market_type_verbose):
    for i in range(start, end):
        current_vol = depth[i][1]
        current_price = depth[i][0]
        previous_b_values = [depth[j][1] for j in range(i - 20, i)]  # values 20 before
        following_b_values = [depth[j][1] for j in range(i + 1, i + 21)]  # values 20 after

        distance_to = abs(current_price - c_close[-1]) / (c_close[-1] / 100)
        static_dict = static_f if market_type == "f" else static_s

        if all(current_vol >= b * size_mpl for b in previous_b_values + following_b_values) and distance_to <= atr_dis * avg_atr_per and current_vol >= avg_vol * vol_mpl and current_price not in static_dict:

            levels_volumes = levels_f_volumes if market_type == 'f' else levels_s_volumes

            if current_price not in levels_volumes.keys():
                return False, {current_price: current_vol}
            else:
                direction = '🔼' if current_price >= c_close[-1] else '🔽'
                personal_message = f"""
🐋 Size only!
{market_type_verbose} #{symbol}

current price: {c_close[-1]}
average vol: {round(avg_vol / 1000, 1)}K coins

size price: {current_price} {direction} {round(distance_to, 2)}% from current price
size vol: {round(current_vol / 1000, 1)}K coins

<b>size/avg.vol: {round(current_vol / avg_vol, 1)}</b>

<i>Повідомлення не є торговою рекомендацією.</i>
@UA_sizes_bot
"""
                screenshoter_send(symbol, market_type, current_price, personal_message)
                # print(personal_message)
                return True, current_price
