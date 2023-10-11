from typing import List
from collections import Counter

import numpy as np

from .check_agari import is_agari, parse_agari_info


class YakuList:
    SUKANTSU = 1
    SUANKO = 2
    CHINROTO = 3
    DAISANGEN = 4
    DAISUSHI = 5
    SYOSUSHI = 6
    TSUISO = 7
    RYUISO = 8
    CHURENPOTO = 9
    KOKUSHIMUSO = 10
    SUANKOTANKI = 11
    KOKUSHIJUSANMEN = 12
    CHURENCHUMEN = 13
    TENHOU = 14
    CHIHOU = 15

    TSUMO = 1 << 4
    PINFU = 1 << 5
    HONROTO = 1 << 6
    CHINITSU = 1 << 7
    HONITSU = 1 << 8
    JUNCHANTA = 1 << 9
    HONCHANTA = 1 << 10
    SANANKO = 1 << 11
    SANKANTSU = 1 << 12
    SANSYOKUDOKO = 1 << 13
    SANSYOKUDOJUN = 1 << 14
    IKKITSUKAN = 1 << 15
    TOITOI = 1 << 16
    RYANPEKO = 1 << 17
    IPEKO = 1 << 18
    CHITOITSU = 1 << 19
    TANYAO = 1 << 20
    SYOSANGEN = 1 << 21

    SANGENHAI_SHIFT = 22
    SANGENHAI_MASK = 12582912  # (1 << 22) + (1 << 23)
    BAKAZEHAI = 1 << 24
    MENFONHAI = 1 << 25
    DORA_SHIFT = 26
    DORA_MASK = 2080374784  # (1 << 26) + (1 << 27)+ (1 << 28) + (1 << 29) + (1 << 30)
    URA_DORA_SHIFT = 31
    URA_DORA_MASK = 66571993088  # (1 << 31) + (1 << 32)+ (1 << 33) + (1 << 34) + (1 << 35)
    AKA_DORA_SHIFT = 36
    AKA_DORA_MASK = 206158430208  # (1 << 36) + (1 << 37)

    RIICHI = 1 << 38
    DOUBLE_RIICHI = 1 << 39
    ROB_KAN = 1 << 40
    RINSHAN = 1 << 41
    HAITEI = 1 << 42
    IPPATSU = 1 << 43


class Yaku(object):

    def __init__(self, hand_tiles, furo, agarihai, dora, ura_dora, bahai, menfon, tsumo, riichi, ippatsu, tokusyu=0, aka=True):
        """
        tokusyu: 1=岭上开花、2=抢杠、3=海底
        """
        self.hand_tiles = list(hand_tiles)
        self.hand_tiles.sort()
        self.counter = Counter([_ // 4 for _ in self.hand_tiles])
        self.agari = is_agari(self.counter)
        self.furo = furo
        self.agarihai = agarihai // 4
        self.riichi = riichi
        self.bahai = bahai
        self.menfon = menfon
        self.tsumo = tsumo
        self.dora = dora
        self.ura_dora = ura_dora
        self.has_aka = aka
        self.dora_count = 0
        self.ura_dora_count = 0
        self.aka_count = 0
        if not self.agari:
            return

        self.pon = []
        self.chi = []
        self.ankan = []
        self.minkan = []
        for furo_type, ptn in self.furo.keys():
            if furo_type == 0:
                self.chi.append(ptn[0])
            elif furo_type == 1:
                self.pon.append(ptn)
            elif furo_type == 2:
                self.ankan.append(ptn)
            elif furo_type == 3:
                self.minkan.append(ptn)
        self.kui = 1 if len(self.pon + self.chi + self.minkan) > 0 else 0
        self.ippatsu = ippatsu
        self.tokusyu = tokusyu

    def count_dora(self):
        total_tiles = self.hand_tiles + [_ for tiles in self.furo.values() for _ in tiles]
        total_counter = Counter([_ // 4 for _ in total_tiles])
        for d in self.dora:
            self.dora_count += total_counter[d]
        if self.riichi:
            for d in self.ura_dora:
                self.ura_dora_count += total_counter[d]
        if self.has_aka:
            self.aka_count = sum(map(lambda x: x in [16, 52, 88], total_tiles))

    def naive_check_yaku(self):
        if not self.agari:
            return False
        if self.riichi or (self.tsumo and not self.kui) or self.tokusyu:
            return True
        if isinstance(self.agari, str):
            x_s = list(map(lambda _: int(_, 16), self.agari.split(',')))
            for x in x_s:
                if x & 2080374784:
                    return True
            return False
        return True

    def calculate_yaku(self):
        if isinstance(self.agari, str):
            x = list(map(lambda _: int(_, 16), self.agari.split(',')))
            han, fu, score, ret = self.yaku(x)
        elif self.agari:
            if self.counter[self.agarihai] == 2:
                ret = [YakuList.KOKUSHIJUSANMEN]
                han = 2
            else:
                ret = [YakuList.KOKUSHIMUSO]
                han = 1
        else:
            return
        if han == 0:
            return
        return self.parse_yaku_ret(ret, self.tsumo)

    def yaku(self, xs: List[int]):
        self.count_dora()
        tiles_pos = [_[0] for _ in self.counter.items()]
        yakuman = []
        han_list = np.zeros(shape=(len(xs)), dtype=int)
        fu_list = np.zeros(shape=len(xs), dtype=int)
        ret_list = np.zeros(shape=len(xs), dtype=int)
        han_yakuman = 0
        num_pon = len(self.pon)
        num_ankan = len(self.ankan)
        num_minkan = len(self.minkan)
        num_chi = len(self.chi)
        futei = 20  # 符底
        if self.tsumo:
            futei += 2
        elif self.kui == 0:
            futei += 10
        for k, x in enumerate(xs):  # 遍历每一种和牌方式
            han = 0
            ret = 0
            fu = futei
            num_pon = len(self.pon)
            info = parse_agari_info(x)
            mentsu = []
            num_anko = info['num_kotsu']
            num_shuntsu = info['num_shuntsu']
            atama = info['atama']
            mentsu.append(tiles_pos[atama])

            num_kotsu = num_anko + num_pon + num_ankan + num_minkan

            for i in range(num_anko):  # 先把刻子放进去
                mentsu.append(tiles_pos[info[f'm{i + 1}']])

            mentsu.extend(self.pon)
            mentsu.extend(self.ankan)
            mentsu.extend(self.minkan)

            for i in range(num_shuntsu):  # 最后放顺子
                mentsu.append(tiles_pos[info[f'm{num_anko + i + 1}']])

            mentsu.extend(self.chi)
            machi = 0
            ron_pos = 0
            if mentsu[0] == self.agarihai:  # 单骑听牌
                machi |= 0x10
            for m in range(num_anko):
                if mentsu[m + 1] == self.agarihai:  # 双碰听牌
                    machi |= 0x2
                    ron_pos = m + 1
                    break
            for m in range(num_shuntsu):
                shuntsu_ptn = mentsu[4 - m]
                if shuntsu_ptn == self.agarihai:
                    if self.agarihai % 9 != 6:  # 两面听牌
                        machi |= 0x1
                    else:
                        machi |= 0x8  # 边张听牌
                elif shuntsu_ptn + 2 == self.agarihai:
                    if self.agarihai % 9 != 2:
                        machi |= 0x1
                    else:
                        machi |= 0x8
                elif shuntsu_ptn + 1 == self.agarihai:
                    machi |= 0x4  # 嵌张听牌
            if machi >= 4:
                fu += 2
            if not self.tsumo and machi == 2:  # 双碰听牌和来的刻子应算作明刻
                mentsu[ron_pos], mentsu[num_anko] = mentsu[num_anko], mentsu[ron_pos]
                num_anko -= 1
                num_pon += 1
            roto = 0  # 老头牌刻子、雀头
            ji = 0  # 字牌刻子、雀头
            sangen = 0  # 三元牌刻子
            for i in range(num_kotsu + 1):
                ptn = mentsu[i]
                if ptn >= 27:
                    ji += 1
                    if i > 0 and 31 <= ptn <= 33:
                        sangen += 1
                elif ptn % 9 == 0 or ptn % 9 == 8:
                    roto += 1
            if mentsu[0] >= 31:  # 三元牌雀头
                fu += 2
            elif mentsu[0] == self.bahai:  # 场风雀头
                fu += 2
            if mentsu[0] == self.menfon:  # 门风雀头
                fu += 2
            for i in range(num_anko):
                ptn = mentsu[i + 1]
                if ptn >= 27 or ptn % 9 == 0 or ptn % 9 == 8:
                    fu += 8
                else:
                    fu += 4
            for i in range(num_anko, num_anko + num_pon):
                ptn = mentsu[i + 1]
                if ptn >= 27 or ptn % 9 == 0 or ptn % 9 == 8:
                    fu += 4
                else:
                    fu += 2
            for i in range(num_anko + num_pon, num_anko + num_pon + num_ankan):
                ptn = mentsu[i + 1]
                if ptn >= 27 or ptn % 9 == 0 or ptn % 9 == 8:
                    fu += 32
                else:
                    fu += 16
            for i in range(num_anko + num_pon + num_ankan, num_kotsu):
                ptn = mentsu[i + 1]
                if ptn >= 27 or ptn % 9 == 0 or ptn % 9 == 8:
                    fu += 16
                else:
                    fu += 8
            if num_kotsu >= 2:
                if num_kotsu == 4:  # 4刻子的情况
                    if num_ankan + num_minkan == 4:
                        yakuman.append(YakuList.SUKANTSU)  # 四杠子
                        han_yakuman += 1
                    if num_anko + num_ankan == 4:
                        if machi & 0x10:
                            yakuman.append(YakuList.SUANKOTANKI)  # 四暗刻单骑
                            han_yakuman += 2
                        else:
                            yakuman.append(YakuList.SUANKO)  # 四暗刻
                            han_yakuman += 1
                    if ji == 5:
                        yakuman.append(YakuList.TSUISO)  # 字一色
                        han_yakuman += 1
                    elif roto == 5:
                        yakuman.append(YakuList.CHINROTO)  # 清老头
                        han_yakuman += 1
                    ret |= YakuList.TOITOI
                    han += 2
                    if roto + ji == 5:
                        ret |= YakuList.HONROTO  # 混老头
                        han += 2
                if num_kotsu >= 3:
                    if ji >= 4:
                        fonhai = 0
                        for i in range(num_kotsu):
                            fonhai += 1 if 27 <= mentsu[i + 1] <= 30 else 0
                        if fonhai == 4:  # 大四喜
                            yakuman.append(YakuList.DAISUSHI)
                            han_yakuman += 2
                        elif fonhai == 3 and 27 <= mentsu[0] <= 30:  # 小四喜
                            yakuman.append(YakuList.SYOSUSHI)
                            han_yakuman += 1
                    if num_anko + num_ankan == 3:  # 三暗刻
                        ret |= YakuList.SANANKO
                        han += 2
                    if num_ankan + num_minkan == 3:  # 三杠子
                        ret |= YakuList.SANKANTSU
                        han += 2
                    pre = []
                    num_doko = 0  # 三色同刻
                    for i in range(num_kotsu):
                        ptn = mentsu[i + 1]
                        if ptn < 27:
                            for c in pre:
                                if c == ptn % 9:
                                    num_doko += 1
                            pre.append(ptn % 9)
                    if num_doko >= 3:
                        ret |= YakuList.SANSYOKUDOKO
                        han += 2
                if sangen == 3:
                    yakuman.append(YakuList.DAISANGEN)
                    han_yakuman += 1
                elif sangen == 2 and 31 <= mentsu[0] <= 33:
                    ret |= YakuList.SYOSANGEN
                    han += 2
            if num_shuntsu + num_chi >= 2:
                if num_shuntsu == 4:
                    if mentsu[0] < 31 and mentsu[0] != self.bahai and mentsu[0] != self.menfon and machi & 0x1:  # 平和
                        ret |= YakuList.PINFU
                        han += 1
                        fu = 20 if self.tsumo else 30
                    if info['ryanpeikou']:
                        ret |= YakuList.RYANPEKO
                        han += 3
                elif num_shuntsu + num_chi == 4:
                    if fu == 20:  # 副露平和形状的荣和补到30符
                        fu = 30
                if num_shuntsu + num_chi >= 3:
                    if info['ikki'] != 0:
                        ret |= YakuList.IKKITSUKAN
                        han += 2 - self.kui
                    else:
                        ikki = 0
                        for i in range(num_shuntsu + num_chi):
                            ptn = mentsu[4 - i]
                            if ptn % 3 == 0:
                                ikki |= 1 << ptn // 3
                        if ikki & 0x7 == 7 or ikki & 0x38 == 0x38 or ikki & 0x1c0 == 0x1c0:
                            ret |= YakuList.IKKITSUKAN
                            han += 2 - self.kui
                        else:
                            pre = []
                            num_dojun = 0  # 三色同顺
                            for i in range(num_shuntsu + num_chi):
                                ptn = mentsu[4 - i]
                                if ptn < 27:
                                    for c in pre:
                                        if c % 9 == ptn % 9 and c != ptn:
                                            num_dojun += 1
                                    pre.append(ptn)
                            if num_dojun >= 3:
                                ret |= YakuList.SANSYOKUDOJUN
                                han += 2 - self.kui
                if info['cyuren']:
                    if self.counter[self.agarihai] == 4 or self.counter[self.agarihai] == 2:
                        yakuman.append(YakuList.CHURENCHUMEN)  # 九莲九面听
                        han_yakuman += 2
                    else:
                        yakuman.append(YakuList.CHURENPOTO)  # 九莲宝灯
                        han_yakuman += 1
                if info['ippeikou']:  # 一杯口
                    ret |= YakuList.IPEKO
                    han += 1
            man = pin = sou = 0
            if not info['chitoi']:
                for i in range(num_shuntsu + num_chi):
                    if mentsu[4 - i] % 9 == 0 or mentsu[4 - i] % 9 == 6:
                        roto += 1
                for ptn in mentsu:
                    if 0 <= ptn <= 8:
                        man += 1
                    elif 9 <= ptn <= 17:
                        pin += 1
                    elif 18 <= ptn <= 26:
                        sou += 1
                if roto == 5:
                    ret |= YakuList.JUNCHANTA  # 纯全带幺九
                    han += 3 - self.kui
                elif roto + ji == 5 and num_shuntsu + num_chi > 0:
                    ret |= YakuList.HONCHANTA  # 混全带幺九
                    han += 2 - self.kui
                else:
                    g = True
                    for m in mentsu:
                        if m not in [32, 19, 20, 21, 23, 25]:
                            g = False
                            break
                    if g:
                        for i in range(num_shuntsu + num_chi):
                            if mentsu[4 - i] != 19:
                                g = False
                                break
                        if g:  # 绿一色
                            yakuman.append(YakuList.RYUISO)  # 绿一色
                            han_yakuman += 1
                ret |= sangen << YakuList.SANGENHAI_SHIFT  # 三元牌
                han += sangen
                for i in range(num_kotsu):
                    if mentsu[i + 1] == self.bahai:
                        ret |= YakuList.BAKAZEHAI  # 场风
                        han += 1
                    if mentsu[i + 1] == self.menfon:
                        ret |= YakuList.MENFONHAI  # 门风
                        han += 1
            else:
                fu = 25
                ret |= YakuList.CHITOITSU  # 七对子
                han += 2
                roto = self.counter[0] + self.counter[8] + self.counter[9] + self.counter[17] + self.counter[18] + self.counter[26]
                ji = sum(self.counter[_] for _ in range(27, 34))
                if ji == 14:
                    yakuman.append(YakuList.TSUISO)  # 字一色
                    han_yakuman += 1
                elif roto + ji == 14:
                    ret |= YakuList.HONROTO  # 混老头
                    han += 2
            if roto + ji == 0:
                ret |= YakuList.TANYAO  # 断幺
                han += 1
            if (man == 0) + (pin == 0) + (sou == 0) == 2:
                if ji == 0:
                    ret |= YakuList.CHINITSU  # 清一色
                    han += 6 - self.kui
                else:
                    ret |= YakuList.HONITSU  # 混一色
                    han += 3 - self.kui
            if fu != 25:
                fu = (fu + 9) // 10 * 10
            if han_yakuman:
                return han_yakuman, fu, 8000 * han_yakuman, yakuman
            han_list[k] = han
            fu_list[k] = fu
            ret_list[k] = ret
        if self.tsumo and not self.kui:
            ret_list |= YakuList.TSUMO  # 门清自摸
            han_list += 1
        if self.riichi == 1:  # 立直
            ret_list |= YakuList.RIICHI
            han_list += 1
            if self.ippatsu:  # 一发
                ret_list |= YakuList.IPPATSU
                han_list += 1
        elif self.riichi == 2:  # 两立直
            ret_list |= YakuList.DOUBLE_RIICHI
            han_list += 2
            if self.ippatsu:
                ret_list |= YakuList.IPPATSU  # 一发
                han_list += 1
        if self.tokusyu > 0:
            if self.tokusyu == 1:  # 岭上开花
                ret_list |= YakuList.RINSHAN
            elif self.tokusyu == 2:  # 抢杠
                ret_list |= YakuList.ROB_KAN
            elif self.tokusyu == 3:  # 海底
                ret_list |= YakuList.HAITEI
            han_list += 1
        ret_list |= self.dora_count << YakuList.DORA_SHIFT
        han_list += self.dora_count
        if self.riichi:
            ret_list |= self.ura_dora_count << YakuList.URA_DORA_SHIFT
            han_list += self.ura_dora_count
        ret_list |= self.aka_count << YakuList.AKA_DORA_SHIFT
        han_list += self.aka_count
        score = fu_list * 1 << (han_list + 2)
        max_score = np.max(score)
        if (score == max_score).sum() == 1:
            max_score_index = score.argmax()
        else:
            max_score_index = ((score == max_score) * han_list).argmax()
        i = max_score_index
        fu = fu_list[i]
        ret = ret_list[i]
        score = max_score
        han = han_list[i]
        if han == self.dora_count + self.aka_count + self.ura_dora_count:  # 只有宝牌的番
            han = 0
        if han < 5:
            if score >= 2000:
                score = 2000
        elif han == 5:
            score = 2000
        elif 6 <= han <= 7:
            score = 3000
        elif 8 <= han <= 10:
            score = 4000
        elif 11 <= han <= 12:
            score = 6000
        elif han >= 13:
            score = 8000
        else:
            score = fu * 2 ** (han + 2)
        return int(han), int(fu), int(score), int(ret)

    @staticmethod
    def parse_yaku_ret(ret, tsumo):
        yaku_list = []
        if isinstance(ret, List):
            for i in ret:
                if i == YakuList.TENHOU:
                    yaku_list.append('天和')
                elif i == YakuList.CHIHOU:
                    yaku_list.append('地和')
                elif i == YakuList.SUKANTSU:
                    yaku_list.append('四杠子')
                elif i == YakuList.SUANKO:
                    yaku_list.append('四暗刻')
                elif i == YakuList.CHINROTO:
                    yaku_list.append('清老头')
                elif i == YakuList.DAISANGEN:
                    yaku_list.append('大三元')
                elif i == YakuList.DAISUSHI:
                    yaku_list.append('大四喜')
                elif i == YakuList.SYOSUSHI:
                    yaku_list.append('小四喜')
                elif i == YakuList.TSUISO:
                    yaku_list.append('字一色')
                elif i == YakuList.RYUISO:
                    yaku_list.append('绿一色')
                elif i == YakuList.CHURENPOTO:
                    yaku_list.append('九莲宝灯')
                elif i == YakuList.KOKUSHIMUSO:
                    yaku_list.append('国士无双')
                elif i == YakuList.SUANKOTANKI:
                    yaku_list.append('四暗刻单骑')
                elif i == YakuList.KOKUSHIJUSANMEN:
                    yaku_list.append('国士十三面')
                elif i == YakuList.CHURENCHUMEN:
                    yaku_list.append('纯正九莲宝灯')
            return yaku_list
        riichi = False
        if ret & YakuList.RIICHI:
            yaku_list.append('立直')
            riichi = True
        if ret & YakuList.DOUBLE_RIICHI:
            yaku_list.append('两立直')
            riichi = True
        if ret & YakuList.IPPATSU:
            yaku_list.append('一发')
        if ret & YakuList.TSUMO:
            yaku_list.append('门清自摸')
        if ret & YakuList.PINFU:
            yaku_list.append('平和')
        if ret & YakuList.MENFONHAI:
            yaku_list.append('门风')
        if ret & YakuList.BAKAZEHAI:
            yaku_list.append('场风')
        sangen = (ret & YakuList.SANGENHAI_MASK) >> YakuList.SANGENHAI_SHIFT
        if sangen:
            yaku_list.append(f'三元牌の役牌: {sangen}')
        if ret & YakuList.TANYAO:
            yaku_list.append('断幺')
        if ret & YakuList.IPEKO:
            yaku_list.append('一杯口')
        if ret & YakuList.ROB_KAN:
            yaku_list.append('抢杠')
        elif ret & YakuList.RINSHAN:
            yaku_list.append('岭上开花')
        elif ret & YakuList.HAITEI:
            if tsumo:
                yaku_list.append('海底摸月')
            else:
                yaku_list.append('河底捞鱼')
        if ret & YakuList.SANSYOKUDOKO:
            yaku_list.append('三色同刻')
        if ret & YakuList.SANKANTSU:
            yaku_list.append('三杠子')
        if ret & YakuList.TOITOI:
            yaku_list.append('对对和')
        if ret & YakuList.SANANKO:
            yaku_list.append('三暗刻')
        if ret & YakuList.SYOSANGEN:
            yaku_list.append('小三元')
        if ret & YakuList.HONROTO:
            yaku_list.append('混老头')
        if ret & YakuList.CHITOITSU:
            yaku_list.append('七对子')
        if ret & YakuList.HONCHANTA:
            yaku_list.append('混全带幺九')
        if ret & YakuList.IKKITSUKAN:
            yaku_list.append('一气通贯')
        elif ret & YakuList.SANSYOKUDOJUN:
            yaku_list.append('三色同顺')
        if ret & YakuList.RYANPEKO:
            yaku_list.append('两杯口')
        if ret & YakuList.JUNCHANTA:
            yaku_list.append('纯全带幺九')
        if ret & YakuList.HONITSU:
            yaku_list.append('混一色')
        elif ret & YakuList.CHINITSU:
            yaku_list.append('清一色')

        dora = (ret & YakuList.DORA_MASK) >> YakuList.DORA_SHIFT
        if dora:
            yaku_list.append(f"宝牌: {dora}")
        aka = (ret & YakuList.AKA_DORA_MASK) >> YakuList.AKA_DORA_SHIFT
        if aka:
            yaku_list.append(f"赤宝牌: {aka}")
        if riichi:
            ura_dora = (ret & YakuList.URA_DORA_MASK) >> YakuList.URA_DORA_SHIFT
            yaku_list.append(f"里宝牌: {ura_dora}")
        return yaku_list
