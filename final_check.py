#!/usr/bin/env python3
"""最终检查：修复特殊字符匹配，确认最终状态"""
import json
import re
from pathlib import Path

SONGS_FILE = Path(__file__).parent / 'data' / 'songs' / 'higequ_riyu_songs.json'
SAVE_DIR = Path(__file__).parent / 'assets' / 'audio' / 'jp_songs'

def normalize(s):
    """标准化字符串用于比较：移除特殊字符，转小写"""
    s = s.lower()
    # 替换常见特殊字符
    s = re.sub(r'[/\\:""*?|]', '_', s)
    s = re.sub(r'[（(][^）)]*[）)]', '', s)  # 移除括号内容
    s = re.sub(r'\s+', '', s)  # 移除空格
    return s

def is_song_downloaded(title, artist, local_names):
    """检查歌曲是否已下载（支持模糊匹配）"""
    title_norm = normalize(title)
    artist_norm = normalize(artist)
    
    for name in local_names:
        name_norm = normalize(name)
        # 标题和艺术家都在文件名中
        if title_norm in name_norm and artist_norm in name_norm:
            return True
        # 只有标题（对于艺术家名不同的情况）
        if len(title_norm) > 5 and title_norm in name_norm:
            return True
    return False

# 加载歌曲列表
with open(SONGS_FILE, 'r', encoding='utf-8') as f:
    songs = json.load(f)

# 本地文件
local_names = [f.name for f in SAVE_DIR.glob('*.mp3')]
print(f"本地MP3文件: {len(local_names)}")
print(f"原始歌曲列表: {len(songs)}")

# 检查每首歌
downloaded = []
missing = []
for song in songs:
    title = song.get('title', '')
    artist = song.get('artist', '')
    music_url = song.get('music_url', '')
    
    if is_song_downloaded(title, artist, local_names):
        downloaded.append(song)
    else:
        missing.append(song)

print(f"\n已下载: {len(downloaded)}")
print(f"缺失: {len(missing)}")

if missing:
    print(f"\n缺失歌曲详情:")
    for s in missing:
        url_status = "有链接(分享空)" if s.get('music_url') else "无链接"
        print(f"  - {s['title']} - {s['artist']} [{url_status}]")

# 统计lrc
lrc_count = len(list(SAVE_DIR.glob('*.lrc')))
print(f"\n{'=' * 60}")
print(f"最终统计:")
print(f"  MP3: {len(local_names)}/100")
print(f"  LRC: {lrc_count}/100")
print(f"  无法下载: {len(missing)} 首")
print(f"  保存目录: {SAVE_DIR}")
print("=" * 60)
