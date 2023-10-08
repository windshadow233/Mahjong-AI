import socket
import signal
import os
import argparse
import sys
from typing import Union
import random
import numpy as np
from collections import defaultdict, OrderedDict
import json
import threading
import time
from queue import Queue
from uuid import uuid4

import torch
from quart.utils import run_sync
import traceback
import asyncio
import logging

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from mahjong.game import MahjongGame
from mahjong.agent import Agent, AiAgent
from model.models import RewardPredictor
from mahjong.utils import *
from mahjong.yaku import Yaku, YakuList
from mahjong.check_agari import *
from mahjong.display import *


class ControlledQueue(Queue):
    def __init__(self, maxsize=0):
        super(ControlledQueue, self).__init__(maxsize)
        self._allow_put = True

    def allow_put(self):
        self._allow_put = True

    def put(self, item, block: bool = ..., timeout=...) -> None:
        if self._allow_put:
            self._allow_put = False
            super().put(item, block, timeout)


class ClientConnection(object):
    def __init__(self, client_socket, username):
        self.client_socket = client_socket
        self.username = username
        self.message_queue = ControlledQueue()

    def __eq__(self, username):
        return self.username == username

    def is_human(self):
        return isinstance(self.client_socket, socket.SocketType)

    def is_ai(self):
        return not self.is_human() and self.client_socket != 'Disconnected'

    def send(self, msg):
        if self.is_human():
            self.client_socket.send(msg)

    def close(self):
        if self.is_human():
            self.client_socket.close()

    def recv(self):
        buffer = []
        while True:
            data = self.client_socket.recv(1)
            if len(data) == 0:
                break
            if data == b'\n':
                break
            buffer.append(data)
        return b''.join(buffer).decode('utf-8')

    def fetch_message(self):
        self.message_queue.allow_put()
        return self.message_queue.get()


class GameEnvironment(object):

    def __init__(self, has_aka=True, AI_count=0, min_score=0, fast=False, allow_observe=True, train=False):
        self.game = MahjongGame(has_aka, is_playback=False)
        self.agents = self.game.agents
        self.round = 0
        self.honba = 0
        self.riichi_ba = 0
        self.has_aka = has_aka

        self.clients = []
        self.observe_info = defaultdict(list)  # {who: [observer_client]}
        self.observers = {}  # {username: (observe_who, observer_client)}

        self.current_player = 0
        self.game_start = False
        self.AI_count = AI_count
        if AI_count > 0:
            self.ai_agent = AiAgent()
        else:
            self.ai_agent = None
        self.min_score = min_score
        self.fast = fast
        self.allow_observe = allow_observe
        self.train = train
        if train:
            self.device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
            params = torch.load('model/saved/reward-model/best.pt', map_location=self.device)
            self.reward_model = RewardPredictor(74, params['hidden_dims'], params['num_layers'])
            self.reward_model.load_state_dict(params['state_dict'])
            self.reward_model.to(self.device)
            self.collected_data = defaultdict(list)
            self.reward_features = defaultdict(list)
        for i in range(AI_count):
            self.clients.append(ClientConnection(f'一姬{i + 1}(简单)', username=f'一姬{i + 1}(简单)'))

    def reward(self, features, i):
        """计算第i轮的reward"""
        features = features.to(self.device)
        if i == 0:
            score0 = 250
            score1 = self.reward_model(features[:, :1, :]).item() * 500
        else:
            score0 = self.reward_model(features[:, :i, :]).item() * 500
            score1 = self.reward_model(features[:, :i + 1, :]).item() * 500
        return score1 - score0

    def start(self):
        for conn in self.clients:
            if conn.is_human():
                conn.message_queue = ControlledQueue()
        self.game.new_game(self.round, self.honba, self.riichi_ba)

    def reset(self):
        logging.info("Game is reset")
        self.game = MahjongGame(self.has_aka, is_playback=False)
        self.agents = self.game.agents
        self.round = 0
        self.honba = 0
        self.riichi_ba = 0

        self.clients.clear()
        self.observe_info.clear()
        self.observers.clear()

        self.current_player = 0
        self.game_start = False
        if self.train:
            self.collected_data.clear()
            self.reward_features.clear()
        for i in range(self.AI_count):
            self.clients.append(ClientConnection(f'一姬{i + 1}(简单)', username=f'一姬{i + 1}(简单)'))

    def update(self, key, value, client: ClientConnection = None):
        if client is None:
            self.send_multiply({'event': 'update', 'key': key, 'value': value})
        else:
            if client.is_human():
                self.send_personal(client, {'event': 'update', 'key': key, 'value': value})
            who = self.clients.index(client)
            self.send_observers(who, {'event': 'update', 'key': key, 'value': value})

    def player_join(self, client_socket, username, observe):
        if observe:
            if not self.allow_observe:
                response = {'event': 'join', 'status': 0, 'message': '服务端未开启观战'}
                self.send_personal(client_socket, response)
                return False, None
            username = username or random.choice([client.username for client in self.clients]) if self.clients else ''
            if username not in self.clients:
                response = {'event': 'join', 'status': -1, 'message': '该玩家不在房间内，已为你随机选择'}
                client = ClientConnection(client_socket, str(uuid4()))
                idx = random.randint(0, 3)
                self.observers[client.username] = (idx, client)
                self.observe_info[idx].append(client)
                self.send_personal(client_socket, response)
                if self.game_start:
                    self.send_all_game_info(client=client)
                else:
                    response = {'event': 'join', 'status': -1, 'message': '请等待其他玩家加入'}
                    self.send_personal(client_socket, response)
                return True, client
            idx = self.clients.index(username)
            response = {'event': 'join', 'status': -1, 'message': '成功加入观战位'}
            username = str(uuid4())
            client = ClientConnection(client_socket, username)
            logging.info(f"username: {username} join")
            self.observers[client.username] = (idx, client)
            self.observe_info[idx].append(client)
            self.send_personal(client_socket, response)
            if self.game_start:
                self.send_all_game_info(client=client)
            return True, client
        if len(username) > 8:
            response = {'event': 'join', 'status': 0, 'message': '用户名长度不能超过8'}
            self.send_personal(client_socket, response)
            return False, None
        if username in self.clients:
            idx = self.clients.index(username)
            if self.clients[idx].is_human():
                if not self.game_start:
                    response = {'event': 'join', 'status': 0, 'message': '用户名已被占用'}
                    self.send_personal(client_socket, response)
                    return False, None
                # else:
                #     response = {'event': 'join', 'status': 0, 'message': '您已在房间内'}
                #     self.send_personal(client_socket, response)
                #     return False, None
            if self.game_start and self.clients[idx].client_socket == 'Disconnected':
                client = self.clients[idx]
                client.client_socket = client_socket
                client.message_queue = ControlledQueue()
                response = {'event': 'join', 'status': 1, 'message': '欢迎重新加入游戏！'}
                self.send_personal(client_socket, response)
                self.send_all_game_info(client=client)
                return True, client
        if len(self.clients) >= 4:
            if self.allow_observe:
                response = {'event': 'join', 'status': -1, 'message': '房间人数已满，已加入观战位'}
                username = str(uuid4())
                client = ClientConnection(client_socket, username)
                logging.info(f"username: {username} join")
                idx = random.randint(0, 3)
                self.observers[client.username] = (idx, client)
                self.observe_info[idx].append(client)
                self.send_personal(client_socket, response)
                self.send_all_game_info(client=client)
                return True, client
            else:
                response = {'event': 'join', 'status': 0, 'message': '房间人数已满'}
                self.send_personal(client_socket, response)
                return False, None
        if not username:
            i = 1
            while 1:
                username = f'匿名玩家{i}'
                if username not in self.clients:
                    break
                i += 1
        logging.info(f"username: {username} join")
        client = ClientConnection(client_socket, username)
        self.clients.append(client)
        response = {'event': 'join', 'status': 1, 'message': f'成功加入房间, 您的用户名为「{username}」'}
        self.send_personal(client, response)
        if len(self.clients) < 4:
            self.send_multiply({'event': 'join', 'message': f'当前人数:{len(self.clients)}, 等待其他玩家加入...'})
        return True, client

    def player_disconnect(self, client: ClientConnection):
        logging.info(f"{client.username} leave")
        if client in self.clients:
            if not self.game_start:
                client.close()
                self.clients.remove(client)
                self.send_multiply({'event': 'quit', 'message': f'当前人数:{len(self.clients)},等待其他玩家加入...'})
            else:
                idx = self.clients.index(client)
                client.close()
                self.clients[idx].client_socket = 'Disconnected'
                if all(not _.is_human() for _ in self.clients):
                    self.reset()
        elif client.username in self.observers:
            client.close()
            who, client = self.observers.pop(client.username)
            self.observe_info[who].remove(client)

    def send_personal(self, client: Union[socket.SocketType, ClientConnection], message):
        # logging.debug(yellow(f"Send {message}"))
        message = json.dumps(message) + '\n'
        client.send(message.encode('utf-8'))

    def send_observers(self, who, message):
        observers = self.observe_info[who]
        for observer in list(observers):
            try:
                self.send_personal(observer, message)
            except:
                continue

    def send_multiply(self, message, exception=-1, exception_ob=-1):
        # logging.debug(yellow(f"Send multiply {message} except {exception}"))
        message = json.dumps(message).encode('utf-8') + b'\n'
        for i, client in enumerate(self.clients):
            if i == exception or not client.is_human():
                continue
            client.send(message)
        for username, (who, client) in self.observers.items():
            if who == exception_ob:
                continue
            try:
                client.send(message)
            except:
                continue

    def fetch_decision_message(self, client: ClientConnection, actions):
        if client.is_human():
            message = client.fetch_message()
            logging.debug(yellow(f"fetch message from queue: {message}"))
            if 'action' in message:
                return message['action']
        return actions[0]
        # who = self.clients.index(client)
        # return self.decision_by_ai(who, actions)

    def fetch_discard_message(self, who, client: ClientConnection, tiles, banned):
        if client.is_human():
            message = client.fetch_message()
            logging.debug(yellow(f"fetch message from queue: {message}"))
            if 'tile_id' in message:
                return message['tile_id']
        if tiles == 'all':
            tiles = list(self.agents[who].tiles)
        # return self.discard_by_ai(who, tiles, banned)
        return random.choice([_ for _ in tiles if _ // 4 not in banned])

    def decision_by_ai(self, who, actions, after_tsumo):
        state = self.game.get_feature(who)
        pon_action = None
        chi_actions = {}
        kan_actions = []
        pon_feature = None
        action_score_dict = {}

        for i, action in enumerate(actions):
            if action['type'] == 'agari':
                if self.ai_agent.agari_decision(self.agents, action):
                    action_score_dict[i] = 1
            elif action['type'] == 'riichi':
                score = self.ai_agent.riichi_decision(state)
                logging.debug(yellow(f'「{self.clients[who].username}」「立直」行为意愿: {score:.3f}'))
                action_score_dict[i] = score
            elif action['type'] == 'ryuukyoku':
                if action['kyuuhai_type_count'] == 9:
                    if self.agents[who].score >= 100:  # 只有9种9牌且分数没那么低时还是流了吧
                        action_score_dict[i] = 1
            elif action['type'] == 'pon':
                pattern = action['pattern']
                if pon_feature is None:
                    pon_feature = self.game.get_pon_feature(who, pattern[0] // 4, action['kui'])
                if pon_action is None:
                    pon_action = i, pon_feature
                else:  # 有多种碰的方法，则一定存在赤牌，方便起见，优先考虑将赤牌碰出去的操作
                    if {16, 52, 88}.intersection(pattern):
                        pon_action = i, pon_feature
            elif action['type'] == 'chi':
                pattern = action['pattern']
                chi_ptn = min(pattern) // 4
                chi_feature = chi_actions.get(chi_ptn, (i, self.game.get_chi_feature(who, chi_ptn, action['kui'])))[1]
                if chi_ptn not in chi_actions:
                    chi_actions[chi_ptn] = i, chi_feature
                else:  # 同一种顺子pattern有多种吃的方法，则一定存在赤牌，方便起见，优先考虑将赤牌吃出去的操作
                    if {16, 52, 88}.intersection(pattern):
                        chi_actions[chi_ptn] = i, chi_feature
            elif action['type'] == 'kan':
                pattern = action['pattern']
                kan_feature = self.game.get_kan_feature(who, pattern)
                kan_actions.append((i, kan_feature))
        if pon_action:
            i, pon_feature = pon_action
            pon_state = np.concatenate([pon_feature, state], axis=0)
            action_score_dict[i] = score = self.ai_agent.pon_decision(pon_state)
            logging.debug(yellow(f'「{self.clients[who].username}」「碰」行为意愿: {score:.3f}'))
        if chi_actions:
            for i, chi_feature in chi_actions.values():
                chi_state = np.concatenate([chi_feature, state], axis=0)
                action_score_dict[i] = score = self.ai_agent.chi_decision(chi_state)
                logging.debug(yellow(f'「{self.clients[who].username}」「吃」行为意愿: {score:.3f}'))
        if kan_actions:
            for i, kan_feature in kan_actions:
                kan_state = np.concatenate([kan_feature, state], axis=0)
                action_score_dict[i] = score = self.ai_agent.kan_decision(kan_state)
                logging.debug(yellow(f'「{self.clients[who].username}」「杠」行为意愿: {score:.3f}'))
        if not after_tsumo and not self.fast:
            time.sleep(1 + random.random() * 3)
        if action_score_dict:
            max_score_action, max_score = max(action_score_dict.items(), key=lambda x: x[1])
            if max_score < 0.5:  # 行为意愿均低于阈值，选择pass
                return actions[0]
            if after_tsumo and not self.fast:
                time.sleep(1 + random.random() * 3)
            return actions[max_score_action]
        return actions[0]

    def discard_by_ai(self, who, tiles, banned):
        if not self.fast:
            time.sleep(1 + random.random() * 2)
        if banned:
            tiles = [_ for _ in tiles if _ // 4 not in banned]
        state = self.game.get_feature(who)
        discard, conf = self.ai_agent.discard(state, tiles)
        logging.debug(yellow(f"「{self.clients[who].username}」以置信度:{conf:.3f} 切出「{TENHOU_TILE_STRING_DICT[discard]}」"))
        if self.train:
            self.collected_data[who].append([state, discard // 4])
        return discard

    def print_agari_info(self, who, from_who, action):
        han = action['han']
        fu = action['fu']
        score = action['score']
        ret = action['yaku']
        yaku_list = action['yaku_list']
        if who != from_who:
            agari_info = f"「{self.clients[from_who].username}」放铳！「{self.clients[who].username}」荣和！役种: {'、'.join(yaku_list)}->"
        else:
            agari_info = f"「{self.clients[who].username}」自摸！役种: {'、'.join(yaku_list)}->"
        if isinstance(ret, List):
            if han >= 2:
                agari_info += f'{han}倍役满！'
            else:
                agari_info += '役满！'
        else:
            agari_info += f'{han}番({fu}符)->基本点: {score}'
        logging.info(cyan(agari_info))
        self.agents[who].tiles.difference_update({action['machi']})
        logging.info(cyan(self.agents[who].display_tiles('str') + '  ' + TENHOU_TILE_STRING_DICT[action['machi']]))
        if self.agents[who].furo:
            logging.info(cyan(self.agents[who].display_furo('str')))

    def game_update(self, res):
        change_oya = True
        self.honba = honba = self.game.honba
        self.riichi_ba = riichi_ba = self.game.riichi_ba
        oya = self.game.oya
        score_delta = [0, 0, 0, 0]
        if isinstance(res, list):  # 和牌
            first_winner = res[0]['who']
            for action in res:
                who = action['who']
                from_who = action['from_who']
                score = action['score']
                if who == from_who:  # 自摸
                    if who == oya:
                        score = ((score * 2) + 90) // 100
                        for i in range(4):
                            if i != oya:
                                self.agents[i].score -= score + honba
                                score_delta[i] -= score + honba
                        self.agents[who].score += score * 3 + honba * 3
                        score_delta[who] += score * 3 + honba * 3
                        change_oya = False
                    else:
                        score_oya = ((score * 2) + 90) // 100
                        score = (score + 90) // 100
                        for i in range(4):
                            if i == who:
                                self.agents[i].score += score_oya + score * 2 + honba * 3
                                score_delta[i] += score_oya + score * 2 + honba * 3
                            elif i == oya:
                                self.agents[i].score -= score_oya + honba
                                score_delta[i] -= score_oya + honba
                            else:
                                self.agents[i].score -= score + honba
                                score_delta[i] -= score + honba
                else:
                    if who == oya:
                        score = ((score * 6) + 90) // 100 + honba * 3
                        change_oya = False
                    else:
                        score = ((score * 4) + 90) // 100 + honba * 3
                    self.agents[from_who].score -= score
                    self.agents[who].score += score
                    score_delta[from_who] -= score
                    score_delta[who] += score
                self.print_agari_info(who, from_who, action)
            if riichi_ba:
                self.agents[first_winner].score += riichi_ba * 10
                score_delta[first_winner] += riichi_ba * 10
            self.riichi_ba = 0
            if not change_oya:
                self.honba += 1
            else:
                self.honba = 0
        else:  # 流局
            why = res['why']
            if why == 'yama_end':  # 结算荒牌流局
                logging.info(cyan('荒牌流局'))
                nagashimangan = res['nagashimangan']
                machi_state = res['machi_state']
                for i in range(4):
                    if i in machi_state:
                        machi_tiles = machi_state[i][1]
                        logging.info(cyan(f"「{self.clients[i].username}」听牌: {'、'.join(TILE_STRING_DICT[_] for _ in machi_tiles)}"))
                change_oya = oya not in machi_state
                if nagashimangan:  # 流满
                    for i in nagashimangan:
                        logging.info(cyan(f"「{self.clients[i].username}」流局满贯！"))
                        for j in range(4):
                            if j == i:
                                if j == oya:
                                    self.agents[j].score += 120
                                    score_delta[j] += 120
                                else:
                                    self.agents[j].score += 80
                                    score_delta[j] += 80
                            else:
                                if j == oya:
                                    self.agents[j].score -= 40
                                    score_delta[j] -= 40
                                else:
                                    self.agents[j].score -= 20
                                    score_delta[j] -= 20
                else:
                    if 1 <= len(machi_state) < 4:
                        score_get = 30 // len(machi_state)
                        score_give = 30 // (4 - len(machi_state))
                        for i in range(4):
                            if i in machi_state:
                                self.agents[i].score += score_get
                                score_delta[i] += score_get
                            else:
                                self.agents[i].score -= score_give
                                score_delta[i] -= score_give
            else:
                if why == 'yao9':
                    who = res['who']
                    logging.info(cyan(f'流局: 「{self.clients[who].username}」九种九牌'))
                elif why == 'kaze4':
                    logging.info(cyan(f'流局: 四风连打'))
                elif why == 'kan4':
                    logging.info(cyan(f'流局: 四杠散了'))
                elif why == 'reach4':
                    logging.info(cyan(f'流局: 四家立直'))
                elif why == 'ron3':
                    logging.info(cyan(f'流局: 三家和了'))
                change_oya = False
            self.honba += 1
        if change_oya:
            self.round += 1
        if min(p.score for p in self.agents) * 100 < self.min_score:
            return True, score_delta
        if self.round > 11:
            return True, score_delta
        if self.round > 7 or (self.round == 7 and not change_oya):
            if max(p.score for p in self.agents) < 300:
                return False, score_delta
            if change_oya:
                if self.riichi_ba:
                    winner = max(((i, p.score) for i, p in enumerate(self.agents)), key=lambda x: x[1])[0]
                    self.agents[winner].score += self.riichi_ba * 10
                    self.riichi_ba = 0
                return True, score_delta
            winner = self.game.get_rank()[0][0]
            return winner == oya, score_delta
        else:
            return False, score_delta

    def get_game_info(self):
        return {
            'round': self.game.round,
            'honba': self.game.honba,
            'riichi_ba': self.game.riichi_ba,
            'dora_indicator': self.game.dora_indicator,
            'oya': self.game.oya,
            'agents': [
                {
                    'username': self.clients[i].username,
                    'score': p.score,
                    'tile_count': len(self.agents[i].tiles),
                    'furo': OrderedDict({str(x): y for x, y in p.furo.items()}),
                    'kui_info': p.kui_info,
                    'riichi': p.riichi_status,
                    'riichi_round': p.riichi_round,
                    'discard': p.discard_tiles,
                    'river': p.river,
                    'riichi_tile': p.riichi_tile,
                    'is_ai': self.clients[i].is_ai()
                } for i, p in enumerate(self.agents)
            ],
            'left_num': self.game.left_num
        }

    def get_player_info(self, who):
        p = self.agents[who]
        return {
            'username': self.clients[who].username,
            'seat': who,
            'tiles': list(p.tiles),
            'furo': OrderedDict({str(x): y for x, y in p.furo.items()}),
            'kui_info': p.kui_info,
            'machi': list(sorted(p.machi))
        }

    def send_player_score(self):
        self.send_multiply({'event': 'score', 'score': self.game.get_rank()})

    @run_sync
    def check_draw(self, who, tile_id, where):
        """
        检查并响应当前是否能和牌、立直、暗杠、加杠等，生成一个可行的行为列表并选择

        :return {
            'type': 'agari' / 'riichi' / 'kan' / 'pass' / 'ryuukyoku'
            'who': who,
            'from_who': who,
            'pattern'
        }
        """
        player = self.agents[who]
        connection = self.clients[who]
        actions = [{'type': 'pass'}]
        can_agari = False
        """判定和牌"""
        agari = None
        yaku = None
        tenhou = False  # 天、地和
        if tile_id // 4 in player.machi:
            if where == -1:
                tokusyu = 1
            elif self.game.left_num == 0:
                tokusyu = 3
            else:
                tokusyu = 0
            yaku = Yaku(
                hand_tiles=player.tiles,
                furo=player.furo,
                agarihai=tile_id,
                dora=self.game.dora,
                ura_dora=self.game.ura_dora,
                bahai=self.game.round_wind,
                menfon=player.menfon,
                tsumo=True,
                riichi=player.riichi_status,
                ippatsu=player.ippatsu_status,
                tokusyu=tokusyu,
                aka=self.has_aka
            )
            agari = yaku.agari
            if self.game.first_round:
                tenhou = True
                actions.append({'type': 'agari', 'who': who, 'from_who': who, 'machi': tile_id})
                can_agari = True
            elif yaku.naive_check_yaku():
                actions.append({'type': 'agari', 'who': who, 'from_who': who, 'machi': tile_id})
                can_agari = True
            else:
                if isinstance(agari, str):
                    x = list(map(lambda _: int(_, 16), agari.split(',')))
                    han, fu, score, ret = yaku.yaku(x)
                else:
                    if yaku.counter[yaku.agarihai] == 2:
                        ret = [YakuList.KOKUSHIJUSANMEN]
                        han = 2
                    else:
                        ret = [YakuList.KOKUSHIMUSO]
                        han = 1
                    fu = 25
                    score = han * 8000
                if han > 0:
                    actions.append({'type': 'agari', 'who': who, 'from_who': who, 'yaku': ret, 'han': han, 'fu': fu,
                                    'score': score, 'machi': tile_id})
                    can_agari = True
        """判定九种九牌"""
        if self.game.first_round:
            kyuuhai_type_count = len({_ // 4 for _ in player.tiles}.intersection([0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33]))
            if kyuuhai_type_count >= 9:
                actions.append({'type': 'ryuukyoku', 'who': who, 'why': 'yao9', 'kyuuhai_type_count': kyuuhai_type_count})
        """判定立直"""
        can_riichi = self.game.can_declare_riichi(who)
        if can_riichi:
            actions.append({'type': 'riichi', 'who': who, 'step': 1, 'double_riichi': self.game.first_round})

        """判定杠"""
        can_ankan, ankan_patterns = self.game.check_kan(who, tile_id, mode=0)
        can_addkan, addkan_pattern = self.game.check_kan(who, tile_id, mode=2)
        if can_ankan or can_addkan:
            for ptn in ankan_patterns + addkan_pattern:
                actions.append({'type': 'kan', 'pattern': ptn, 'who': who, 'from_who': who})
        if len(actions) > 1:
            message = {'event': 'decision', 'actions': actions}
            self.send_observers(who, message)
            if connection.is_human():
                self.send_personal(connection, message)
                action = self.fetch_decision_message(connection, actions)
            else:
                action = self.decision_by_ai(who, actions, True)
            if action['type'] == 'agari':
                if 'yaku' not in action:
                    if isinstance(agari, str):
                        x = list(map(lambda _: int(_, 16), agari.split(',')))
                        han, fu, score, ret = yaku.yaku(x)
                    else:
                        if yaku.counter[yaku.agarihai] == 2:
                            ret = [YakuList.KOKUSHIJUSANMEN]
                            han = 2
                        else:
                            ret = [YakuList.KOKUSHIMUSO]
                            han = 1
                        fu = 25
                        score = han * 8000
                    if tenhou:
                        han += 1
                        if isinstance(ret, list):
                            if who == self.game.oya:
                                tenhou = YakuList.TENHOU
                                if YakuList.KOKUSHIMUSO in ret:
                                    ret.remove(YakuList.KOKUSHIMUSO)
                                    ret.append(YakuList.KOKUSHIJUSANMEN)
                                    han += 1
                                elif YakuList.CHURENPOTO in ret:
                                    ret.remove(YakuList.CHURENPOTO)
                                    ret.append(YakuList.CHURENCHUMEN)
                                    han += 1
                                elif YakuList.SUANKO in ret:
                                    ret.remove(YakuList.SUANKO)
                                    ret.append(YakuList.SUANKOTANKI)
                                    han += 1
                            else:
                                tenhou = YakuList.CHIHOU
                            ret.append(tenhou)
                            score += 8000
                        else:
                            ret = [YakuList.TENHOU if who == self.game.oya else YakuList.CHIHOU]
                            han = 1
                            score = 8000
                    action['yaku'] = ret
                    action['han'] = han
                    action['fu'] = fu
                    action['score'] = score
                action['yaku_list'] = yaku.parse_yaku_ret(action['yaku'], True)
                action['hai'] = yaku.hand_tiles
                action['furo'] = list(yaku.furo.values())
            elif can_agari:  # 见逃
                if player.riichi_status:
                    player.riichi_furiten = True
                    self.update('furiten', True, connection)
        else:
            action = None
        return action

    @run_sync
    def check_discard(self, who, from_who, is_next_player, tile_id, add_kan=False):
        """
        检查并响应别家打出的牌是否能和牌、吃、碰、明杠，返回一个可行的行为列表并选择，add_kan=True时只判断抢杠和牌

        :return {
            'type': 'agari' / 'chi' / 'pon' / 'kan' / 'pass'
            'pattern': [int]
        }
        """
        player = self.agents[who]
        connection = self.clients[who]
        actions = [{'type': 'pass', 'who': who}]
        can_agari = False
        yaku = None
        agari = None
        if not player.furiten:
            """判定和牌"""
            if tile_id // 4 in player.machi:
                if add_kan:
                    tokusyu = 2
                elif self.game.left_num == 0:
                    tokusyu = 3
                else:
                    tokusyu = 0
                yaku = Yaku(
                    hand_tiles=player.tiles.union({tile_id}),
                    furo=player.furo,
                    agarihai=tile_id,
                    dora=self.game.dora,
                    ura_dora=self.game.ura_dora,
                    bahai=self.game.round_wind,
                    menfon=player.menfon,
                    tsumo=False,
                    riichi=player.riichi_status,
                    ippatsu=player.ippatsu_status,
                    tokusyu=tokusyu,
                    aka=self.has_aka
                )
                agari = yaku.agari
                if yaku.naive_check_yaku():
                    actions.append({'type': 'agari', 'who': who, 'from_who': from_who, 'machi': tile_id})
                    can_agari = True
                else:
                    if isinstance(agari, str):
                        x = list(map(lambda _: int(_, 16), agari.split(',')))
                        han, fu, score, ret = yaku.yaku(x)
                    else:
                        if yaku.counter[yaku.agarihai] == 2:
                            ret = [YakuList.KOKUSHIJUSANMEN]
                            han = 2
                        else:
                            ret = [YakuList.KOKUSHIMUSO]
                            han = 1
                        fu = 25
                        score = han * 8000
                    if han > 0:
                        actions.append(
                            {'type': 'agari', 'who': who, 'from_who': from_who, 'yaku': ret, 'han': han, 'fu': fu,
                             'score': score, 'machi': tile_id})
                        can_agari = True
                    else:
                        player.round_furiten = True
                        self.update('furiten', True, connection)
        if not add_kan:
            """判断吃碰杠"""
            if is_next_player:
                can_chi, patterns = self.game.check_chi(who, tile_id)
                for pattern in patterns:
                    for furo in player.search_furo(0, pattern, tile_id):
                        actions.append(
                            {'type': 'chi', 'who': who, 'from_who': from_who, 'pattern': furo, 'kui': tile_id})
            can_pon, pattern = self.game.check_pon(who, tile_id)
            if can_pon:
                for furo in player.search_furo(1, pattern, tile_id):
                    actions.append({'type': 'pon', 'who': who, 'from_who': from_who, 'pattern': furo, 'kui': tile_id})
            can_kan, pattern = self.game.check_kan(who, tile_id, mode=1)
            if can_kan:
                actions.append({'type': 'kan', 'who': who, 'from_who': from_who, 'pattern': pattern, 'kui': tile_id})
        if len(actions) > 1:
            message = {'event': 'decision', 'actions': actions}
            self.send_observers(who, message)
            if connection.is_human():
                self.send_personal(connection, message)
                action = self.fetch_decision_message(connection, actions)
            else:
                action = self.decision_by_ai(who, actions, False)
            if action['type'] == 'agari':
                if 'yaku' not in action:
                    if isinstance(agari, str):
                        x = list(map(lambda _: int(_, 16), agari.split(',')))
                        han, fu, score, ret = yaku.yaku(x)
                    else:
                        if yaku.counter[yaku.agarihai] == 2:
                            ret = [YakuList.KOKUSHIJUSANMEN]
                            han = 2
                        else:
                            ret = [YakuList.KOKUSHIMUSO]
                            han = 1
                        fu = 25
                        score = han * 8000
                    action['yaku'] = ret
                    action['han'] = han
                    action['fu'] = fu
                    action['score'] = score
                action['yaku_list'] = yaku.parse_yaku_ret(action['yaku'], False)
                action['hai'] = yaku.hand_tiles
                action['furo'] = list(yaku.furo.values())
            elif can_agari:  # 见逃
                if player.riichi_status:
                    player.riichi_furiten = True
                player.round_furiten = True
                self.update('furiten', True, connection)
        else:
            action = None
        return action

    async def handle_draw(self, who, tile_id=None, where=0):
        tile_id = self.game.draw(who=who, tile_id=tile_id, where=where)
        connection = self.clients[who]

        message = {'event': 'draw', 'who': who, 'tile_id': tile_id, 'where': where}
        if connection.is_human():
            self.send_personal(connection, message)
        self.send_observers(who, message)
        self.send_multiply({'event': 'draw', 'who': who, 'where': where}, exception=who, exception_ob=who)
        self.update('left_num', self.game.left_num)
        action = await self.check_draw(who, tile_id, where)
        # if where == -1:
        #     if action is None or action['type'] != 'agari':  # 如果没有杠上开花，需要翻新宝牌
        #         self.game.new_dora()
        #         self.update('dora_indicator', self.game.dora_indicator)
        return tile_id, action

    async def random_delay(self):
        if not self.fast and random.random() < 0.1:
            await asyncio.sleep(1 + random.random() * 3)
        return {'type': 'pass'}

    async def handle_discard(self, who, tile_id, mode, after_tsumo=True, is_riichi_tile=False):
        """
        who: 切牌者
        tile_id: 切出的牌
        mode: 是否为摸切
        after_tsumo: 是否为摸牌以后的切牌（还可能是鸣牌之后的切牌）
        is_riichi: 切出的是否为立直宣言牌
        """
        self.game.discard(who=who, tile_id=tile_id)
        connection = self.clients[who]
        self.update('furiten', self.agents[who].furiten, connection)
        self.update('machi', list(sorted(self.agents[who].machi)), connection)
        self.send_multiply({'event': 'discard', 'who': who, 'tile_id': tile_id, 'mode': mode, 'after_tsumo': after_tsumo, 'is_riichi': is_riichi_tile}, exception=who)
        agari_actions = []
        pon_kan_action = None
        chi_action = None
        jobs = []
        self.send_multiply({'event': 'wait', 'message': '等待他人响应...'})
        for i in range(1, 4):
            player_pos = (who + i) % 4
            jobs.append(self.check_discard(player_pos, who, i == 1, tile_id))
        jobs.append(self.random_delay())
        actions = await asyncio.gather(*jobs)
        for action in actions:
            if isinstance(action, dict):
                if action['type'] == 'agari':
                    agari_actions.append(action)
                elif action['type'] in ['pon', 'kan']:
                    pon_kan_action = action
                elif action['type'] == 'chi':
                    chi_action = action
        if agari_actions:
            return agari_actions
        if pon_kan_action:
            return pon_kan_action
        if chi_action:
            return chi_action
        if not self.fast:
            await asyncio.sleep(0.4)

    async def handle_tsumo_action(self, tile_id, action):
        """玩家摸牌以后的行为"""
        p = self.game.agents[self.current_player]
        while action is not None:
            if action['type'] == 'pass':
                return tile_id, action
            elif action['type'] == 'agari':
                """处理和牌"""
                return tile_id, action
            elif action['type'] == 'riichi':
                """处理立直宣言"""
                logging.info(blue(f'「{self.clients[self.current_player].username}」「立直」!'))
                p.declare_riichi = 1
                return tile_id, action
            elif action['type'] == 'ryuukyoku':
                return tile_id, action
            elif action['type'] == 'kan':
                """处理杠"""
                self.game.first_round = False  # 清除第一巡标记
                for _ in self.agents:
                    _.ippatsu_status = 0  # 清除所有玩家的一发标识

                kan_type, pattern, add = action['pattern']
                if kan_type == 0:
                    kan_tile_list = p.search_furo(4, pattern, add)
                    self.game.kan(self.current_player, kan_tile_list, from_who=self.current_player, mode=0)
                    logging.info(blue(f"「{self.clients[self.current_player].username}」暗杠「{' '.join(TENHOU_TILE_STRING_DICT[_] for _ in kan_tile_list)}」"))
                else:
                    kan_tile_list = p.search_furo(2, pattern, add)
                    agari_actions = []
                    jobs = []
                    self.send_multiply({'event': 'addkan', 'action': action})
                    for i in range(1, 4):
                        player_pos = (self.current_player + i) % 4
                        jobs.append(self.check_discard(player_pos, self.current_player, i == 1, add, add_kan=True))
                    jobs.append(self.random_delay())
                    actions = await asyncio.gather(*jobs)
                    for act in actions:
                        if act is None:
                            continue
                        if act['type'] == 'agari':
                            agari_actions.append(act)
                    if agari_actions:
                        return tile_id, agari_actions
                    self.game.kan(self.current_player, kan_tile_list, from_who=self.current_player, add=add, mode=2)
                    logging.info(blue(f"「{self.clients[self.current_player].username}」加杠「{' '.join(TENHOU_TILE_STRING_DICT[_] for _ in kan_tile_list)}」"))
                self.send_multiply({'event': 'kan', 'action': action})
                self.game.new_dora()
                self.update('dora_indicator', self.game.dora_indicator)
                tile_id, action = await self.handle_draw(who=self.current_player, where=-1)
        return tile_id, action

    def select_tile(self, client, tiles, banned=None, tsumo=None, riichi=False, is_riichi_tile=False):
        banned = banned or []
        who = self.clients.index(client)

        message = {'event': 'select_tile', 'tiles': tiles, 'banned': banned, 'tsumo': tsumo, 'riichi': riichi, 'is_riichi_tile': is_riichi_tile}
        self.send_observers(who, message)
        if client.is_human():
            self.send_personal(client, message)
            tile_id = self.fetch_discard_message(who, client, tiles, banned)
        else:
            if tiles == 'all':
                tiles = list(self.agents[who].tiles)
            tile_id = self.discard_by_ai(who, tiles, banned)
        mode = tile_id == tsumo  # 是否为摸切。如果banned为空，则tsumo为自摸的牌，否则tsumo为被鸣的牌，则必定不是摸切
        return tile_id, mode

    def send_all_game_info(self, client: ClientConnection = None):
        game_info = self.get_game_info()
        if client is None:
            for i in range(4):
                player_info = self.get_player_info(i)
                client = self.clients[i]
                if client.is_human():
                    self.send_personal(client, {'event': 'start', 'game': game_info, 'self': player_info})
                for observer in self.observe_info[i]:
                    self.send_personal(observer, {'event': 'start', 'game': game_info, 'self': player_info})
        elif client in self.clients:
            who = self.clients.index(client)
            player_info = self.get_player_info(who)
            self.send_personal(client, {'event': 'start', 'game': game_info, 'self': player_info})
        elif client.username in self.observers:
            who, client = self.observers[client.username]
            player_info = self.get_player_info(who)
            try:
                self.send_personal(client, {'event': 'start', 'game': game_info, 'self': player_info})
            except:
                pass

    async def game_loop(self):
        self.current_player = self.game.oya
        p = self.agents[self.current_player]
        connection = self.clients[self.current_player]
        tile_id, action = await self.handle_draw(who=self.current_player, where=0)
        tile_id, res = await self.handle_tsumo_action(tile_id, action)
        if res:  # 自摸和了或者加杠被人抢和
            if isinstance(res, list):
                if len(res) == 3:
                    self.send_multiply({'event': 'ryuukyoku', 'why': 'ron3', 'action': res})  # 三家和
                    return {'event': 'ryuukyoku', 'why': 'ron3', 'action': res}
                self.send_multiply({'event': 'agari', 'action': res})
                return res
            event_type = res.get('type')
            if event_type == 'agari':
                self.send_multiply({'event': 'agari', 'action': [res]})
                return [res]
            if event_type == 'ryuukyoku':
                self.send_multiply({'event': 'ryuukyoku', 'why': 'yao9', 'who': res.get('who'), 'hai': list(p.tiles)})
                return res
            if event_type != 'pass':
                self.send_multiply({'event': event_type, 'action': res})
        banned = []
        after_tsumo = True
        while 1:
            is_riichi_tile = p.declare_riichi and p.riichi_tile == -1
            """玩家选择一张牌"""
            if not p.riichi_status:  # 没立直才能选牌
                if p.declare_riichi:
                    riichi_options = check_riichi(p.hand_tile_counter, return_riichi_hai=True)
                    tile_id, mode = self.select_tile(connection, [_ for _ in p.tiles if _ // 4 in riichi_options],
                                                     tsumo=tile_id, is_riichi_tile=is_riichi_tile)
                else:
                    tile_id, mode = self.select_tile(connection, "all", banned=banned, tsumo=tile_id, is_riichi_tile=is_riichi_tile)
            else:
                tile_id, mode = self.select_tile(connection, [tile_id], tsumo=tile_id,
                                                 riichi=True, is_riichi_tile=is_riichi_tile)  # 立直时只能摸切，但还是发一个包过去并阻塞一会
            banned.clear()
            actions = await self.handle_discard(self.current_player, tile_id=tile_id, mode=mode, after_tsumo=after_tsumo, is_riichi_tile=is_riichi_tile)  # pass时, actions=None
            if not self.game_start:
                return None
            if isinstance(actions, list):  # 有人和了
                if len(actions) == 3:
                    self.send_multiply({'event': 'ryuukyoku', 'why': 'ron3', 'action': actions})  # 三家和
                    return {'event': 'ryuukyoku', 'why': 'ron3', 'action': actions}
                self.send_multiply({'event': 'agari', 'action': actions})
                return actions

            if self.game.first_round and p.menfon == 30 and 27 <= p.discard_tiles[0] // 4 <= 30:  # 第一巡四风连打判定
                if all(_.discard_tiles and _.discard_tiles[0] // 4 == p.discard_tiles[0] // 4 for _ in self.agents):
                    self.send_multiply({'event': 'ryuukyoku', 'why': 'kaze4'})
                    return {'type': 'ryuukyoku', 'why': 'kaze4'}

            if p.declare_riichi and not p.riichi_status:  # 没人和牌并且自己宣告立直的情况下，成功立个直
                self.game.riichi(self.current_player, double_riichi=self.game.first_round)
                self.send_multiply({'event': 'riichi', 'action': {'type': 'riichi', 'who': self.current_player, 'step': 2}})
                if all(_.riichi_status for _ in self.agents):
                    self.send_multiply({'event': 'ryuukyoku', 'why': 'reach4'})
                    return {'type': 'ryuukyoku', 'why': 'reach4'}
            if p.menfon == 30:
                self.game.first_round = False
            if actions is not None:  # 其他玩家的操作
                p.river.pop()
                after_tsumo = False
                p.nagashimangan = 0  # 清除被鸣牌玩家的流局满贯标识
                self.game.first_round = False  # 清除第一巡标识
                for _ in self.agents:
                    _.ippatsu_status = 0  # 清除所有玩家的一发标识
                player_id = actions['who']
                self.current_player = player_id
                p = self.agents[self.current_player]
                connection = self.clients[self.current_player]
                ptn = actions['pattern']
                if actions['type'] == 'chi':
                    chi_ptn = min(ptn) // 4
                    banned.append(tile_id // 4)
                    if tile_id // 4 == chi_ptn and chi_ptn % 9 != 7:
                        banned.append(chi_ptn + 3)
                    elif tile_id // 4 == chi_ptn + 2 and chi_ptn % 9 != 0:
                        banned.append(chi_ptn - 1)
                    self.game.chi(player_id, ptn, kui_tile=tile_id, from_who=actions['from_who'])
                    self.send_multiply({'event': actions['type'], 'action': actions})
                    logging.info(blue(f"「{self.clients[player_id].username}」吃了「{' '.join(TENHOU_TILE_STRING_DICT[_] for _ in ptn)}」"))
                elif actions['type'] == 'pon':
                    banned.append(tile_id // 4)
                    self.game.pon(player_id, ptn, kui_tile=tile_id, from_who=actions['from_who'])
                    self.send_multiply({'event': actions['type'], 'action': actions})
                    logging.info(blue(f"「{self.clients[player_id].username}」碰了「{' '.join(TENHOU_TILE_STRING_DICT[_] for _ in ptn)}」"))
                elif actions['type'] == 'kan':
                    ptn = [ptn[1] * 4 + i for i in range(4)]
                    self.game.kan(player_id, ptn, mode=1, kui_tile=tile_id, from_who=actions['from_who'])
                    self.send_multiply({'event': actions['type'], 'action': actions})
                    self.game.new_dora()
                    self.update('dora_indicator', self.game.dora_indicator)
                    logging.info(blue(f"「{self.clients[player_id].username}」杠了「{' '.join(TENHOU_TILE_STRING_DICT[_] for _ in ptn)}」"))
                    tile_id, action = await self.handle_draw(who=player_id, where=-1)
                    tile_id, res = await self.handle_tsumo_action(tile_id, action)
                    if res:  # 自摸和了或者加杠被人抢和
                        if isinstance(res, list):
                            if len(res) == 3:
                                self.send_multiply({'event': 'ryuukyoku', 'why': 'ron3', 'action': res})  # 三家和
                                return {'event': 'ryuukyoku', 'why': 'ron3', 'action': res}
                            self.send_multiply({'event': 'agari', 'action': res})
                            return res
                        event_type = res.get('type')
                        if event_type == 'agari':
                            self.send_multiply({'event': 'agari', 'action': [res]})
                            return [res]
                        if event_type != 'pass':
                            self.send_multiply({'event': event_type, 'action': res})
                    after_tsumo = True
                continue
            else:
                if p.riichi_status and p.riichi_tile == -1:  # 设置横放牌
                    p.riichi_tile = tile_id
                self.current_player = (self.current_player + 1) % 4
                p = self.agents[self.current_player]
                connection = self.clients[self.current_player]

            if sum(self.game.kang_num) == 4 and 4 not in self.game.kang_num:
                self.send_multiply({'event': 'ryuukyoku', 'why': 'kan4'})
                return {'type': 'ryuukyoku', 'why': 'kan4'}

            if self.game.left_num == 0:
                nagashimangan = [i for i in range(4) if self.agents[i].nagashimangan and all(
                    _ % 9 == 0 or _ % 9 == 8 or 27 <= _ <= 33 for _ in self.agents[i].discard_tiles)]
                machi_state = {i: [list(self.agents[i].tiles), list(self.agents[i].machi)] for i in range(4) if
                               self.agents[i].machi}
                self.send_multiply({'event': 'ryuukyoku', 'why': 'yama_end', 'nagashimangan': nagashimangan,
                                    'machi_state': machi_state})
                return {'type': 'ryuukyoku', 'why': 'yama_end', 'nagashimangan': nagashimangan,
                        'machi_state': machi_state}

            tile_id, action = await self.handle_draw(who=self.current_player, where=0)
            tile_id, res = await self.handle_tsumo_action(tile_id, action)
            if res:  # 自摸和了或者加杠被人抢和
                if isinstance(res, list):
                    if len(res) == 3:
                        self.send_multiply({'event': 'ryuukyoku', 'why': 'ron3', 'action': res})  # 三家和
                        return {'event': 'ryuukyoku', 'why': 'ron3', 'action': res}
                    self.send_multiply({'event': 'agari', 'action': res})
                    return res
                event_type = res.get('type')
                if event_type == 'agari':
                    self.send_multiply({'event': 'agari', 'action': [res]})
                    return [res]
                if event_type == 'ryuukyoku':
                    self.send_multiply({'event': 'ryuukyoku', 'why': 'yao9', 'who': res.get('who'), 'hai': list(p.tiles)})
                    return res
                if event_type != 'pass':
                    self.send_multiply({'event': event_type, 'action': res})
            p.ippatsu_status = 0  # 摸了牌没和，清除一发
            after_tsumo = True


class Server:
    def __init__(self, host, port, AI_count, min_score, fast, allow_observe, train=False):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        self.ROOM_ID_LOCK = 0
        signal.signal(signal.SIGINT, self.close_server)
        signal.signal(signal.SIGTERM, self.close_server)
        self.AI_count = AI_count
        train = train and AI_count == 4 and os.path.isfile('model/saved/reward-model/best.pt')  # 四个AI的情况下方可开启训练模式
        self.train = train
        self.game = GameEnvironment(has_aka=True, AI_count=AI_count, min_score=min_score, fast=fast, allow_observe=allow_observe, train=train)
        logging.info(red(f"Server running at {host}:{port} with {self.AI_count} AI..."))

    def close_server(self, signum, frame):
        self.server_socket.close()
        logging.info(red("Server shutdown"))
        exit(0)

    def recv_socket(self, client_socket):
        buffer = []
        while True:
            data = client_socket.recv(1)
            if len(data) == 0:
                break
            if data == b'\n':
                break
            buffer.append(data)
        return b''.join(buffer).decode('utf-8')

    def handle_client(self, client: ClientConnection):
        while 1:
            try:
                data = self.recv_socket(client.client_socket)
                if len(data) == 0:
                    break
                data = json.loads(data)
                logging.debug(yellow(f"Recv: {data}"))
                event = data.get('event')
                if event in ['quit', 'discard', 'decision']:
                    client.message_queue.put(data)
                if event == 'quit':
                    break
                if event == 'change_ob':
                    if client.username not in self.game.observers:
                        continue
                    username = data.get('username')
                    if username not in self.game.clients:
                        continue
                    target = self.game.clients.index(username)
                    who, _ = self.game.observers[client.username]
                    self.game.observers[client.username] = (target, client)
                    self.game.observe_info[who].remove(client)
                    self.game.observe_info[target].append(client)
                    self.game.send_all_game_info(client)
            except Exception as e:
                client.message_queue.put({'event': 'quit'})
                tb = traceback.format_exc()
                logging.debug(red(f"An exception occurred: {e}"))
                logging.debug(red(f"Traceback info:\n{tb}"))
                break
        self.game.player_disconnect(client)

    @run_sync
    def recv_continue_message(self, client: ClientConnection):
        message = client.fetch_message()
        if message['event'] == 'ready':
            logging.info(f"{client.username} is ready")

    async def game_main_loop(self):
        self.game.game_start = True
        random.shuffle(self.game.clients)
        while self.game.game_start:
            self.game.start()
            self.game.send_all_game_info()
            wind = ['東', '南', '西', '北'][self.game.round // 4]
            wind_round = self.game.round % 4 + 1
            logging.info(green(f'{wind}{wind_round}局 - {self.game.honba}本场------场供: {self.game.riichi_ba * 1000}'))
            res = await self.game.game_loop()
            if res is None:
                logging.debug(yellow("游戏中断..."))
                break
            if self.train:
                scores = [p.score for p in self.game.agents]
            game_over, score_delta = self.game.game_update(res)
            if self.train:
                for i in range(4):
                    self.game.reward_features[i].append(torch.from_numpy(self.game.game.get_game_feature(score_delta[i], scores[i])))
                    for item in self.game.collected_data[i]:
                        if len(item) == 3:
                            continue
                        features = torch.stack(self.game.reward_features[i])[None].float()
                        reward = self.game.reward(features, len(self.game.reward_features[i]) - 1)
                        item.append(reward)
            if not self.game.fast:
                await asyncio.sleep(2)
            self.game.send_multiply({'event': 'settlement', 'res': res, 'score': score_delta, 'ura_dora': self.game.game.ura_dora_indicator})
            wait_jobs = []
            for client in self.game.clients:
                if client.is_human():
                    wait_jobs.append(self.recv_continue_message(client))
            if not self.game.fast and all([not _.is_human() for _ in self.game.clients]):
                wait_jobs.append(asyncio.sleep(15))
            await asyncio.gather(*wait_jobs)
            logging.info(green("Continue..."))
            if game_over:
                logging.info(green('游戏结束！'))
                for i, score in self.game.game.get_rank():
                    logging.info(green(f"「{self.game.clients[i].username}」积分「{score * 100}」"))
                self.game.game_start = False
                if not self.game.fast:
                    await asyncio.sleep(0.1)
                self.game.send_player_score()
                wait_jobs = []
                for client in self.game.clients:
                    if client.is_human():
                        wait_jobs.append(self.recv_continue_message(client))
                if not self.game.fast and all([not _.is_human() for _ in self.game.clients]):
                    wait_jobs.append(asyncio.sleep(10))
                await asyncio.gather(*wait_jobs)
                self.game.send_multiply({'event': 'end', 'message': '游戏结束！请重新加入房间～'})
                if not self.game.fast:
                    await asyncio.sleep(0.1)
                for conn in self.game.clients:
                    conn.close()
                self.game.reset()
                break

    def game_thread(self):
        try:
            asyncio.run(self.game_main_loop())
        except Exception as e:
            tb = traceback.format_exc()
            logging.debug(red(f"An exception occurred: {e}"))
            logging.debug(red(f"Traceback info:\n{tb}"))
            pass

    def handle_connection(self):
        while 1:
            try:
                client_socket, addr = self.server_socket.accept()
                message = json.loads(self.recv_socket(client_socket))
                username = message.get('username')
                observe = message.get('observe')
                success, client = self.game.player_join(client_socket, username, observe)
                if success:
                    threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
            except:
                continue

    async def run(self):
        threading.Thread(target=self.handle_connection, daemon=True).start()
        while True:
            try:
                if len(self.game.clients) == 4 and not self.game.game_start:
                    thread = threading.Thread(target=self.game_thread, daemon=True)
                    thread.start()
                    thread.join()
                await asyncio.sleep(0.1)
            except Exception as e:
                tb = traceback.format_exc()
                logging.debug(red(f"An exception occurred: {e}"))
                logging.debug(red(f"Traceback info:\n{tb}"))


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('--host', '-H', default='0.0.0.0', type=str)
    args.add_argument('--port', '-P', default=9999, type=int)
    args.add_argument('--AI', '-A', default=0, type=int)
    args.add_argument('--allow_observe', '-ob', action='store_true', help='Allow observe')
    args.add_argument('--min_score', '-m', default=0, type=int)
    args.add_argument('--debug', '-d', action='store_true', help='Print more details')
    args.add_argument('--fast', '-f', action='store_true', help='Cancel AI thinking time')
    args.add_argument('--train', '-t', action='store_true', help='Collect playing data')
    args = args.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    server = Server(args.host, args.port, args.AI, args.min_score, args.fast, args.allow_observe, args.train)
    asyncio.run(server.run())
