import os
import signal
from pathlib import Path
import requests
import re
from multiprocessing import Pool

project_dir = os.path.abspath(Path(os.path.dirname(__file__)).parent)
data_dir = os.path.join(project_dir, 'data')
headers = {
    'Host': 'tenhou.net',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
}


def download_file(url):
    file_name = url.split('?')[1] + '.xml'
    try:
        response = requests.get(url, stream=True, headers=headers)
        with open(os.path.join(data_dir, file_name), 'w') as out_file:
            game_type = int(re.search('<GO type="(\\d+)"', response.text).groups()[0])
            if game_type & 0x10 or game_type & 0x04 or game_type & 0x02:  # 把混在里面的三人麻将、无赤牌、无食断的对局筛选掉
                return
            out_file.write(response.text)
        print(f"Downloaded {file_name} from {url}")
    except:
        return


def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


if __name__ == '__main__':
    log_dir = os.path.join(project_dir, 'logs')
    os.makedirs(data_dir, exist_ok=True)
    links = []
    for log in os.listdir(log_dir):
        with open(os.path.join(log_dir, log), 'r') as f:
            data = f.readlines()
        for line in data:
            if '四鳳' in line:
                link = re.search('<a href="(.*)">', line).groups()[0].replace('?log=', 'log/?')
                links.append(link)
    links = set(links)
    exists = list(map(lambda x: 'http://tenhou.net/0/log/?' + x.split('.')[0], os.listdir(data_dir)))
    links.difference_update(exists)
    print(f'Found {len(links)} links')
    pool = Pool(initializer=init_worker)
    try:
        pool.map(download_file, links)
    except KeyboardInterrupt:
        pool.terminate()
        pool.join()
    else:
        pool.close()
        pool.join()
