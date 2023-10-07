import copy
import pickle
from typing import List
import os
from collections import Counter
from itertools import combinations
from .make_agari_table_2 import AGARI_TABLE, calc_key, to_pattern

with open(os.path.join(os.path.dirname(__file__), AGARI_TABLE), 'rb') as f:
    agari_table = pickle.loads(f.read())

MACHI_TABLE = 'MACHI_TABLE.pkl'
with open(os.path.join(os.path.dirname(__file__), MACHI_TABLE), 'rb') as f:
    machi_table = pickle.loads(f.read())


def parse_agari_info(value):
    num_kotsu = value & 0b111
    num_shuntsu = (value & (0b111 << 3)) >> 3
    atama = (value & (0b1111 << 6)) >> 6
    m1 = (value & (0b1111 << 10)) >> 10
    m2 = (value & (0b1111 << 14)) >> 14
    m3 = (value & (0b1111 << 18)) >> 18
    m4 = (value & (0b1111 << 22)) >> 22
    chitoi = (value & (1 << 26)) >> 26
    cyuren = (value & (1 << 27)) >> 27
    ikki = (value & (1 << 28)) >> 28
    ryanpeikou = (value & (1 << 29)) >> 29
    ippeikou = (value & (1 << 30)) >> 30
    return locals()


def is_agari(counter):
    """
    一般形、七对子返回一个或多个16进制数，国士无双返回True，没和返回None
    """
    pattern = to_pattern(counter)
    key = calc_key(pattern)
    if key in agari_table[0]:
        return agari_table[0][key]
    if key in agari_table[1]:
        if sum(counter[i] for i in [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33]) == 14:
            return True
    return None


def check_machi(counter):
    ptn = to_pattern(counter)
    key = calc_key(ptn)
    if key in machi_table[0]:
        return True
    if key in machi_table[1]:
        if sum(counter[i] for i in [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33]) == 13:  # 国士无双听牌
            return True
    return False


def check_riichi(counter, return_riichi_hai=False):
    counter = copy.copy(counter)
    hai = []
    for t, c in list(counter.items()):
        if c > 0:
            counter[t] -= 1
            if check_machi(counter):
                if not return_riichi_hai:
                    return True
                hai.append(t)
            counter[t] += 1
    if hai:
        return hai
    if return_riichi_hai:
        return []
    return False


def machi(counter):
    counter = copy.copy(counter)
    res = set()
    for i in range(34):
        if counter[i] == 4:
            continue
        counter[i] += 1
        if is_agari(counter) is not None:
            res.add(i)
        counter[i] -= 1
    return res
