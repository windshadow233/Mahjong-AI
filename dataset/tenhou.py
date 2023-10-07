import os
import warnings
import xml.etree.ElementTree as ET
import numpy as np
import re
import tqdm

from mahjong.game import MahjongGame
from mahjong.utils import YAKU_LIST
from mahjong.check_agari import is_agari
from collections import Counter


class TenhouData(object):
    def __init__(self, log_file):
        self.file = log_file
        try:
            tree = ET.parse(log_file)
        except ET.ParseError as e:
            print(log_file)
            print(e)
            os.remove(log_file)
            return
        self.root = tree.getroot()
        self.type = self.game_type()
        if not self.is_four_player_game():
            raise RuntimeError('暂不支持三人麻将')

    def get_rank(self):
        for child in self.root:
            if 'owari' in child.attrib:
                owari = list(map(float, child.attrib['owari'].split(',')))[1::2]
                return np.array(owari).argsort().tolist()[::-1]

    def print_info(self, info_int):
        print('牌局信息: ')
        if info_int & 0x01:
            print('PVP', end=' ')
        else:
            print('PVE', end=' ')
        if info_int & 0x02:
            print('无赤牌', end=' ')
        else:
            print('有赤牌', end=' ')
        if info_int & 0x04:
            print('无食断', end=' ')
        else:
            print('有食断', end=' ')
        if info_int & 0x08:
            print('半庄战', end=' ')
        else:
            print('東风战', end=' ')
        if info_int & 0x10:
            raise RuntimeError('暂不支持三人麻将')
        if info_int & 0x20:
            print('特上、凤凰桌', end=' ')
        else:
            warnings.warn('该对局段位较低，无法保证质量')
        if info_int & 0x40:
            print('速桌', end=' ')
        if info_int & 0x80:
            print('上级桌')

    def game_type(self):
        for child in self.root:
            if child.tag == 'GO':
                return int(child.attrib['type'])

    def is_four_player_game(self):
        return not bool(self.type & 0x10)

    def parse_discard_data(self, target=0):
        features = []
        labels = []
        game = MahjongGame(is_playback=True)
        has_aka = True
        draw_pattern = re.compile('[TUVW]\\d+')
        discard_pattern = re.compile('[DEFG]\\d+')
        iteration = iter(self.root)
        child = next(iteration)
        while 1:
            try:
                if child.tag == 'GO':
                    has_aka = not bool(int(child.attrib['type']) & 0x02)
                elif child.tag == 'INIT':
                    info = child.attrib
                    game.init_from_info(info, has_aka)
                elif child.tag == 'AGARI':
                    ...
                elif child.tag == 'N':
                    who = int(child.attrib['who'])
                    code = int(child.attrib['m'])
                    game.declare_furo(who, code)
                elif child.tag == 'RYUUKYOKU':
                    ...
                elif child.tag == 'REACH':
                    who = int(child.attrib['who'])
                    step = child.attrib['step']
                    if step == '1':
                        game.agents[who].declare_riichi = 1
                    else:
                        game.riichi(who)
                elif child.tag == 'DORA':
                    game.new_dora(int(child.attrib['hai']))
                elif draw_pattern.match(child.tag):
                    game.draw('TUVW'.index(child.tag[0]), int(child.tag[1:]))
                elif discard_pattern.match(child.tag):
                    who = 'DEFG'.index(child.tag[0])
                    if who == target and not game.agents[target].riichi_status:
                        features.append(game.get_feature(target))
                        labels.append(int(child.tag[1:]))
                    game.discard(who, int(child.tag[1:]))
                child = next(iteration)
            except StopIteration:
                break
        return features, labels

    def parse_pon_data(self, target=0):
        features = []
        labels = []
        game = MahjongGame(is_playback=True)
        has_aka = True
        draw_pattern = re.compile('[TUVW]\\d+')
        discard_pattern = re.compile('[DEFG]\\d+')
        iteration = iter(self.root)
        child = next(iteration)
        while 1:
            try:
                if child.tag == 'GO':
                    has_aka = not bool(int(child.attrib['type']) & 0x02)
                elif child.tag == 'INIT':
                    info = child.attrib
                    game.init_from_info(info, has_aka)
                elif child.tag == 'AGARI':
                    ...
                elif child.tag == 'N':
                    who = int(child.attrib['who'])
                    code = int(child.attrib['m'])
                    game.declare_furo(who, code)
                elif child.tag == 'RYUUKYOKU':
                    ...
                elif child.tag == 'REACH':
                    who = int(child.attrib['who'])
                    step = child.attrib['step']
                    if step == '1':
                        game.agents[who].declare_riichi = 1
                    else:
                        game.riichi(who)
                elif child.tag == 'DORA':
                    game.new_dora(int(child.attrib['hai']))
                elif draw_pattern.match(child.tag):
                    game.draw('TUVW'.index(child.tag[0]), int(child.tag[1:]))
                elif discard_pattern.match(child.tag):
                    who = 'DEFG'.index(child.tag[0])
                    tile_id = int(child.tag[1:])
                    game.discard(who, tile_id)
                    if who != target:
                        can_pon, pon_pattern = game.check_pon(target, tile_id)
                        if can_pon:
                            """如果能碰牌,则判断该玩家是否碰了"""
                            child = next(iteration)
                            feature = game.get_feature(target)
                            pon_feature = game.get_pon_feature(target, pattern=pon_pattern, kui_tile=tile_id)
                            feature = np.concatenate([pon_feature, feature], axis=0)
                            features.append(feature)
                            if child.tag != 'N':  # 下一条log并非鸣牌
                                labels.append(0)
                            else:
                                who = int(child.attrib['who'])
                                code = int(child.attrib['m'])
                                if who != target:  # 鸣牌者并非目标
                                    labels.append(0)
                                else:
                                    if code & (1 << 3):
                                        labels.append(1)
                                    else:
                                        labels.append(0)
                            continue  # 重新回到循环开头，让前面的逻辑来处理这条记录
                child = next(iteration)
            except StopIteration:
                break
        return features, labels

    def parse_kan_data(self, target=0):
        features = []
        labels = []
        game = MahjongGame(is_playback=True)
        has_aka = True
        draw_pattern = re.compile('[TUVW]\\d+')
        discard_pattern = re.compile('[DEFG]\\d+')
        iteration = iter(self.root)
        child = next(iteration)
        while 1:
            try:
                if child.tag == 'GO':
                    has_aka = not bool(int(child.attrib['type']) & 0x02)
                elif child.tag == 'INIT':
                    info = child.attrib
                    game.init_from_info(info, has_aka)
                elif child.tag == 'AGARI':
                    ...
                elif child.tag == 'N':
                    who = int(child.attrib['who'])
                    code = int(child.attrib['m'])
                    game.declare_furo(who, code)
                elif child.tag == 'RYUUKYOKU':
                    ...
                elif child.tag == 'REACH':
                    who = int(child.attrib['who'])
                    step = child.attrib['step']
                    if step == '1':
                        game.agents[who].declare_riichi = 1
                    else:
                        game.riichi(who)
                elif child.tag == 'DORA':
                    game.new_dora(int(child.attrib['hai']))
                elif draw_pattern.match(child.tag):
                    who = 'TUVW'.index(child.tag[0])
                    tile_id = int(child.tag[1:])
                    game.draw(who, tile_id)
                    if who == target:
                        can_ankan, ankan_patterns = game.check_kan(target, tile_id, mode=0)
                        can_addkan, addkan_patterns = game.check_kan(target, tile_id, mode=2)
                        can_kan = can_ankan or can_addkan
                        kan_patterns = ankan_patterns + addkan_patterns
                        if can_kan:
                            """如果能杠牌,则判断该玩家是否杠了"""
                            child = next(iteration)
                            feature = game.get_feature(target)
                            if child.tag != 'N':  # 下一条log并非鸣牌
                                for kan_pattern in kan_patterns:
                                    kan_feature = game.get_kan_feature(target, pattern=kan_pattern)
                                    features.append(np.concatenate([kan_feature, feature], axis=0))
                                    labels.append(0)
                            else:  # 因为是自摸之后的鸣牌操作，则必定是暗杠或者加杠
                                code = int(child.attrib['m'])
                                if code & (1 << 4):  # 鸣了加杠
                                    pattern = ((code & 0xfe00) >> 9) // 3
                                else:  # 鸣了暗杠
                                    pattern = ((code & 0xff00) >> 8) // 4
                                for kan_pattern in kan_patterns:
                                    kan_feature = game.get_kan_feature(target, pattern=kan_pattern)
                                    features.append(np.concatenate([kan_feature, feature], axis=0))
                                    if kan_pattern[1] == pattern:
                                        labels.append(1)
                                    else:
                                        labels.append(0)
                            continue  # 重新回到循环开头，让前面的逻辑来处理这条记录
                elif discard_pattern.match(child.tag):
                    who = 'DEFG'.index(child.tag[0])
                    tile_id = int(child.tag[1:])
                    game.discard(who, tile_id)
                    # if who == target:
                    #     """天凤平台居然可以自己先打出去再声明加杠。。。大意了。但这种数据还是不要了，没必要为极少数据写一堆代码"""
                    if who != target:
                        can_kan, kan_pattern = game.check_kan(target, tile_id, mode=1)  # 检查明杠
                        if can_kan:
                            """如果能杠牌,则判断该玩家是否杠了"""
                            child = next(iteration)
                            feature = game.get_feature(target)
                            kan_feature = game.get_kan_feature(target, pattern=kan_pattern)
                            features.append(np.concatenate([kan_feature, feature], axis=0))
                            if child.tag != 'N':  # 下一条log并非鸣牌
                                labels.append(0)
                            else:
                                who = int(child.attrib['who'])
                                code = int(child.attrib['m'])
                                if who != target:  # 鸣牌者并非目标
                                    labels.append(0)
                                else:
                                    if not code & 0b111100:
                                        labels.append(1)
                                    else:
                                        labels.append(0)
                            continue  # 重新回到循环开头，让前面的逻辑来处理这条记录
                child = next(iteration)
            except StopIteration:
                break
        return features, labels

    def parse_chi_data(self, target=0):
        features = []
        labels = []
        game = MahjongGame(is_playback=True)
        has_aka = True
        draw_pattern = re.compile('[TUVW]\\d+')
        discard_pattern = re.compile('[DEFG]\\d+')
        iteration = iter(self.root)
        child = next(iteration)
        while 1:
            try:
                if child.tag == 'GO':
                    has_aka = not bool(int(child.attrib['type']) & 0x02)
                elif child.tag == 'INIT':
                    info = child.attrib
                    game.init_from_info(info, has_aka)
                elif child.tag == 'AGARI':
                    ...
                elif child.tag == 'N':
                    who = int(child.attrib['who'])
                    code = int(child.attrib['m'])
                    game.declare_furo(who, code)
                elif child.tag == 'RYUUKYOKU':
                    ...
                elif child.tag == 'REACH':
                    who = int(child.attrib['who'])
                    step = child.attrib['step']
                    if step == '1':
                        game.agents[who].declare_riichi = 1
                    else:
                        game.riichi(who)
                elif child.tag == 'DORA':
                    game.new_dora(int(child.attrib['hai']))
                elif draw_pattern.match(child.tag):
                    game.draw('TUVW'.index(child.tag[0]), int(child.tag[1:]))
                elif discard_pattern.match(child.tag):
                    who = 'DEFG'.index(child.tag[0])
                    tile_id = int(child.tag[1:])
                    game.discard(who, tile_id)
                    if who == (target - 1) % 4:
                        can_chi, chi_pattern = game.check_chi(target, tile_id)
                        if can_chi:
                            """如果能吃牌,则判断该玩家是否吃了"""
                            child = next(iteration)
                            feature = game.get_feature(target)
                            for ptn in chi_pattern:
                                chi_feature = game.get_chi_feature(target, pattern=ptn, kui_tile=tile_id)
                                features.append(np.concatenate([chi_feature, feature], axis=0))
                            if child.tag != 'N':  # 下一条log并非鸣牌
                                labels.extend([0] * len(chi_pattern))
                            else:
                                who = int(child.attrib['who'])
                                code = int(child.attrib['m'])
                                if who != target:  # 鸣牌者并非目标
                                    labels.extend([0] * len(chi_pattern))
                                else:
                                    if code & (1 << 2):
                                        t = (code & 0xfc00) >> 10
                                        t = t // 3
                                        t = t // 7 * 9 + t % 7
                                        for ptn in chi_pattern:
                                            if ptn == t:
                                                labels.append(1)
                                            else:
                                                labels.append(0)
                                    else:
                                        labels.extend([0] * len(chi_pattern))
                            continue  # 重新回到循环开头，让前面的逻辑来处理这条记录
                child = next(iteration)
            except StopIteration:
                break
        return features, labels

    def parse_riichi_data(self, target=0):
        features = []
        labels = []
        game = MahjongGame(is_playback=True)
        has_aka = True
        draw_pattern = re.compile('[TUVW]\\d+')
        discard_pattern = re.compile('[DEFG]\\d+')
        iteration = iter(self.root)
        child = next(iteration)
        while 1:
            try:
                if child.tag == 'GO':
                    has_aka = not bool(int(child.attrib['type']) & 0x02)
                elif child.tag == 'INIT':
                    info = child.attrib
                    game.init_from_info(info, has_aka)
                elif child.tag == 'AGARI':
                    ...
                elif child.tag == 'N':
                    who = int(child.attrib['who'])
                    code = int(child.attrib['m'])
                    game.declare_furo(who, code)
                elif child.tag == 'RYUUKYOKU':
                    ...
                    # print('流局')
                elif child.tag == 'REACH':
                    who = int(child.attrib['who'])
                    step = child.attrib['step']
                    if step == '1':
                        ...
                        game.agents[who].declare_riichi = 1
                        # if who == target:
                        #     print(game.players[who].hand_tile_counter)
                        #     print(game.players[who].display_tiles())
                    else:
                        game.riichi(who)
                elif child.tag == 'DORA':
                    game.new_dora(int(child.attrib['hai']))
                elif draw_pattern.match(child.tag):
                    who = 'TUVW'.index(child.tag[0])
                    game.draw(who, int(child.tag[1:]))
                    if who == target:
                        if game.can_declare_riichi(who):
                            features.append(game.get_feature(target))
                            child = next(iteration)
                            if child.tag == 'REACH':
                                labels.append(1)
                            else:
                                labels.append(0)
                            continue
                elif discard_pattern.match(child.tag):
                    game.discard('DEFG'.index(child.tag[0]), int(child.tag[1:]))
                child = next(iteration)
            except StopIteration:
                break
        return features, labels

    def parse_reward_data(self, target):
        features = []
        label = None
        game = MahjongGame(is_playback=True)
        has_aka = True
        draw_pattern = re.compile('[TUVW]\\d+')
        discard_pattern = re.compile('[DEFG]\\d+')
        iteration = iter(self.root)
        child = next(iteration)
        while 1:
            try:
                if child.tag == 'GO':
                    has_aka = not bool(int(child.attrib['type']) & 0x02)
                elif child.tag == 'INIT':
                    info = child.attrib
                    game.init_from_info(info, has_aka)
                elif child.tag == 'AGARI':
                    sc = child.attrib['sc']
                    target_sc = int(sc.split(',')[1::2][target])
                    features.append(game.get_game_feature(target_sc, game.agents[target].score))
                    if 'owari' in child.attrib:
                        label = int(child.attrib['owari'].split(',')[::2][target])
                elif child.tag == 'N':
                    who = int(child.attrib['who'])
                    code = int(child.attrib['m'])
                    game.declare_furo(who, code)
                elif child.tag == 'RYUUKYOKU':
                    sc = child.attrib['sc']
                    target_sc = int(sc.split(',')[1::2][target])
                    features.append(game.get_game_feature(target_sc, game.agents[target].score))
                    if 'owari' in child.attrib:
                        label = int(child.attrib['owari'].split(',')[::2][target])
                elif child.tag == 'REACH':
                    who = int(child.attrib['who'])
                    step = child.attrib['step']
                    if step == '1':
                        game.agents[who].declare_riichi = 1
                    else:
                        game.riichi(who)
                elif child.tag == 'DORA':
                    game.new_dora(int(child.attrib['hai']))
                elif draw_pattern.match(child.tag):
                    game.draw('TUVW'.index(child.tag[0]), int(child.tag[1:]))
                elif discard_pattern.match(child.tag):
                    game.discard('DEFG'.index(child.tag[0]), int(child.tag[1:]))
                child = next(iteration)
            except StopIteration:
                break
        return np.array(features), label
