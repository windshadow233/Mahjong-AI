import socket
import json
import time
import sys
import traceback
import argparse
import os
import ast

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from mahjong.display import *
from mahjong.yaku import Yaku


class Mahjong(object):

    def __init__(self):
        super(Mahjong, self).__init__()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None

        self.seat = self.wind = None

        self.machi = None
        self.furiten = False

        self.oya = None
        self.game_round = None
        self.honba = None
        self.riichi_ba = None
        self.dora_indicator = None
        self.agents = None
        self.left_num = None

        self.tiles = None
        self.furo = None
        self.game_start = False  # 一轮游戏是否开始
        self.end = False  # 整局游戏终

        self.observe = False

        self.latest_player = None
        self.latest_discard_mode = None
        self.latest_discard_tile = None
        self.latest_event = None

    def set_game_info(self, game_info):
        self.latest_event = self.latest_player = self.latest_discard_mode = self.latest_discard_tile = None
        self.furiten = False
        self.game_round = game_info['round']
        self.honba = game_info['honba']
        self.riichi_ba = game_info['riichi_ba']
        self.dora_indicator = game_info['dora_indicator']
        self.oya = self.game_round % 4
        self.agents = game_info['agents']
        self.left_num = game_info['left_num']

    def set_self_info(self, self_info):
        if self_info:
            self.username = self_info['username']
            self.seat = self_info['seat']
            self.tiles = list(sorted(self_info['tiles']))
            self.furo = self_info['furo']
            self.machi = self_info['machi']
            self.wind = ['東家', '南家', '西家', '北家'][self.seat - self.oya]

    def get_user_string(self, who):
        player_wind = ['東家', '南家', '西家', '北家'][who - self.oya]
        username = self.agents[who]['username']
        return f'{username}「{player_wind}」'

    def print_game_info(self):
        os.system('clear')
        wind = ['東', '南', '西', '北'][self.game_round // 4]
        wind_round = self.game_round % 4 + 1
        left_num = self.left_num
        if self.observe:
            observe_msg = '(正在观战) '
        else:
            observe_msg = ''
        print(green(f'{observe_msg}{wind}{wind_round}局 - {self.honba}本场------场供: {self.riichi_ba * 1000}'))
        print(yellow('宝牌指示牌:'))
        print(ascii_style_print([self.dora_indicator], with_color='yellow'))
        print("")
        for i in range(4):
            p = self.agents[i]
            player_wind = ['東家', '南家', '西家', '北家'][i - self.oya]
            u = p['username']
            s = p['score']
            player_info = light_grey(f"「{player_wind}」{u} ({s * 100})")
            if p['riichi']:
                player_info += red(' (立直)')
            discard_info = [
                cyan(pad_string(TENHOU_TILE_STRING_DICT[_], 6)) if i < p['riichi_round'] else
                green(pad_string(TENHOU_TILE_STRING_DICT[_], 6))
                for i, _ in enumerate(p['discard'], 1)
            ]
            if len(discard_info) <= 18:
                discard_info = [discard_info]
            else:
                discard_info = [discard_info[:18], discard_info[18:]]
            for i, info in enumerate(discard_info):
                discard_info[i] = ' '.join(info)
                if i > 0:
                    discard_info[i] = ' ' * 6 + discard_info[i]
            discard_info = '\n'.join(discard_info)
            print(player_info)
            print(magenta(f"牌河: ") + discard_info)
            if p['furo']:
                furo_str = "副露: "
                for furo_key, tiles in p['furo'].items():
                    furo_type, _ = ast.literal_eval(furo_key)
                    if furo_type == 2:
                        furo_str += f'「🀫 {TENHOU_TILE_STRING_DICT[tiles[0]]} {TENHOU_TILE_STRING_DICT[tiles[1]]} 🀫 」'
                    else:
                        furo_str += '「' + ' '.join([TENHOU_TILE_STRING_DICT[_] for _ in tiles]) + '」'
                    furo_str += ' '
                print(green(furo_str[:-1]))
                # print(green(f"副露: {' '.join(['「' + ' '.join([TENHOU_TILE_STRING_DICT[_] for _ in furo]) + '」' for furo in p['furo'].values()])}"))
            print(blue('-' * 150))
        print(red(f"余牌: {left_num}"))
        if self.latest_player is not None:
            mode = ['手切', '摸切'][self.latest_discard_mode]
            print(magenta(f'{self.get_user_string(self.latest_player)}{mode}: \n{ascii_style_print([[self.latest_discard_tile]])}'))
        if self.latest_event:
            print(yellow(self.latest_event))

    def print_self_info(self):
        print(yellow('-' * 150))
        print(light_grey(f'{self.username}「{self.wind}」({self.agents[self.seat]["score"] * 100})'))
        length = len(self.tiles)
        numbers = list(map(str, range(1, length + 1)))
        print(yellow('　'.join(_.ljust(9, ' ') for _ in numbers)))
        print(ascii_style_print([self.tiles]))
        if self.furo:
            print(ascii_style_print(self.furo.values()))
        if self.machi:
            machi_msg = yellow(f"听牌: {'、'.join(TILE_STRING_DICT[_] for _ in self.machi)}")
            if self.furiten:
                print(red('\n(振听) ' + machi_msg))
            else:
                print('\n' + machi_msg)

    def make_decision(self, message):
        actions = message['actions']
        msg = '\n可进行以下操作:'
        for i, action in enumerate(actions):
            if action['type'] == 'pass':
                msg += f'\n{i}、Pass'
            elif action['type'] == 'ryuukyoku':
                msg += f'\n{i}、流局（九种九牌）'
            elif action['type'] == 'agari':
                msg += f'\n{i}、和！'
            elif action['type'] == 'chi':
                furo = action['pattern']
                msg += f'\n{i}、吃！「{" ".join(TENHOU_TILE_STRING_DICT[_] for _ in furo)}」'
            if action['type'] == 'pon':
                furo = action['pattern']
                msg += f'\n{i}、碰！「{" ".join(TENHOU_TILE_STRING_DICT[_] for _ in furo)}」'
            elif action['type'] == 'kan':
                kan_pattern = action['pattern']
                kan_type, pattern, add = kan_pattern
                if kan_type == 0:
                    msg += f'\n{i}、暗杠！「{TILE_STRING_DICT[pattern]}」'
                elif kan_type == 1:
                    msg += f'\n{i}、明杠！「{TILE_STRING_DICT[pattern]}」'
                else:
                    msg += f'\n{i}、加杠！「{TILE_STRING_DICT[pattern]}」'
            elif action['type'] == 'riichi':
                msg += f'\n{i}、立直！'
        if not self.observe:
            msg += '\n请选择: '
        decision = yellow(msg)
        if not self.observe:
            while 1:
                ans = input(decision)
                if ans.isdigit() and 0 <= int(ans) < len(actions):
                    action = actions[int(ans)]
                    self.send({'event': 'decision', 'action': action})
                    break
                print(red("输入有误！"))
        else:
            print(decision)

    def discard_tile(self, message):
        tiles = message['tiles']
        riichi = message['riichi']
        tsumo = message['tsumo']
        if tiles == 'all':
            tiles = self.tiles
        elif len(tiles) > 1:
            tiles = list(sorted(tiles))
        if not self.observe:
            if not riichi:
                banned = message['banned']
                while 1:
                    if message['tiles'] != 'all':
                        length = len(tiles)
                        numbers = list(map(str, range(1, length + 1)))
                        print(yellow('　'.join(_.ljust(9, ' ') for _ in numbers)))
                        print(ascii_style_print([tiles]))
                    ans = input(red("\n选择一张牌打出(输入对应的数字): "))
                    if ans.isdigit() and 1 <= int(ans) <= len(tiles):
                        tile = tiles[int(ans) - 1]
                        if tile // 4 in banned:
                            print(red("禁止现物、筋食替！"))
                            continue
                        break
                    print(red("输入有误！"))
            else:
                time.sleep(1.5)  # 立直时摸切阻塞1.5秒
                tile = tiles[0]
            self.tiles.remove(tile)
            self.tiles.sort()
            self.latest_player = self.seat
            self.latest_discard_mode = tsumo == tile
            self.latest_discard_tile = tile
            self.agents[self.seat]['discard'].append(tile)
            self.send({'event': 'discard', 'who': self.seat, 'tile_id': tile})

    def handle_connection(self):
        while 1:
            try:
                message = self.recv()
                event = message.get('event')
                if event == 'start':
                    self.end = False
                    self.set_game_info(message['game'])
                    self.set_self_info(message['self'])
                    self.game_start = True
                if event == 'update':
                    key = message['key']
                    value = message['value']
                    self.__setattr__(key, value)
                elif event not in ['draw', 'select_tile', 'decision']:
                    self.latest_event = None
                if event == 'score':
                    value = message['score']
                    for who, score in value:
                        self.agents[who]['score'] = score
                if event == 'discard':
                    who = message['who']
                    tile_id = message['tile_id']
                    self.agents[who]['discard'].append(tile_id)
                    self.latest_player = who
                    self.latest_discard_mode = message['mode']
                    self.latest_discard_tile = tile_id
                    if who == self.seat and self.observe:
                        self.tiles.remove(tile_id)
                        self.tiles.sort()
                elif event == 'riichi':
                    who = message['action']['who']
                    self.latest_event = f"{self.get_user_string(who)}宣告立直！"
                    p = self.agents[who]
                    if message['action'].get('status') == 2:
                        p['score'] -= 10
                        self.riichi_ba += 1
                    else:
                        p['riichi'] = 1
                        p['riichi_round'] = len(p['discard']) + 1
                elif event == 'addkan':
                    action = message['action']
                    who = action['who']
                    pattern = action['pattern']
                    self.latest_event = f"{self.get_user_string(who)}声明加杠「{TILE_STRING_DICT[pattern[1]]}」"
                elif event in ['chi', 'pon', 'kan']:
                    action = message['action']
                    who = action['who']
                    p = self.agents[who]
                    pattern = action['pattern']
                    if event == 'chi':
                        self.latest_event = f"{self.get_user_string(who)}吃了「{' '.join(TENHOU_TILE_STRING_DICT[_] for _ in pattern)}」"
                        key = str((0, (min(pattern) // 4, len(p['furo']))))
                    elif event == 'pon':
                        self.latest_event = f"{self.get_user_string(who)}碰了「{' '.join(TENHOU_TILE_STRING_DICT[_] for _ in pattern)}」"
                        self.agents[who]['furo'][str((1, min(pattern) // 4))] = pattern
                        key = str((1, pattern[0] // 4))
                    else:
                        kan_type, pattern, add = pattern
                        if kan_type == 0:
                            self.latest_event = f'{self.get_user_string(who)}暗杠了「{TILE_STRING_DICT[pattern]}」'
                            key = str((2, pattern))
                        elif kan_type == 1:
                            self.latest_event = f'{self.get_user_string(who)}明杠了「{TILE_STRING_DICT[pattern]}」'
                            self.agents[who]['furo'][str((3, pattern))] = [4 * pattern + i for i in range(4)]
                            key = str((3, pattern))
                        else:
                            self.latest_event = f'{self.get_user_string(who)}加杠了「{TILE_STRING_DICT[pattern]}」'
                            p['furo'].pop(str((1, pattern)))
                            if who == self.seat:
                                self.furo.pop(str((1, pattern)))
                            key = str((3, pattern))
                        pattern = [4 * pattern + i for i in range(4)]
                    p['furo'][key] = pattern
                    if who == self.seat:
                        self.furo[key] = pattern
                        self.tiles = list(sorted(set(self.tiles).difference(pattern)))
                elif event == 'agari':
                    self.end = True
                    actions = message['action']
                    ura_dora = message['ura_dora_indicator']
                    self.latest_event = f"里宝牌指示牌:\n{ascii_style_print([ura_dora], with_color=None)}\n\n"
                    for action in actions:
                        who = action['who']
                        machi = action['machi']
                        from_who = action['from_who']
                        ret = action['yaku']
                        han = action['han']
                        fu = action['fu']
                        score = action['score']
                        hai = action['hai']
                        hai.remove(machi)
                        furo = action['furo']
                        yaku_list = action['yaku_list']
                        if who == from_who:
                            self.latest_event += f"{self.get_user_string(who)}({self.agents[who]['username']}) 自摸！"
                        else:
                            self.latest_event += f"{self.get_user_string(from_who)}({self.agents[from_who]['username']}) 放铳！{self.get_user_string(who)}({self.agents[who]['username']}) 荣和！"
                        self.latest_event += '\n' + ascii_style_print([hai, [machi]], with_color=None)
                        if furo:
                            self.latest_event += '\n' + ascii_style_print(furo, with_color=None)
                        self.latest_event += f"\n\n役种: {'、'.join(yaku_list)} |------> "
                        if isinstance(ret, list):
                            if han > 1:
                                self.latest_event += f'{han}倍役满'
                            else:
                                self.latest_event += '役满'
                        else:
                            self.latest_event += f'{han}番'
                        self.latest_event += f'({fu}符) |------> 基本点: {score}\n\n'
                elif event == 'ryuukyoku':
                    self.end = True
                    self.latest_event = '流局: '
                    why = message['why']
                    if why == 'yama_end':
                        machi_state = message['machi_state']
                        nagashimangan = message['nagashimangan']
                        self.latest_event += '荒牌流局...'
                        for machi_player, (hand_tiles, machi_tiles) in machi_state.items():
                            self.latest_event += '\n' + '-' * 150
                            hand_tiles.sort()
                            machi_player = int(machi_player)
                            self.latest_event += f"\n{self.get_user_string(machi_player)}({self.agents[machi_player]['username']}) 听牌: {'、'.join(TILE_STRING_DICT[_] for _ in sorted(machi_tiles))}"
                            self.latest_event += f"\n{ascii_style_print([hand_tiles], with_color=None)}"
                            if self.agents[machi_player]['furo']:
                                self.latest_event += f"\n{ascii_style_print(self.agents[machi_player]['furo'].values(), with_color=None)}"
                        for nagashi_player in nagashimangan:
                            self.latest_event += f"\n{self.get_user_string(nagashi_player)} 流局满贯！"
                    elif why == 'kan4':
                        self.latest_event += '四杠散了...'
                    elif why == 'reach4':
                        self.latest_event += '四家立直...'
                    elif why == 'kaze4':
                        self.latest_event += '四风连打...'
                    elif why == 'yao9':
                        who = message['who']
                        self.latest_event += f"{self.get_user_string(who)} 九种九牌..."
                        self.latest_event += f"\n{ascii_style_print([sorted(message['hai'])], with_color=None)}"
                    elif why == 'ron3':
                        action = message['action']
                        for act in action:
                            who = act['who']
                            self.latest_event += f"{self.get_user_string(who)}\n"
                        self.latest_event += '三家和了!'
                if self.game_start:
                    self.print_game_info()
                if 'message' in message:
                    print(red(message['message']))
                if event == 'draw':
                    tile_id = message.get('tile_id')
                    if tile_id is not None:
                        self.tiles.append(tile_id)
                if self.game_start:
                    self.print_self_info()
                if event == 'end':
                    break
                if event == 'decision':
                    self.make_decision(message)
                elif event == 'select_tile':
                    self.discard_tile(message)
                if self.end:
                    if not self.observe:
                        input(red('请按回车继续...'))
                        self.send({'event': 'ready'})
                        print(green('等待他人确认中...'))
                    else:
                        print(red('等待玩家确认中...'))
                    self.end = False
            except KeyboardInterrupt:
                self.send({'event': 'quit'})
                break
            except Exception as e:
                self.send({'event': 'quit'})
                tb = traceback.format_exc()
                print(f"An exception occurred: {e}")
                print(f"Traceback info:\n{tb}")
                break
        print("已断开与服务器的连接")

    def send(self, message):
        self.client_socket.send(json.dumps(message).encode('utf-8') + b'\n')

    def recv(self):
        buffer = []
        while True:
            data = self.client_socket.recv(1)
            if len(data) == 0:
                break
            if data == b'\n':
                break
            buffer.append(data)
        return json.loads(b''.join(buffer).decode('utf-8'))

    def connect(self, host, port, username, observe):
        try:
            self.client_socket.connect((host, port))
            self.send({'username': username, 'observe': observe})
            response = self.recv()
            if response['status'] != 0:
                if response['status'] == -1:
                    self.observe = True
                print(green(response['message']))
                self.handle_connection()
            else:
                print(red(response['message']))
            self.client_socket.close()
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as e:
            tb = traceback.format_exc()
            print(f"An exception occurred: {e}")
            print(f"Traceback info:\n{tb}")


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('--host', '-H', default='localhost', type=str)
    args.add_argument('--port', '-P', default=9999, type=int)
    args.add_argument('--username', '-U', default='', type=str)
    args.add_argument('--observe', '-ob', action='store_true', help='Observe mode')
    args = args.parse_args()
    app = Mahjong()
    app.connect(args.host, args.port, args.username, args.observe)
