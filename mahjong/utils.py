from typing import List, Iterable
from copy import deepcopy, copy
from collections import Counter

YAKU_LIST = '門前清自摸和;立直;一發;槍槓;嶺上開花;海底摸月;河底撈魚;平和;斷么九;一盃口;自風 東;自風 南;自風 西;自風 北;場風 東;場風 南;場風 西;場風 北;役牌 白;役牌 發;役牌 中;兩立直;七對子;混全帶么九;一氣通貫;三色同順;三色同刻;三槓子;對對和;三暗刻;小三元;混老頭;二盃口;純全帶么九;混一色;清一色;人和;天和;地和;大三元;四暗刻;四暗刻單騎;字一色;綠一色;清老頭;九蓮寶燈;純正九蓮寶燈;國士無雙;國士無雙13面;大四喜;小四喜;四槓子;ドラ;裏ドラ;赤ドラ'.split(';')


class AutoCleanCounter(Counter):
    def __setitem__(self, key, value):
        if value == 0:
            del self[key]
        else:
            super(AutoCleanCounter, self).__setitem__(key, value)


def encode_shunzi(tile_id_list, kui_tile):
    kui_index = tile_id_list.index(kui_tile)
    pattern = tile_id_list[0] // 4 * 3 + kui_index
    code = 3
    code |= 0x004
    for i, tile_id in enumerate(tile_id_list):
        code |= (tile_id % 4) << (3 + i * 2)
    code |= pattern << 10
    return code


def encode_kezi(tile_id_list, kui_tile, where):
    kui_index = tile_id_list.index(kui_tile)
    code = where % 4
    code |= 0x0008
    pattern = tile_id_list[0] // 4
    unused = pattern * 3 + 6 - sum(tile_id_list)
    pattern = pattern * 3 + kui_index
    code |= unused << 5
    code |= pattern << 9
    return code


def encode_kanzi(tile_id_list, kui_tile, where, add=None, pon_code=None):
    if add is not None:
        pon_code |= 1 << 4
        return pon_code
    code = where % 4
    kui_index = tile_id_list.index(kui_tile) if code != 0 else 0
    pattern = kui_tile // 4 * 4 + kui_index
    code |= pattern << 8
    return code


def parse_meld(m):
    kui = m & 3
    if m & (1 << 2):  # 顺子
        t = (m & 0xfc00) >> 10
        r = t % 3  # 哪张牌是新拿来的
        t //= 3
        t = t // 7 * 9 + t % 7
        t *= 4
        h = [t + 4 * 0 + ((m & 0x0018) >> 3), t + 4 * 1 + ((m & 0x0060) >> 5), t + 4 * 2 + ((m & 0x0180) >> 7)]
        return 0, h, h[r], kui

    if m & (1 << 3):  # 刻子
        unused = (m & 0x0060) >> 5
        t = (m & 0xfe00) >> 9
        r = t % 3
        t //= 3
        t *= 4
        h = [t, t, t]
        if unused == 0:
            h[0] += 1
            h[1] += 2
            h[2] += 3
        elif unused == 1:
            h[0] += 0
            h[1] += 2
            h[2] += 3
        elif unused == 2:
            h[0] += 0
            h[1] += 1
            h[2] += 3
        elif unused == 3:
            h[0] += 0
            h[1] += 1
            h[2] += 2
        return 1, h, h[r], kui

    if m & (1 << 4):  # 加杠
        added = (m & 0x0060) >> 5
        t = (m & 0xfe00) >> 9
        r = t % 3
        t //= 3
        t *= 4
        n = t + added
        h = [t, t, t]
        if added == 0:
            h[0] += 1
            h[1] += 2
            h[2] += 3
        elif added == 1:
            h[0] += 0
            h[1] += 2
            h[2] += 3
        elif added == 2:
            h[0] += 0
            h[1] += 1
            h[2] += 3
        else:
            h[0] += 0
            h[1] += 1
            h[2] += 2
        if r == 1:
            h.insert(0, h.pop(1))
        elif r == 2:
            h.insert(0, h.pop(2))
        return 2, h, n, kui

    elif not (m & (1 << 5)):  # 暗杠、大明杠
        hai0 = (m & 0xff00) >> 8
        r = hai0 % 4
        if not kui:
            hai0 = (hai0 & -3) + 3
        t = hai0 // 4 * 4
        h = [t, t + 1, t + 2, t + 3]
        if kui:
            return 3, h, h[r], kui
        else:
            return 4, h, h[r], kui


def get_dora(d):
    """d为dora指示牌id"""
    d = d // 4
    if d % 9 == 8:
        d = d - 8
    elif d == 30:
        d = 27
    elif d == 33:
        d = 31
    else:
        d += 1
    return d
