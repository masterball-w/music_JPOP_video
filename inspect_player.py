#!/usr/bin/env python3
"""Inspect player page HTML to find audio URL"""
import requests
import re

url = "https://higequ.com/player/234817642/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, headers=headers, timeout=30)
response.encoding = 'utf-8'
html = response.text

# Find all script blocks
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, flags=re.DOTALL)
for i, script in enumerate(scripts):
    if any(kw in script.lower() for kw in ['audio', 'mp3', 'play', 'src', 'music', 'song', 'url', 'kuwo', 'source']):
        print(f"=== Script {i} (len={len(script)}) ===")
        print(script[:5000])
        print()

# Find audio tags
audios = re.findall(r'<audio[^>]*>.*?</audio>', html, re.DOTALL)
print(f"\n--- Audio tags: {len(audios)} ---")
for a in audios:
    print(a[:500])

# Find any URLs with mp3 or audio
mp3_urls = re.findall(r'https?://[^\s"\'<>]+\.mp3[^\s"\'<>]*', html)
print(f"\n--- MP3 URLs: {len(mp3_urls)} ---")
for u in mp3_urls:
    print(f"  {u}")

# Find any data attributes with URLs
data_urls = re.findall(r'data-[a-z]+=["\'](https?://[^"\']+)["\']', html)
print(f"\n--- Data URLs: {len(data_urls)} ---")
for u in data_urls:
    print(f"  {u}")

# Find external JS
js_files = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
print(f"\n--- External JS: {js_files} ---")
