#!/usr/bin/env python3
"""
1. 找出缺失的歌曲并补全下载
2. 从网页下载每首歌的lrc歌词
"""
import json
import os
import re
import time
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
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            return line
    return None


def download_with_requests(download_url, save_path, cookie_str):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Referer': 'https://pan.quark.cn/',
        'Origin': 'https://pan.quark.cn',
        'Cookie': cookie_str,
    }
    response = requests.get(download_url, headers=headers, stream=True, timeout=120)
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
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


def find_missing_songs(client, target_fid, cookie_str):
    """找出缺失的歌曲并下载"""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    
    # 获取网盘中所有文件
    print("扫描网盘文件...")
    all_files = collect_all_files(client, target_fid)
    mp3_files = [f for f in all_files if f.get('file_name', '').lower().endswith('.mp3')]
    print(f"网盘中有 {len(mp3_files)} 个MP3文件")
    
    # 获取本地已下载文件
    local_files = set(f.name for f in SAVE_DIR.glob('*.mp3'))
    print(f"本地已下载 {len(local_files)} 个MP3文件")
    
    # 找出缺失的
    missing = []
    for f in mp3_files:
        if f['file_name'] not in local_files:
            missing.append(f)
    
    print(f"需要补全 {len(missing)} 首歌曲\n")
    
    if not missing:
        print("所有歌曲已下载完成！")
        return
    
    # 下载缺失的
    success = 0
    fail = 0
    for i, file_info in enumerate(missing, 1):
        fid = file_info['fid']
        fname = file_info['file_name']
        output_path = SAVE_DIR / fname
        
        print(f"  [{i}/{len(missing)}] ↓ {fname} ...", end='', flush=True)
        try:
            download_url = client.download.get_download_url(fid)
            download_with_requests(download_url, str(output_path), cookie_str)
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f" ✓ ({size_mb:.1f} MB)")
            success += 1
        except Exception as e:
            print(f" ✗ {e}")
            fail += 1
        time.sleep(1)
    
    print(f"\n补全完成: 成功 {success}, 失败 {fail}")


def fetch_lrc_from_player(rid, title, artist):
    """从player页面提取歌词并生成lrc格式"""
    url = f"https://higequ.com/player/{rid}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = 'utf-8'
        html = resp.text
        
        # 提取歌词行 - 查找 lyric-line data-time 元素
        # 格式: <div class="lyric-line" data-time="12.34">歌词文本</div>
        lyric_lines = re.findall(
            r'class="lyric-line[^"]*"\s+data-time="([^"]*)"[^>]*>([^<]+)<',
            html
        )
        
        if not lyric_lines:
            # 尝试另一种格式
            lyric_lines = re.findall(
                r'data-time="([^"]*)"[^>]*class="lyric-line[^"]*"[^>]*>([^<]+)<',
                html
            )
        
        if not lyric_lines:
            return None
        
        # 生成lrc格式
        lrc_lines = [
            f'[ti:{title}]',
            f'[ar:{artist}]',
            f'[by:higequ.com]',
            ''
        ]
        
        for time_str, text in lyric_lines:
            text = text.strip()
            if not text:
                continue
            try:
                t = float(time_str)
                minutes = int(t // 60)
                seconds = t % 60
                lrc_lines.append(f'[{minutes:02d}:{seconds:05.2f}]{text}')
            except ValueError:
                continue
        
        return '\n'.join(lrc_lines) if len(lrc_lines) > 4 else None
        
    except Exception as e:
        print(f"    获取歌词失败: {e}")
        return None


def download_all_lyrics():
    """下载所有歌曲的歌词"""
    print("\n=== 下载歌词 ===")
    
    # 加载歌曲数据
    with open(SONGS_FILE, 'r', encoding='utf-8') as f:
        songs = json.load(f)
    
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    
    success = 0
    fail = 0
    skip = 0
    
    for i, song in enumerate(songs, 1):
        title = song.get('title', '')
        artist = song.get('artist', '')
        rid = song.get('rid', '')
        
        # lrc文件名与mp3对应
        safe_name = f"{artist} - {title}"
        # 清理文件名中的非法字符
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', safe_name)
        lrc_path = SAVE_DIR / f"{safe_name}.lrc"
        
        if lrc_path.exists() and lrc_path.stat().st_size > 0:
            skip += 1
            continue
        
        print(f"  [{i}/{len(songs)}] 歌词: {title} - {artist} ...", end='', flush=True)
        
        lrc_content = fetch_lrc_from_player(rid, title, artist)
        
        if lrc_content:
            lrc_path.write_text(lrc_content, encoding='utf-8')
            print(f" ✓")
            success += 1
        else:
            print(f" ✗ 无歌词")
            fail += 1
        
        time.sleep(0.5)
    
    print(f"\n歌词下载完成: 成功 {success}, 跳过 {skip}, 失败 {fail}")


def main():
    print("=" * 60)
    print("补全歌曲下载 + 歌词下载")
    print("=" * 60)
    
    cookie_str = load_cookie()
    if not cookie_str:
        print("❌ 无法读取Cookie")
        return
    
    client = QuarkClient(cookies=cookie_str, auto_login=False)
    
    # 查找目标文件夹
    root = client.list_files(folder_id='0', page=1, size=100)
    target_fid = None
    for item in root.get('data', {}).get('list', []):
        if item.get('file_name') == TARGET_FOLDER_NAME:
            target_fid = item['fid']
            break
    
    if not target_fid:
        print(f"❌ 找不到文件夹: {TARGET_FOLDER_NAME}")
        return
    
    # 1. 补全缺失歌曲
    find_missing_songs(client, target_fid, cookie_str)
    
    client.close()
    
    # 2. 下载歌词
    download_all_lyrics()
    
    # 3. 统计
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
