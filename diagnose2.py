#!/usr/bin/env python3
"""诊断：列出网盘所有文件名 vs 本地文件"""
import json
import time
import requests
from pathlib import Path
from quark_client import QuarkClient

BASE_DIR = Path(__file__).parent
COOKIE_FILE = BASE_DIR / 'cookie.txt'
SAVE_DIR = BASE_DIR / 'assets' / 'audio' / 'jp_songs'
SONGS_FILE = BASE_DIR / 'data' / 'songs' / 'higequ_riyu_songs.json'

lines = COOKIE_FILE.read_text(encoding='utf-8').splitlines()
cookie_str = next((l.strip() for l in lines if l.strip() and not l.strip().startswith('#')), '')

client = QuarkClient(cookies=cookie_str, auto_login=False)

root = client.list_files(folder_id='0', page=1, size=100)
target_fid = None
for item in root.get('data', {}).get('list', []):
    if item.get('file_name') == '日语歌曲下载':
        target_fid = item['fid']
        break

# 列出目标文件夹的直接子项
print("=== 目标文件夹直接子项 ===")
resp = client.list_files(folder_id=target_fid, page=1, size=100)
items = resp.get('data', {}).get('list', [])
total = resp.get('data', {}).get('_total', len(items))
print(f"总数: {total}, 本页: {len(items)}")

folders = [i for i in items if not i.get('file')]
files = [i for i in items if i.get('file')]
print(f"文件夹: {len(folders)}, 文件: {len(files)}")

# 列出所有子文件夹名称和前5个文件
print("\n=== 子文件夹列表 ===")
for i, folder in enumerate(folders, 1):
    fid = folder['fid']
    fname = folder['file_name']
    # 获取子文件夹内容
    sub = client.list_files(folder_id=fid, page=1, size=10)
    sub_items = sub.get('data', {}).get('list', [])
    mp3_names = [s['file_name'] for s in sub_items if s.get('file_name', '').lower().endswith('.mp3')]
    print(f"  [{i}] {fname} -> {mp3_names}")
    time.sleep(0.2)

# 本地文件
local_names = set(f.name for f in SAVE_DIR.glob('*.mp3'))
print(f"\n本地MP3: {len(local_names)}")

# 原始歌曲列表
with open(SONGS_FILE, 'r', encoding='utf-8') as f:
    songs = json.load(f)
print(f"原始歌曲: {len(songs)}")

client.close()
