#!/usr/bin/env python3
"""
找出缺失歌曲 → 重新转存 → 下载
"""
import json
import time
import re
import requests
from pathlib import Path
from quark_client import QuarkClient

BASE_DIR = Path(__file__).parent
COOKIE_FILE = BASE_DIR / 'cookie.txt'
SONGS_FILE = BASE_DIR / 'data' / 'songs' / 'higequ_riyu_songs.json'
SAVE_DIR = BASE_DIR / 'assets' / 'audio' / 'jp_songs'
TARGET_FOLDER_NAME = '日语歌曲下载'


def load_cookie():
    lines = COOKIE_FILE.read_text(encoding='utf-8').splitlines()
    return next((l.strip() for l in lines if l.strip() and not l.strip().startswith('#')), '')


def download_file(download_url, save_path, cookie_str):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Referer': 'https://pan.quark.cn/',
        'Origin': 'https://pan.quark.cn',
        'Cookie': cookie_str,
    }
    resp = requests.get(download_url, headers=headers, stream=True, timeout=120)
    resp.raise_for_status()
    with open(save_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


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


def main():
    cookie_str = load_cookie()
    client = QuarkClient(cookies=cookie_str, auto_login=False)

    # 1. 加载原始歌曲列表
    with open(SONGS_FILE, 'r', encoding='utf-8') as f:
        songs = json.load(f)
    print(f"原始歌曲: {len(songs)}")

    # 2. 获取网盘中已有的文件（按歌曲名匹配）
    root = client.list_files(folder_id='0', page=1, size=100)
    target_fid = None
    for item in root.get('data', {}).get('list', []):
        if item.get('file_name') == TARGET_FOLDER_NAME:
            target_fid = item['fid']
            break

    all_cloud_files = collect_all_files(client, target_fid)
    cloud_mp3_names = set(f['file_name'] for f in all_cloud_files if f.get('file_name', '').lower().endswith('.mp3'))
    print(f"网盘MP3（去重）: {len(cloud_mp3_names)}")

    # 3. 本地已有的文件
    local_names = set(f.name for f in SAVE_DIR.glob('*.mp3'))
    print(f"本地MP3: {len(local_names)}")

    # 4. 找出缺失的歌曲（在原始列表中，但本地没有）
    # 构建歌曲名到歌曲信息的映射
    # 网盘文件名格式: "艺术家 - 歌曲名.mp3"
    missing_songs = []
    for song in songs:
        title = song.get('title', '')
        artist = song.get('artist', '')
        music_url = song.get('music_url', '')
        rid = song.get('rid', '')

        # 检查本地是否已有（模糊匹配）
        found = False
        for local_name in local_names:
            # 本地文件名格式: "艺术家 - 歌曲名.mp3"
            if title in local_name and artist in local_name:
                found = True
                break

        if not found:
            missing_songs.append(song)

    print(f"\n缺失的歌曲: {len(missing_songs)}")
    for s in missing_songs:
        print(f"  - {s['title']} - {s['artist']} (url: {s.get('music_url', 'N/A')})")

    # 5. 重新转存缺失的歌曲
    songs_with_url = [s for s in missing_songs if s.get('music_url') and 'quark' in s['music_url']]
    print(f"\n需要重新转存: {len(songs_with_url)}")

    if songs_with_url:
        urls = [s['music_url'] for s in songs_with_url]

        def progress(current, total, url, result):
            title = next((s['title'] for s in songs_with_url if s['music_url'] == url), url)
            status = '✓' if result.get('success') else f"✗ {result.get('error', '')}"
            print(f"  [{current}/{total}] {status} {title}")

        client.shares.batch_save_shares(
            share_urls=urls,
            target_folder_id=target_fid,
            save_all=True,
            wait_for_completion=False,
            progress_callback=progress
        )

        print("\n等待转存处理...")
        time.sleep(15)

    # 6. 重新扫描网盘并下载缺失的
    print("\n=== 下载缺失的歌曲 ===")
    all_cloud_files = collect_all_files(client, target_fid)
    cloud_mp3 = [f for f in all_cloud_files if f.get('file_name', '').lower().endswith('.mp3')]

    # 去重：按文件名，只保留第一个
    seen = set()
    unique_mp3 = []
    for f in cloud_mp3:
        if f['file_name'] not in seen:
            seen.add(f['file_name'])
            unique_mp3.append(f)

    # 找出本地没有的
    to_download = []
    for f in unique_mp3:
        if f['file_name'] not in local_names:
            to_download.append(f)

    print(f"需要下载: {len(to_download)}")

    success = 0
    fail = 0
    for i, f in enumerate(to_download, 1):
        fid = f['fid']
        fname = f['file_name']
        output_path = SAVE_DIR / fname

        print(f"  [{i}/{len(to_download)}] ↓ {fname} ...", end='', flush=True)
        try:
            dl_url = client.download.get_download_url(fid)
            download_file(dl_url, str(output_path), cookie_str)
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f" ✓ ({size_mb:.1f} MB)")
            success += 1
        except Exception as e:
            print(f" ✗ {e}")
            fail += 1
        time.sleep(1)

    print(f"\n下载完成: 成功 {success}, 失败 {fail}")

    client.close()

    # 7. 最终统计
    mp3_count = len(list(SAVE_DIR.glob('*.mp3')))
    lrc_count = len(list(SAVE_DIR.glob('*.lrc')))
    print(f"\n{'=' * 60}")
    print(f"最终统计:")
    print(f"  MP3文件: {mp3_count}")
    print(f"  LRC文件: {lrc_count}")
    print(f"  保存目录: {SAVE_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    main()
