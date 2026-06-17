#!/usr/bin/env python3
"""诊断：对比网盘文件和本地文件"""
import json
import time
import requests
from pathlib import Path
from quark_client import QuarkClient

BASE_DIR = Path(__file__).parent
COOKIE_FILE = BASE_DIR / 'cookie.txt'
SAVE_DIR = BASE_DIR / 'assets' / 'audio' / 'jp_songs'

lines = COOKIE_FILE.read_text(encoding='utf-8').splitlines()
cookie_str = next((l.strip() for l in lines if l.strip() and not l.strip().startswith('#')), '')

client = QuarkClient(cookies=cookie_str, auto_login=False)

# 找到目标文件夹
root = client.list_files(folder_id='0', page=1, size=100)
target_fid = None
for item in root.get('data', {}).get('list', []):
    if item.get('file_name') == '日语歌曲下载':
        target_fid = item['fid']
        break

def collect_all_files(client, folder_id):
    all_files = []
    page = 1
    while True:
        resp = client.list_files(folder_id=folder_id, page=page, size=100)
        items = resp.get('data', {}).get('list', [])
        if not items:
            break
        for item in items:
            if item.get('file'):
                all_files.append(item)
            else:
                all_files.extend(collect_all_files(client, item['fid']))
        total = resp.get('data', {}).get('_total', 0)
        if len(items) * page >= total:
            break
        page += 1
    return all_files

all_files = collect_all_files(client, target_fid)
mp3_files = [f for f in all_files if f.get('file_name', '').lower().endswith('.mp3')]

print(f"网盘MP3: {len(mp3_files)}")
cloud_names = set()
for f in mp3_files:
    name = f['file_name']
    cloud_names.add(name)
    
print(f"网盘不重复文件名: {len(cloud_names)}")

local_names = set(f.name for f in SAVE_DIR.glob('*.mp3'))
print(f"本地MP3: {len(local_names)}")

# 找出网盘有但本地没有的
missing_names = cloud_names - local_names
print(f"\n缺失的歌曲 ({len(missing_names)}):")
for name in sorted(missing_names):
    print(f"  {name}")

# 找出本地有但网盘没有的（不应该有）
extra = local_names - cloud_names
if extra:
    print(f"\n本地多出的 ({len(extra)}):")
    for name in sorted(extra):
        print(f"  {name}")

client.close()
