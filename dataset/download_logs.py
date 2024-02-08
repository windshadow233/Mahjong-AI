import os
import signal
from pathlib import Path
import requests
import re
import gzip
from multiprocessing import Pool

project_dir = os.path.abspath(Path(os.path.dirname(__file__)).parent)
log_dir = os.path.join(project_dir, 'logs')
headers = {
    'Host': 'tenhou.net',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
}


def download_logs(filename):
    try:
        url = f'https://tenhou.net/sc/raw/dat/{filename}.html.gz'
        r = requests.get(url, headers=headers)
        r = gzip.decompress(r.content).decode('utf-8')
        with open(os.path.join(log_dir, f'{filename}.txt'), 'w') as f:
            f.write(r)
        print(f"Downloaded {filename}.txt from {url}")
    except:
        return


def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


if __name__ == '__main__':
    os.makedirs(log_dir, exist_ok=True)
    r = requests.get('https://tenhou.net/sc/raw/list.cgi', headers=headers)
    filenames = re.findall('scc\\d+.html.gz', r.text)
    exists = list(map(lambda x: x[:-4], os.listdir(log_dir)))
    filenames = set(map(lambda x: x[:-8], filenames))
    filenames.difference_update(exists)
    print(f'Found {len(filenames)} logs')
    pool = Pool(initializer=init_worker)
    try:
        pool.map(download_logs, filenames)
    except KeyboardInterrupt:
        pool.terminate()
        pool.join()
    else:
        pool.close()
        pool.join()