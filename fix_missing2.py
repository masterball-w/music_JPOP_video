#!/usr/bin/env python3
"""
完整修复：
1. 对比原始100首歌 vs 本地已有文件
2. 对缺失的歌重新转存（用新文件夹避免冲突）
3. 下载所有缺失的MP3
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


def load_cookie():
    lines = COOKIE_FILE.read_text(encoding='utf-8').splitlines()
    return next((l.strip() for l in lines if l.strip() and not l.strip().startswith('#')), '')


def download_file(url, save_path, cookie_str):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Referer': 'https://pan.quark.cn/',
        'Origin': 'https://pan.quark.cn',
        'Cookie': cookie_str,
    }
    resp = requests.get(url, headers=headers, stream=True, timeout=120)
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


def is_song_in_local(title, artist, local_names):
    """检查歌曲是否已在本地"""
    for name in local_names:
        name_lower = name.lower()
        # 文件名格式: "artist - title.mp3"
        if title.lower() in name_lower and artist.lower() in name_lower:
            return True
        # 也检查只有标题的
        if title.lower() in name_lower:
            return True
    return False


def main():
    cookie_str = load_cookie()
    client = QuarkClient(cookies=cookie_str, auto_login=False)

    # 1. 加载原始歌曲
    with open(SONGS_FILE, 'r', encoding='utf-8') as f:
        songs = json.load(f)

    # 2. 本地已有文件
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    local_names = [f.name for f in SAVE_DIR.glob('*.mp3')]
    print(f"本地MP3: {len(local_names)}")

    # 3. 找出缺失的歌曲
    missing = []
    for song in songs:
        title = song.get('title', '')
        artist = song.get('artist', '')
        if not is_song_in_local(title, artist, local_names):
            missing.append(song)

    print(f"缺失歌曲: {len(missing)}")
    for s in missing:
        print(f"  - {s['title']} - {s['artist']}")

    if not missing:
        print("所有歌曲已下载完成！")
        client.close()
        return

    # 4. 创建新文件夹用于存放缺失歌曲
    folder_name = '日语歌曲补全'
    root = client.list_files(folder_id='0', page=1, size=100)
    target_fid = None
    for item in root.get('data', {}).get('list', []):
        if item.get('file_name') == folder_name:
            target_fid = item['fid']
            break

    if not target_fid:
        try:
            result = client.create_folder(folder_name, parent_id='0')
            target_fid = result['data']['fid']
        except Exception as e:
            if '同名' in str(e):
                for item in client.list_files(folder_id='0', page=1, size=100).get('data', {}).get('list', []):
                    if item.get('file_name') == folder_name:
                        target_fid = item['fid']
                        break
    print(f"\n目标文件夹ID: {target_fid}")

    # 5. 转存缺失歌曲
    songs_with_url = [s for s in missing if s.get('music_url') and 'quark' in s['music_url']]
    print(f"\n需要转存: {len(songs_with_url)}")

    if songs_with_url:
        urls = [s['music_url'] for s in songs_with_url]

        def progress(current, total, url, result):
            title = next((s['title'] for s in songs_with_url if s['music_url'] == url), url)
            status = '✓' if result.get('success') else f"✗ {result.get('error', '')[:30]}"
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

    # 6. 从新文件夹下载所有文件
    print("\n=== 下载缺失歌曲 ===")
    all_files = collect_all_files(client, target_fid)
    mp3_files = [f for f in all_files if f.get('file_name', '').lower().endswith('.mp3')]
    # 去重
    seen = set()
    unique_mp3 = []
    for f in mp3_files:
        if f['file_name'] not in seen:
            seen.add(f['file_name'])
            unique_mp3.append(f)

    print(f"待下载: {len(unique_mp3)}")

    success = 0
    fail = 0
    for i, f in enumerate(unique_mp3, 1):
        fname = f['file_name']
        output_path = SAVE_DIR / fname

        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"  [{i}/{len(unique_mp3)}] ⊘ 已存在: {fname}")
            continue

        print(f"  [{i}/{len(unique_mp3)}] ↓ {fname} ...", end='', flush=True)
        try:
            dl_url = client.download.get_download_url(f['fid'])
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
    print(f"最终统计: MP3={mp3_count}, LRC={lrc_count}")
    print(f"保存目录: {SAVE_DIR}")

    # 列出仍然缺失的
    local_names2 = [f.name for f in SAVE_DIR.glob('*.mp3')]
    still_missing = []
    for song in songs:
        if not is_song_in_local(song['title'], song['artist'], local_names2):
            still_missing.append(song)
    if still_missing:
        print(f"\n仍然缺失 ({len(still_missing)}):")
        for s in still_missing:
            print(f"  - {s['title']} - {s['artist']}")
    print("=" * 60)


if __name__ == '__main__':
    main()
