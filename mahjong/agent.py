from typing import List, Set, Tuple, Dict, Union
import random
import os
import torch
import logging
from collections import OrderedDict
from itertools import product, combinations
from .utils import *
from .check_agari import check_riichi, check_machi, machi, is_agari
from .display import *

from model.models import DiscardModel, RiichiModel, FuroModel


class Agent(object):
    def __init__(self, score: int, tiles: Set, seat: int, is_playback=False):
        """
        score: 分数除以100
        tiles: 配牌集合, 采用天凤编号0-135
        seat: 自风向、0-3
        is_playback: 是否为回放模式
        """
        self.score = score
        self.tiles = tiles
        self.hand_tile_counter = AutoCleanCounter(map(lambda x: x // 4, tiles))
        self.hand_tile_counter_bak = copy(self.hand_tile_counter)
        self.discard_tiles = []
        self.river = []  # 没有被鸣走的牌河
        self.furo: OrderedDict[Tuple[int, Union[int, Tuple[int, int]]], List] = OrderedDict()  # 键: (int 0:吃 1:碰 2:暗杠 3:明杠, pattern or (pattern, nth)), 值: 具体的牌集合
        self.kui_info: [Tuple] = []
        self.declare_riichi = 0  # 是否宣言了立直
        self.riichi_status = 0  # 是否在立直状态
        self.riichi_round = 100  # 立直巡目(未立直时为100)
        self.riichi_tile = -1  # 第一张没被鸣走的立直宣言牌
        self.ippatsu_status = 0  # 是否有一发
        self.kui = False
        self.machi = set()
        self.menfon = [27, 28, 29, 30][seat]

        self.nagashimangan = 1  # 流局满贯标识

        self.discard_furiten = False  # 舍牌振听
        self.riichi_furiten = False  # 立直振听
        self.round_furiten = False  # 同巡振听

        self.is_playback = is_playback
        if is_playback:
            return
        if machi(self.hand_tile_counter):
            self.machi = machi(self.hand_tile_counter)

    @property
    def furiten(self):
        return self.discard_furiten or self.riichi_furiten or self.round_furiten

    def is_agari(self):
        return is_agari(self.hand_tile_counter)

    def display_tiles(self, style='ascii'):
        if style == 'ascii':
            return ascii_style_print([sorted(self.tiles)])
        return ' '.join(TENHOU_TILE_STRING_DICT[_] for _ in sorted(self.tiles))

    def display_furo(self, style='ascii'):
        if self.furo:
            if style == 'ascii':
                return ascii_style_print(list(self.furo.values()))
            else:
                return ' '.join(['「' + ' '.join([TENHOU_TILE_STRING_DICT[_] for _ in furo]) + '」' for furo in self.furo.values()])

    def draw(self, tile_id):
        self.tiles.add(tile_id)
        self.hand_tile_counter[tile_id // 4] += 1

    def discard(self, tile_id):
        tile = tile_id // 4
        self.tiles.remove(tile_id)
        self.discard_tiles.append(tile_id)
        self.river.append(tile_id)
        self.hand_tile_counter[tile] -= 1
        if self.is_playback:  # 回放模式不计算振听和听牌（不然太慢了）
            return
        self.round_furiten = False
        if self.hand_tile_counter == self.hand_tile_counter_bak:
            if tile in self.machi:
                self.discard_furiten = True
            return
        self.hand_tile_counter_bak = copy(self.hand_tile_counter)
        if not self.riichi_status:
            if check_machi(self.hand_tile_counter):
                self.machi = machi(self.hand_tile_counter)
                self.discard_furiten = bool(self.machi.intersection(set(map(lambda x: x // 4, self.discard_tiles))))
            else:
                self.machi.clear()
                self.discard_furiten = False

    def riichi(self, double_riichi=False):
        if self.riichi_status:
            return False
        if double_riichi:
            self.riichi_status = 2
        else:
            self.riichi_status = 1
        self.ippatsu_status = 1
        self.riichi_round = len(self.discard_tiles)
        self.score -= 10
        self.machi = machi(self.hand_tile_counter)
        return True

    def check_pon(self, tile_id):
        if self.riichi_status:
            return False, None
        tile = tile_id // 4
        if self.hand_tile_counter[tile] >= 2:
            return True, tile
        return False, None

    def check_chi(self, tile_id):
        if self.riichi_status:
            return False, []
        tile = tile_id // 4
        if tile // 9 == 3:  # 字牌
            return False, []
        tile_count = len(self.tiles)
        if self.hand_tile_counter[tile] == tile_count - 2:  # 禁止现物食替
            return False, []
        d = tile % 9
        patterns = []
        if d == 0:
            if self.hand_tile_counter[tile + 1] and self.hand_tile_counter[tile + 2]:
                if self.hand_tile_counter[tile] + self.hand_tile_counter[tile + 3] == tile_count - 2:  # 禁止现物、筋食替
                    return False, []
                return True, [tile]
            return False, []
        if d == 8:
            if self.hand_tile_counter[tile - 1] and self.hand_tile_counter[tile - 2]:
                if self.hand_tile_counter[tile] + self.hand_tile_counter[tile - 3] == tile_count - 2:
                    return False, []
                return True, [tile - 2]
            return False, []
        if d == 1:
            if self.hand_tile_counter[tile - 1] and self.hand_tile_counter[tile + 1]:
                patterns.append(tile - 1)
            if self.hand_tile_counter[tile + 1] and self.hand_tile_counter[tile + 2]:
                if self.hand_tile_counter[tile] + self.hand_tile_counter[tile + 3] != tile_count - 2:
                    patterns.append(tile)
            if patterns:
                return True, patterns
            return False, []
        if d == 7:
            if self.hand_tile_counter[tile - 1] and self.hand_tile_counter[tile + 1]:
                patterns.append(tile - 1)
            if self.hand_tile_counter[tile - 1] and self.hand_tile_counter[tile - 2]:
                if self.hand_tile_counter[tile] + self.hand_tile_counter[tile - 3] != tile_count - 2:
                    patterns.append(tile - 2)
            if patterns:
                return True, patterns
            return False, []
        if self.hand_tile_counter[tile - 1] and self.hand_tile_counter[tile - 2]:
            if self.hand_tile_counter[tile] + self.hand_tile_counter[tile - 3] != tile_count - 2:
                patterns.append(tile - 2)
        if self.hand_tile_counter[tile - 1] and self.hand_tile_counter[tile + 1]:
            patterns.append(tile - 1)
        if self.hand_tile_counter[tile + 1] and self.hand_tile_counter[tile + 2]:
            if self.hand_tile_counter[tile] + self.hand_tile_counter[tile + 3] != tile_count - 2:
                patterns.append(tile)
        if patterns:
            return True, patterns
        return False, []

    def check_kan(self, tile_id, mode):
        if mode == 1:  # 明杠
            if self.riichi_status:
                return False, None
            pattern = tile_id // 4
            if self.hand_tile_counter[pattern] == 3:
                return True, (1, pattern, tile_id)
            return False, None
        if mode == 0:  # 暗杠
            if self.riichi_status:
                """
                立直时暗杠的条件是
                1、只有摸到的牌才能暗杠
                2、不能改变听牌
                计算听牌需要循环多次，故先检查1
                """
                pattern = tile_id // 4
                if self.hand_tile_counter[pattern] == 4:
                    counter = copy(self.hand_tile_counter)
                    counter[pattern] = 0
                    new_machi = machi(counter)
                    if self.machi == new_machi:
                        return True, [(0, pattern, tile_id)]
                return False, []
            ankan_patterns = list(filter(lambda x: x[1] == 4, self.hand_tile_counter.items()))
            ankan_patterns = [(0, _[0], _[0] * 4) for _ in ankan_patterns]
            return bool(ankan_patterns), ankan_patterns
        # 加杠
        add_kan_patterns = []
        for (furo_type, ptn), tile_set in self.furo.items():
            if furo_type == 1 and self.hand_tile_counter[ptn]:  # 碰出的刻子可以加杠
                add = {ptn * 4 + _ for _ in range(4)}.difference(tile_set).pop()
                add_kan_patterns.append((2, ptn, add))
        return bool(add_kan_patterns), add_kan_patterns

    def can_declare_riichi(self):
        if self.kui:  # 非门前清
            return False
        if self.riichi_status:  # 已经立直的情况下
            return False
        if self.score < 10:  # 点棒不够1000
            return False
        return check_riichi(self.hand_tile_counter)

    def pon(self, tile_id_list, kui_tile, from_who=None):
        self.tiles.difference_update(tile_id_list)
        ptn = kui_tile // 4
        self.furo[(1, ptn)] = list(tile_id_list)
        self.kui_info.append((kui_tile, from_who))
        self.kui = True
        self.hand_tile_counter[ptn] -= 2

    def chi(self, tile_id_list, kui_tile, from_who=None):
        for tile_id in tile_id_list:
            if tile_id != kui_tile:
                self.hand_tile_counter[tile_id // 4] -= 1
        self.tiles.difference_update(tile_id_list)
        key = (0, (min(tile_id_list) // 4, len(self.furo)))
        self.furo[key] = list(tile_id_list)
        self.kui_info.append((kui_tile, from_who))
        self.kui = True

    def kan(self, tile_id_list, add=None, mode=0, kui_tile=None, from_who=None):
        ptn = tile_id_list[0] // 4
        if mode == 0:  # 暗杠
            self.tiles.difference_update(tile_id_list)
            self.furo[(2, ptn)] = list(tile_id_list)
            self.hand_tile_counter[ptn] = 0
            self.kui_info.append((kui_tile, from_who))
        elif mode == 1:  # 明杠
            self.tiles.difference_update(tile_id_list)
            self.furo[(3, ptn)] = list(tile_id_list)
            self.kui = True
            self.hand_tile_counter[ptn] = 0
            self.kui_info.append((kui_tile, from_who))
        else:  # 加杠
            assert add is not None
            self.tiles.difference_update({add})
            new_key = (3, ptn)
            old_key = (1, ptn)
            items = list(self.furo.items())
            for i, (key, value) in enumerate(items):
                if key == old_key:
                    value.append(add)
                    items[i] = (new_key, value)
                    self.kui_info[i] = (add, *self.kui_info[i])
                    break
            self.furo = OrderedDict(items)
            self.hand_tile_counter[ptn] = 0

    def search_furo(self, furo_type, pattern, tile_id):
        kui_tile = tile_id // 4
        if furo_type == 0:  # 吃
            if kui_tile == pattern:
                first = list(filter(lambda x: x // 4 == pattern + 1, self.tiles))
                second = list(filter(lambda x: x // 4 == pattern + 2, self.tiles))
                furo_candidates = list(product(first, second))
            elif kui_tile == pattern + 1:
                first = list(filter(lambda x: x // 4 == pattern, self.tiles))
                second = list(filter(lambda x: x // 4 == pattern + 2, self.tiles))
                furo_candidates = list(product(first, second))
            else:
                first = list(filter(lambda x: x // 4 == pattern, self.tiles))
                second = list(filter(lambda x: x // 4 == pattern + 1, self.tiles))
                furo_candidates = list(product(first, second))
        elif furo_type == 1:  # 碰
            same_tiles = list(filter(lambda x: x // 4 == pattern, self.tiles))
            furo_candidates = combinations(same_tiles, 2)
        elif furo_type == 2:  # 加杠
            furo_candidates = self.furo.get((1, pattern))
            return furo_candidates

        elif furo_type == 3:  # 明杠
            furo_candidates = [pattern * 4 + i for i in range(4)]
            return furo_candidates
        else:  # 暗杠
            furo_candidates = [pattern * 4 + i for i in range(4)]
            return furo_candidates
        # 对碰、吃的可行方案进行去重
        seen = set()
        aka_seen = set()
        unique_candidates = []
        for a, b in furo_candidates:
            ptn = (a // 4, b // 4)
            has_aka = a in [16, 52, 88] or b in [16, 52, 88]
            if (not has_aka and ptn not in seen) or (has_aka and ptn not in aka_seen):
                unique_candidates.append(list(sorted([a, b, tile_id])))
                if has_aka:
                    aka_seen.add(ptn)
                else:
                    seen.add(ptn)
        return unique_candidates


class AiAgent(object):
    def __init__(self):
        self.device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

        self.discard_model = None
        self.riichi_model = None
        self.chi_model = None
        self.pon_model = None
        self.kan_model = None

        self.riichi_threshold = self.chi_threshold = self.pon_threshold = self.kan_threshold = None

        self.load_discard_model('model/saved/discard-model/best.pt')
        self.load_riichi_model('model/saved/riichi-model/best.pt')
        self.load_chi_model('model/saved/chi-model/best.pt')
        self.load_pon_model('model/saved/pon-model/best.pt')
        self.load_kan_model('model/saved/kan-model/best.pt')

    def load_discard_model(self, model_path):
        if os.path.isfile(model_path):
            params = torch.load(model_path, map_location=self.device)
            state_dict = params['state_dict']
            num_layers = params['num_layers']
            in_channels = params['in_channels']
            self.discard_model = DiscardModel(num_layers=num_layers, in_channels=in_channels)
            self.discard_model.load_state_dict(state_dict)
            self.discard_model.to(self.device)
            self.discard_model.eval()
            logging.debug(yellow('Discard model loaded'))

    def load_riichi_model(self, model_path):
        if os.path.isfile(model_path):
            params = torch.load(model_path, map_location=self.device)
            state_dict = params['state_dict']
            num_layers = params['num_layers']
            in_channels = params['in_channels']
            self.riichi_threshold = params['threshold']
            self.riichi_model = RiichiModel(num_layers=num_layers, in_channels=in_channels)
            self.riichi_model.load_state_dict(state_dict)
            self.riichi_model.to(self.device)
            self.riichi_model.eval()
            logging.debug(yellow('Riichi model loaded'))

    def load_chi_model(self, model_path):
        if os.path.isfile(model_path):
            params = torch.load(model_path, map_location=self.device)
            state_dict = params['state_dict']
            num_layers = params['num_layers']
            in_channels = params['in_channels']
            self.chi_threshold = params['threshold']
            self.chi_model = FuroModel(num_layers=num_layers, in_channels=in_channels)
            self.chi_model.load_state_dict(state_dict)
            self.chi_model.to(self.device)
            self.chi_model.eval()
            logging.debug(yellow('Chi model loaded'))

    def load_pon_model(self, model_path):
        if os.path.isfile(model_path):
            params = torch.load(model_path, map_location=self.device)
            state_dict = params['state_dict']
            num_layers = params['num_layers']
            in_channels = params['in_channels']
            self.pon_threshold = params['threshold']
            self.pon_model = FuroModel(num_layers=num_layers, in_channels=in_channels)
            self.pon_model.load_state_dict(state_dict)
            self.pon_model.to(self.device)
            self.pon_model.eval()
            logging.debug(yellow('Pon model loaded'))

    def load_kan_model(self, model_path):
        if os.path.isfile(model_path):
            params = torch.load(model_path, map_location=self.device)
            state_dict = params['state_dict']
            num_layers = params['num_layers']
            in_channels = params['in_channels']
            self.kan_threshold = params['threshold']
            self.kan_model = FuroModel(num_layers=num_layers, in_channels=in_channels)
            self.kan_model.load_state_dict(state_dict)
            self.kan_model.to(self.device)
            self.kan_model.eval()
            logging.debug(yellow('Kan model loaded'))

    def discard(self, state, tiles):
        if len(tiles) == 1:
            return tiles[0], 1
        if self.discard_model is None:
            return random.choice(tiles), 1 / len(tiles)
        state = torch.from_numpy(state).float()[None].to(self.device)
        output = self.discard_model(state).softmax(1)[0]
        available = list(set([_ // 4 for _ in tiles]))
        prob = output[available]
        pred = available[prob.argmax().item()]
        candidates = [_ for _ in tiles if _ // 4 == pred]
        discard_id = max(candidates)  # 取max可以确保不优先打赤牌（虽然也偶尔有需要优先打赤牌的需求，但可以忽略不计）
        return discard_id, max(prob)

    def riichi_decision(self, state):
        if self.riichi_model is None:
            return True
        state = torch.from_numpy(state).float()[None].to(self.device)
        return self.riichi_model(state)[0].sigmoid().item() / self.riichi_threshold / 2

    def agari_decision(self, agents, agari_action):
        return True

    def chi_decision(self, state):
        if self.chi_model is None:
            return random.random()
        state = torch.from_numpy(state).float()[None].to(self.device)
        return self.chi_model(state)[0].sigmoid().item() / self.chi_threshold / 2

    def pon_decision(self, state):
        if self.pon_model is None:
            return random.random()
        state = torch.from_numpy(state).float()[None].to(self.device)
        return self.pon_model(state)[0].sigmoid().item() / self.pon_threshold / 2

    def kan_decision(self, state):
        if self.kan_model is None:
            return random.random()
        state = torch.from_numpy(state).float()[None].to(self.device)
        return self.kan_model(state)[0].sigmoid().item() / self.kan_threshold / 2