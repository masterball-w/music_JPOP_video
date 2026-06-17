#!/usr/bin/env python3
"""Inspect the HTML structure of the website to find audio links"""
import requests
from bs4 import BeautifulSoup

url = "https://higequ.com/riyu/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, headers=headers, timeout=30)
response.encoding = 'utf-8'
soup = BeautifulSoup(response.text, 'html.parser')

# Find all links
links = soup.find_all('a', href=True)
print(f"Total links: {len(links)}")
print("\n--- First 30 links ---")
for i, link in enumerate(links[:30]):
    print(f"{i}: href={link['href']}  text={link.get_text(strip=True)[:60]}")

# Find audio elements
audios = soup.find_all('audio')
print(f"\n--- Audio elements: {len(audios)} ---")
for audio in audios[:5]:
    print(audio)
    sources = audio.find_all('source')
    for src in sources:
        print(f"  source: {src.get('src')}")

# Find elements with audio-related classes or data attributes
print("\n--- Looking for audio-related elements ---")
for tag in soup.find_all(attrs={'data-src': True}):
    src = tag.get('data-src')
    if src and ('.mp3' in src or 'audio' in src):
        print(f"  data-src: {src}  tag: {tag.name}")

# Look for any mp3 links
print("\n--- MP3 references ---")
import re
mp3_pattern = re.compile(r'https?://[^\s"\']+\.mp3[^\s"\']*')
mp3_urls = mp3_pattern.findall(response.text)
for u in mp3_urls[:10]:
    print(f"  {u}")

# Look for song detail page links
print("\n--- Song detail page links (riyu/) ---")
riyu_links = [l for l in links if '/riyu/' in l['href'] and l['href'] != '/riyu/']
for l in riyu_links[:10]:
    print(f"  {l['href']}  text={l.get_text(strip=True)[:60]}")

# Print a portion of the HTML around the first song entry
print("\n--- HTML structure around songs ---")
html = response.text
# Find first song-related section
idx = html.find('NIGHT DANCER')
if idx > 0:
    print(html[max(0,idx-500):idx+500])
