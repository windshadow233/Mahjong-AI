import numpy as np
from typing import List
from .agent import Agent
from .utils import *
from .check_agari import is_agari, check_riichi

try:
    from random import SystemRandom
    random = SystemRandom()
except NotImplemented:
    import random


class MahjongGame(object):
    def __init__(self, has_aka=True, is_playback=False):
        self.yama = []  # 牌山
        self.left_num = 0  # 流局剩余牌数
        self.has_aka = has_aka  # 是否是赤牌规则
        self.round = 0  # 局顺
        self.round_wind = 27  # 场风
        self.honba = 0  # 场棒
        self.riichi_ba = 0  # 立直棒
        self.dora_indicator = []  # 宝牌指示牌
        self.dora = []  # 宝牌
        self.ura_dora_indicator = []  # 里宝指示牌
        self.ura_dora = []  # 里宝牌
        self.oya = 0  # 亲家
        self.kang_num = [0] * 4  # 每个玩家的开杠数
        self.agents: List[Agent] = [Agent(250, set(), i, is_playback=is_playback) for i in range(4)]  # 玩家
        self.ranks = list(range(4))
        self.public_visible_tiles = Counter()  # 所有玩家均可见的牌的数量
        self.first_round = True  # 第一巡，用来判定天地和、九九流局等
        self.is_playback = is_playback

    def get_rank(self):
        scores = [(i, p.score) for i, p in enumerate(self.agents)]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def init_from_info(self, init_info, has_aka=True):
        """for playback only"""
        seed = init_info['seed']
        r, h, riichi, _, _, dora_indicator = map(int, seed.split(','))
        self.yama.clear()  # playback不需要牌山信息
        self.left_num = 136 - 13 * 4 - 14
        self.has_aka = has_aka
        self.round = r
        self.round_wind = [27, 28, 29, 30][r // 4]
        self.honba = h
        self.riichi_ba = riichi
        self.dora_indicator = [dora_indicator]
        self.dora = [get_dora(dora_indicator)]
        self.ura_dora_indicator = []
        self.ura_dora = []
        self.oya = int(init_info['oya'])
        self.kang_num = [0] * 4
        self.first_round = True

        scores = list(map(int, init_info['ten'].split(',')))
        tiles = [set(map(int, init_info[f'hai{i}'].split(','))) for i in range(4)]
        self.agents = [Agent(scores[i], tiles[i], (i - r % 4), is_playback=self.is_playback) for i in range(4)]
        index_scores = list(enumerate(scores))
        index_scores.sort(key=lambda x: x[1], reverse=True)
        self.ranks = [index_scores.index((i, p.score)) for i, p in enumerate(self.agents)]
        self.public_visible_tiles = Counter([dora_indicator // 4])

    def new_game(self, game_round, honba, riichi_ba):
        dice1, dice2 = random.randint(1, 6), random.randint(1, 6)
        start_side = (dice1 + dice2) % 4
        start_pos = -start_side * 17 * 2 + (dice1 + dice2) * 2
        self.yama = list(range(136))
        random.shuffle(self.yama)
        self.yama = self.yama[start_pos:] + self.yama[:start_pos]
        self.left_num = 136 - 13 * 4 - 14
        self.round = game_round
        self.round_wind = [27, 28, 29, 30][game_round // 4]
        self.honba = honba
        self.riichi_ba = riichi_ba
        dora_indicator = self.yama[-6]
        ura_dora_indicator = self.yama[-5]
        self.dora_indicator = [dora_indicator]
        self.dora = [get_dora(dora_indicator)]
        self.ura_dora_indicator = [ura_dora_indicator]
        self.ura_dora = [get_dora(ura_dora_indicator)]
        self.oya = game_round % 4
        self.kang_num = [0] * 4
        self.first_round = True

        for i in range(4):
            p = self.agents[(self.oya + i) % 4]
            self.agents[(self.oya + i) % 4] = Agent(
                p.score,
                set(self.yama[i*4:i*4+4] + self.yama[i*4+16:i*4+20] + self.yama[i*4+32:i*4+36] + self.yama[i+48:i+49]),
                i
            )
        self.yama = self.yama[52:]
        index_scores = list(enumerate([p.score for p in self.agents]))
        index_scores.sort(key=lambda x: x[1], reverse=True)
        self.ranks = [index_scores.index((i, p.score)) for i, p in enumerate(self.agents)]
        self.public_visible_tiles = Counter([dora_indicator // 4])

    def new_dora(self, dora=None):
        if dora is None:
            dora = self.yama[-6 - 2 * len(self.dora) + sum(self.kang_num)]
            ura_dora = self.yama[-5 - 2 * len(self.dora) + sum(self.kang_num)]
            self.ura_dora_indicator.append(ura_dora)
            self.ura_dora.append(get_dora(ura_dora))
        self.dora_indicator.append(dora)
        self.dora.append(get_dora(dora))
        self.public_visible_tiles[dora // 4] += 1

    def declare_furo(self, who, meld_code):
        """for playback only"""
        furo_type, tile_id_list, add_tile_id, where = parse_meld(meld_code)
        from_who = (who + where) % 4
        if furo_type == 0:
            self.chi(who, tile_id_list, kui_tile=add_tile_id, from_who=from_who)
        elif furo_type == 1:
            self.pon(who, tile_id_list, kui_tile=add_tile_id, from_who=from_who)
        elif furo_type == 2:
            self.kan(who, tile_id_list, add=add_tile_id, mode=2, from_who=from_who)
        elif furo_type == 3:
            self.kan(who, tile_id_list, mode=1, kui_tile=add_tile_id, from_who=from_who)
        elif furo_type == 4:
            self.kan(who, tile_id_list, mode=0, from_who=from_who)

    def check_pon(self, who, tile_id):
        if self.left_num == 0:
            return False, None
        return self.agents[who].check_pon(tile_id)

    def check_chi(self, who, tile_id):
        if self.left_num == 0:
            return False, []
        return self.agents[who].check_chi(tile_id)

    def check_kan(self, who, tile_id, mode):
        if self.left_num == 0:
            return False, []
        return self.agents[who].check_kan(tile_id, mode)

    def pon(self, who, tile_id_list, kui_tile, from_who=None):
        self.agents[who].pon(tile_id_list, kui_tile, from_who)
        self.public_visible_tiles[kui_tile // 4] += 2

    def chi(self, who, tile_id_list, kui_tile, from_who=None):
        for tile_id in tile_id_list:
            if tile_id != kui_tile:
                self.public_visible_tiles[tile_id // 4] += 1
        self.agents[who].chi(tile_id_list, kui_tile, from_who)

    def kan(self, who, tile_id_list, add=None, kui_tile=None, from_who=None, mode=0):
        """
        mode: 0=暗杠,1=明杠,2=加杠
        """
        self.agents[who].kan(tile_id_list, add=add, kui_tile=kui_tile, from_who=from_who, mode=mode)
        self.kang_num[who] += 1
        self.public_visible_tiles[tile_id_list[0] // 4] = 4

    def draw(self, who, tile_id=None, where=0):
        if tile_id is None:
            if where == -1:
                where = [-1, -2][sum(self.kang_num) % 2]
            tile_id = self.yama.pop(where)
        self.agents[who].draw(tile_id)
        self.left_num -= 1
        return tile_id

    def discard(self, who, tile_id):
        self.agents[who].discard(tile_id)
        self.public_visible_tiles[tile_id // 4] += 1

    def can_declare_riichi(self, who):
        if self.left_num < 4:
            return False
        return self.agents[who].can_declare_riichi()

    def riichi(self, who, double_riichi=False):
        if self.agents[who].riichi(double_riichi):
            self.riichi_ba += 1

    @staticmethod
    def get_hand_tile_feature(counter):
        """
        自家手牌
        :param counter: Counter
        :return: (4, 34)
        """
        feature = np.zeros(shape=(4, 34))
        upper_triangle = np.tril(np.ones(4))
        for tile, c in counter.items():
            if c > 0:
                feature[:, tile] = upper_triangle[c - 1]
        return feature

    @staticmethod
    def get_furo_feature(furo_keys):
        """
        副露,每个副露4通道,共16通道
        :return: (4 * 4, 34)
        """
        total_feature = []
        for furo_type, ptn in furo_keys:
            feature = np.zeros(shape=(4, 34))
            if furo_type == 0:  # 吃
                ptn = ptn[0]
                feature[0, [ptn, ptn + 1, ptn + 2]] = 1
            elif furo_type == 1:  # 碰
                feature[[0, 1, 2], ptn] = 1
            else:  # 杠
                feature[:, ptn] = 1
            total_feature.append(feature)
        total_feature = np.concatenate([*total_feature, np.zeros(shape=(16 - len(total_feature) * 4, 34))], axis=0)
        return total_feature

    def get_visible_tiles_feature(self, target):
        visible = copy(self.public_visible_tiles)
        visible.update([_ // 4 for _ in self.agents[target].tiles])
        feature = np.zeros(shape=(4, 34))
        upper_triangle = np.tril(np.ones(4))
        for tile, c in visible.items():
            if c > 0:
                feature[:, tile] = upper_triangle[c - 1]
        return feature
        # visible = copy(self.public_visible_tiles)
        # upper_triangle = np.tril(np.ones(4))
        # feature1 = np.zeros(shape=(4, 34))  # 全场的可见牌
        # for tile, c in visible.items():
        #     if c > 0:
        #         feature1[:, tile] = upper_triangle[c - 1]
        # visible.update([_ // 4 for _ in self.agents[target].tiles])
        # feature2 = np.zeros(shape=(4, 34))  # 自己的可见牌
        # for tile, c in visible.items():
        #     if c > 0:
        #         feature2[:, tile] = upper_triangle[c - 1]
        # return np.concatenate([feature1, feature2], axis=0)

    def get_discard_tile_feature(self, discard_length=24):
        """
        四家舍牌
        :return: (4 * discard_length, 34)
        """
        feature = np.zeros(shape=(4 * discard_length, 34))
        for i, p in enumerate(self.agents):
            for j, tile in enumerate(p.discard_tiles):
                feature[i * discard_length + j, tile // 4] = 1
        return feature

    def get_dora_feature(self, dora_length=5):
        """
        宝牌
        :return: (dora_length, 34)
        """
        feature = np.zeros(shape=(dora_length, 34))
        for i, tile in enumerate(self.dora):
            feature[i, tile] = 1
        return feature

    def get_aka_feature(self, target):
        feature = np.zeros(shape=(3, 34))
        if 16 in self.agents[target].tiles:
            feature[0] = 1
        if 52 in self.agents[target].tiles:
            feature[1] = 1
        if 88 in self.agents[target].tiles:
            feature[2] = 1
        return feature

    def get_wall_feature(self, wall_length=70):
        feature = np.zeros(shape=(wall_length, 34))
        for tile_id in self.yama:
            feature[tile_id // 4] = 1
        return feature

    @staticmethod
    def get_integer_feature(n, digits=3):
        h, t, s = n // 100, (n % 100) // 10, n % 10
        if digits == 3:
            return np.concatenate([
                np.ones(shape=(h, 34)),
                np.zeros(shape=(10 - h, 34)),
                np.ones(shape=(t, 34)),
                np.zeros(shape=(10 - t, 34)),
                np.ones(shape=(s, 34)),
                np.zeros(shape=(10 - s, 34)),
            ], axis=0)
        if digits == 2:
            return np.concatenate([
                np.ones(shape=(t, 34)),
                np.zeros(shape=(10 - t, 34)),
                np.ones(shape=(s, 34)),
                np.zeros(shape=(10 - s, 34)),
            ], axis=0)
        if digits == 1:
            return np.concatenate([
                np.ones(shape=(s, 34)),
                np.zeros(shape=(10 - s, 34)),
            ], axis=0)

    def get_bucket_feature(self, number_list, bins, one_dim=False):
        cat_num = len(bins) + 1
        values = np.digitize(number_list, bins=bins)
        return np.concatenate([self.get_category_feature(_, cat_num, one_dim) for _ in values])

    @staticmethod
    def get_category_feature(category, cat_num, one_dim=False):
        """
        类别特征
        :return: (cat_num, 34)
        """
        if not one_dim:
            feature = np.zeros(shape=(cat_num, 34))
            feature[category].fill(1)
        else:
            feature = np.zeros(shape=(cat_num,))
            feature[category] = 1
        return feature

    def get_wind_feature(self, target):
        """
        自风、场风
        :return: (2, 34)
        """
        feature = np.zeros(shape=(2, 34))
        feature[0, self.agents[target].menfon] = 1
        feature[1, self.round_wind] = 1
        return feature

    def get_reach_feature(self):
        feature = np.zeros(shape=(4, 34))
        for i, p in enumerate(self.agents):
            feature[i].fill(p.riichi_status)
        return feature

    def get_pon_feature(self, who, pattern, kui_tile):
        player = self.agents[who]
        hand_tile_counter = copy(player.hand_tile_counter)
        furo = copy(player.furo)
        hand_tile_counter[pattern] -= 2
        furo[(1, pattern)] = []
        hand_tile_feature = self.get_hand_tile_feature(hand_tile_counter)
        furo_feature = self.get_furo_feature(furo.keys())
        is_dora = np.ones(shape=(1, 34)) * (pattern in self.dora)
        is_aka = np.ones(shape=(1, 34)) * (kui_tile in [16, 52, 88])
        return np.concatenate([
            is_dora,  # 1
            is_aka,  # 1
            hand_tile_feature,  # 4
            furo_feature  # 16
        ], axis=0)  # 22

    def get_chi_feature(self, who, pattern, kui_tile):
        player = self.agents[who]
        hand_tile_counter = copy(player.hand_tile_counter)
        furo = copy(player.furo)
        kui_ptn = kui_tile // 4
        if kui_ptn == pattern:
            hand_tile_counter[kui_ptn + 1] -= 1
            hand_tile_counter[kui_ptn + 2] -= 1
        elif kui_ptn == pattern + 1:
            hand_tile_counter[kui_ptn - 1] -= 1
            hand_tile_counter[kui_ptn + 1] -= 1
        else:
            hand_tile_counter[kui_ptn - 2] -= 1
            hand_tile_counter[kui_ptn - 1] -= 1
        furo[(0, (pattern, len(furo)))] = []
        hand_tile_feature = self.get_hand_tile_feature(hand_tile_counter)
        furo_feature = self.get_furo_feature(furo.keys())
        is_dora = np.ones(shape=(1, 34)) * (kui_ptn in self.dora)
        is_aka = np.ones(shape=(1, 34)) * (kui_tile in [16, 52, 88])
        return np.concatenate([
            is_dora,  # 1
            is_aka,  # 1
            hand_tile_feature,  # 4
            furo_feature  # 16
        ], axis=0)  # 22

    def get_kan_feature(self, who, pattern):
        player = self.agents[who]
        hand_tile_counter = copy(player.hand_tile_counter)
        furo = copy(player.furo)
        kan_type, kan_ptn, tile_id = pattern
        if kan_type == 2:
            furo.pop((1, kan_ptn))
            furo[(3, kan_ptn)] = []
        elif kan_type == 1:
            furo[(3, kan_ptn)] = []
        else:
            furo[(2, kan_ptn)] = []
        hand_tile_counter[kan_ptn] = 0
        hand_tile_feature = self.get_hand_tile_feature(hand_tile_counter)
        furo_feature = self.get_furo_feature(furo.keys())
        is_dora = np.ones(shape=(1, 34)) * (tile_id // 4 in self.dora)
        is_aka = np.ones(shape=(1, 34)) * (tile_id in [16, 52, 88])
        return np.concatenate([
            is_dora,  # 1
            is_aka,  # 1
            hand_tile_feature,  # 4
            furo_feature  # 16
        ], axis=0)  # 22

    def get_feature(self, target, hidden_info_mask=0):
        """ Oracle Agent能获取的全局信息 """
        # hand_features = []
        # for i in range(4):
        #     if i == target:
        #         hand_features.append(self.get_hand_tile_feature(self.agents[i].hand_tile_counter))
        #     elif hidden_info_mask == 0:
        #         hand_features.append(np.zeros(shape=(4, 34)))
        #     else:
        #         hand_features.append(self.get_hand_tile_feature(self.agents[i].hand_tile_counter) * hidden_info_mask)
        # hand_feature = np.concatenate(hand_features)
        # wall_feature = self.get_wall_feature() * hidden_info_mask if hidden_info_mask > 0 else np.zeros(shape=(70, 34))
        hand_feature = self.get_hand_tile_feature(self.agents[target].hand_tile_counter)  # 手牌
        seat_feature = self.get_category_feature(target, 4)  # 自家座位
        rank_feature = self.get_category_feature(self.ranks[target], 4)  # 自家顺位
        discard_feature = self.get_discard_tile_feature(discard_length=24)  # 四家舍牌
        visible_tiles_feature = self.get_visible_tiles_feature(target)  # 可见牌特征
        dora_feature = self.get_dora_feature()  # 宝牌
        aka_feature = self.get_aka_feature(target)  # 赤牌
        wind_feature = self.get_wind_feature(target)  # 自风、场风
        left_num_feature = self.get_bucket_feature([self.left_num], bins=[5, 10, 22, 46])  # 剩余牌数（分为5个区间）
        furo_feature = [self.get_furo_feature(p.furo.keys()) for p in self.agents]  # 四家副露
        round_feature = self.get_category_feature(self.round, 16)  # 局顺
        honba_feature = self.get_category_feature(self.honba, 20)  # 本场棒
        riichi_ba_feature = self.get_category_feature(self.riichi_ba, 20)  # 立直棒
        score_feature = self.get_bucket_feature([_.score for _ in self.agents], bins=list(range(50, 450, 50)))  # 四家的分数，分为9个区间
        riichi_feature = self.get_reach_feature()  # 四家的立直情况
        oya_feature = self.get_category_feature(self.oya, 4)  # 亲家
        features = np.concatenate([
            hand_feature,  # 16
            # wall_feature,  # 70
            seat_feature,  # 4
            rank_feature,  # 4
            discard_feature,  # 4 * 24
            visible_tiles_feature,  # 4
            dora_feature,  # 5
            aka_feature,  # 3
            wind_feature,  # 2
            left_num_feature,  # 5
            *furo_feature,  # 16 * 4
            round_feature,  # 16
            honba_feature,  # 20
            riichi_ba_feature,  # 20
            score_feature,  # 9 * 4
            riichi_feature,  # 4
            oya_feature  # 4
        ], axis=0)  # 373
        return features

    def get_game_feature(self, round_score, target_score):
        round_score_feature = self.get_bucket_feature([round_score], bins=list(range(-200, 200, 20)), one_dim=True)
        score_feature = self.get_bucket_feature([target_score], bins=list(range(50, 450, 50)), one_dim=True)
        oya_feature = self.get_category_feature(self.oya, 4, one_dim=True)
        honba_feature = self.get_category_feature(self.honba, 20, one_dim=True)  # 本场棒
        riichi_ba_feature = self.get_category_feature(self.riichi_ba, 20, one_dim=True)  # 立直棒
        return np.concatenate([
            round_score_feature,
            score_feature,
            oya_feature,
            honba_feature,
            riichi_ba_feature
        ])
