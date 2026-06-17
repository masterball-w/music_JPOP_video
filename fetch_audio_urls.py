#!/usr/bin/env python3
"""Extract musicUrl (cloud drive link) from each song's player page"""
import requests
import re
import json
import os
import time

def get_all_rids():
    """Get all rids from all pages"""
    rids = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    for page in range(1, 5):
        url = "https://higequ.com/riyu/" if page == 1 else f"https://higequ.com/riyu/?p={page}"
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = 'utf-8'
        page_rids = re.findall(r'data-rid="(\d+)"', resp.text)
        rids.extend(page_rids)
        time.sleep(0.5)
    return rids

def get_music_info(rid):
    """Get musicUrl and cover image from player page"""
    url = f"https://higequ.com/player/{rid}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = 'utf-8'
        html = resp.text

        # Extract musicUrl
        music_url_match = re.search(r"let\s+musicUrl\s*=\s*'([^']*)'", html)
        music_url = music_url_match.group(1) if music_url_match else ""

        # Extract cover image
        cover_match = re.search(r'!\[专辑封面\]\(([^)]+)\)', html)
        cover_url = cover_match.group(1) if cover_match else ""

        # Extract title and artist from HTML
        title_match = re.search(r'id="music-title"[^>]*>([^<]+)<', html)
        artist_match = re.search(r'id="music-artist"[^>]*>([^<]+)<', html)
        title = title_match.group(1).strip() if title_match else ""
        artist = artist_match.group(1).strip() if artist_match else ""

        return {
            'rid': rid,
            'title': title,
            'artist': artist,
            'music_url': music_url,
            'cover_url': cover_url
        }
    except Exception as e:
        print(f"  Error fetching rid {rid}: {e}")
        return None

def main():
    print("Getting all rids...")
    rids = get_all_rids()
    print(f"Found {len(rids)} songs")

    results = []
    for i, rid in enumerate(rids):
        print(f"[{i+1}/{len(rids)}] Fetching player page for rid={rid}...")
        info = get_music_info(rid)
        if info:
            results.append(info)
            print(f"  {info['title']} - {info['artist']}")
            print(f"  music_url: {info['music_url']}")
        time.sleep(0.5)

    # Save results
    output_dir = os.path.join(os.path.dirname(__file__), 'data', 'songs')
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, 'higequ_riyu_songs.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(results)} songs to {output_file}")

    # Summary
    quark_links = [r for r in results if 'quark' in r['music_url']]
    print(f"\n夸克网盘链接: {len(quark_links)}/{len(results)}")
    for r in results[:5]:
        print(f"  {r['title']} -> {r['music_url']}")

if __name__ == '__main__':
    main()
