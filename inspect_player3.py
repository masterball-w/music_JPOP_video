#!/usr/bin/env python3
"""Dump the full player page HTML to find audio source"""
import requests
import re

url = "https://higequ.com/player/234817642/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers, timeout=30)
response.encoding = 'utf-8'
html = response.text

# Find the audio element and surrounding context
idx = html.find('audio-element')
if idx > 0:
    print("=== Around audio-element ===")
    print(html[max(0,idx-200):idx+500])

# Find handleDownloadSong function fully
idx = html.find('handleDownloadSong')
if idx > 0:
    print("\n=== handleDownloadSong ===")
    print(html[max(0,idx-100):idx+1000])

# Find openShareModal
idx = html.find('openShareModal')
if idx > 0:
    print("\n=== openShareModal ===")
    print(html[max(0,idx-100):idx+1000])

# Look for any API endpoint patterns
api_patterns = re.findall(r'(?:fetch|axios|XMLHttpRequest|ajax|api|/api/|endpoint)[^\n]{0,300}', html, re.IGNORECASE)
print(f"\n=== API patterns ({len(api_patterns)}) ===")
for p in api_patterns:
    print(f"  {p[:200]}")

# Look for any hidden input or data attributes with URLs
hidden = re.findall(r'(?:value|data-[a-z]+|href|src)=["\']([^"\']*(?:http|//|/api)[^"\']*)["\']', html)
print(f"\n=== Hidden URLs ({len(hidden)}) ===")
for h in hidden:
    print(f"  {h}")

# Look for the script that sets audio src
print("\n=== Full main script ===")
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, flags=re.DOTALL)
for i, script in enumerate(scripts):
    if 'audioElement' in script:
        print(f"Script {i}, len={len(script)}")
        # Print the part where audioElement is used
        lines = script.split('\n')
        for j, line in enumerate(lines):
            if 'audio' in line.lower() or 'src' in line.lower() or 'play' in line.lower() or 'url' in line.lower() or 'download' in line.lower() or 'share' in line.lower() or 'open' in line.lower():
                print(f"  L{j}: {line.strip()}")
