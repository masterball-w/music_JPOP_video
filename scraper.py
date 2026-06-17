#!/usr/bin/env python3
"""
Scrape Japanese songs from higequ.com/riyu/
"""
import requests
import json
import re
import os
from bs4 import BeautifulSoup
import time

def scrape_page(page_num):
    """Scrape a single page and return list of songs"""
    if page_num == 1:
        url = "https://higequ.com/riyu/"
    else:
        url = f"https://higequ.com/riyu/?p={page_num}"

    print(f"Fetching page {page_num}: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'

        if response.status_code != 200:
            print(f"  Page {page_num} returned status {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all song entries - looking for the pattern in the HTML
        songs = []

        # Try to find song containers - adjust selectors based on actual HTML structure
        # Looking for numbered items with title, artist, album
        text = soup.get_text()

        # Pattern: number, title, artist, album info
        lines = text.split('\n')
        lines = [line.strip() for line in lines if line.strip()]

        i = 0
        while i < len(lines):
            # Look for a number
            if lines[i].isdigit():
                num = int(lines[i])
                if i + 2 < len(lines):
                    title = lines[i + 1]
                    artist = lines[i + 2]
                    album = ""
                    if i + 3 < len(lines) and lines[i + 3].startswith('专辑:'):
                        album = lines[i + 3].replace('专辑:', '').strip()
                        songs.append({
                            'number': num,
                            'title': title,
                            'artist': artist,
                            'album': album
                        })
                        i += 4
                        continue
            i += 1

        print(f"  Found {len(songs)} songs on page {page_num}")
        return songs

    except Exception as e:
        print(f"  Error scraping page {page_num}: {e}")
        return []

def main():
    all_songs = []

    # Scrape pages 1-4 (page 5 is empty based on testing)
    for page in range(1, 5):
        songs = scrape_page(page)
        if songs:
            all_songs.extend(songs)
        time.sleep(1)  # Be polite, don't hammer the server

    print(f"\nTotal songs scraped: {len(all_songs)}")

    # Save to JSON
    output_dir = os.path.join(os.path.dirname(__file__), 'data', 'songs')
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, 'higequ_riyu_songs.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_songs, f, ensure_ascii=False, indent=2)

    print(f"Saved to: {output_file}")

    # Also save individual song files
    for song in all_songs:
        # Create a safe filename
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', song['title'])
        safe_artist = re.sub(r'[<>:"/\\|?*]', '_', song['artist'])
        filename = f"{safe_artist}_{safe_title}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(song, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(all_songs)} individual song files")

if __name__ == '__main__':
    main()
