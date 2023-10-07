"""
该文件用于打听牌表
"""

from make_agari_table_2 import *


def remove_one_from_ptn(a):
    ptns = []
    for i in range(len(a)):
        for j in range(len(a[i])):
            if a[i][j] == 0:
                continue
            a[i][j] -= 1
            new_ptn = copy.deepcopy(a)
            a[i][j] += 1
            if new_ptn[i][j] != 0:
                ptns.append(new_ptn)
            else:
                if len(new_ptn[i]) == 1:
                    new_ptn.pop(i)
                    ptns.append(new_ptn)
                    continue
                if j == 0:
                    new_ptn[i].pop(0)
                elif j == len(a[i]) - 1:
                    new_ptn[i].pop()
                else:
                    if new_ptn[i][j-1] == 0:
                        left, right = new_ptn[i][:j-1], new_ptn[i][j+1:]
                        new_ptn.pop(i)
                        new_ptn.insert(i, left)
                        if right:
                            new_ptn.insert(i+1, right)
                    elif new_ptn[i][j+1] == 0:
                        left, right = new_ptn[i][:j], new_ptn[i][j+2:]
                        new_ptn.pop(i)
                        new_ptn.insert(i, right)
                        if left:
                            new_ptn.insert(i, left)
                    ptns.append(new_ptn)
    return ptns


MACHI_TABLE = 'MACHI_TABLE.pkl'
if __name__ == '__main__':
    machi_table = {0: set(), 1: set()}

    chitoi = ptn([[2], [2], [2], [2], [2], [2], [2]])
    chitoi = list(filter(lambda x: all(_ in [0, 2] for _ in sum(x, [])), chitoi))
    chitoi = unique(chitoi)
    patterns = []
    for p in tqdm.tqdm(chitoi):
        patterns.extend(remove_one_from_ptn(p))
    for a in [[[1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1], [2]],
              [[1, 1, 1], [1, 1, 1], [1, 1, 1], [3], [2]],
              [[1, 1, 1], [1, 1, 1], [3], [3], [2]],
              [[1, 1, 1], [3], [3], [3], [2]],
              [[3], [3], [3], [3], [2]],
              [[1, 1, 1], [1, 1, 1], [1, 1, 1], [2]],
              [[1, 1, 1], [1, 1, 1], [3], [2]],
              [[1, 1, 1], [3], [3], [2]],
              [[3], [3], [3], [2]],
              [[1, 1, 1], [1, 1, 1], [2]],
              [[1, 1, 1], [3], [2]],
              [[3], [3], [2]],
              [[1, 1, 1], [2]],
              [[3], [2]],
              [[2]]]:
        ptns = unique(ptn(a))
        for p in tqdm.tqdm(ptns):
            patterns.extend(remove_one_from_ptn(p))
    patterns = unique(patterns)
    for p in patterns:
        key = calc_key(p)
        machi_table[0].add(key)
    kokushi_ptns = []
    p = [[1] for _ in range(12)]
    for i in range(13):
        p.insert(i, [2])
        kokushi_ptns.extend(remove_one_from_ptn(p))
        p.pop(i)
    kokushi_ptns = unique(kokushi_ptns)
    for p in tqdm.tqdm(kokushi_ptns):
        key = calc_key(p)
        machi_table[1].add(key)

    print('听牌pattern数:', len(machi_table[0]))
    with open(MACHI_TABLE, 'wb') as f:
        f.write(pickle.dumps(machi_table))