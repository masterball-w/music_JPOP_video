#!/usr/bin/env python3
"""Inspect the full HTML to find JS that handles audio playback"""
import requests
import re

url = "https://higequ.com/riyu/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, headers=headers, timeout=30)
response.encoding = 'utf-8'
html = response.text

# Extract all data-rid values
rids = re.findall(r'data-rid="(\d+)"', html)
print(f"Found {len(rids)} data-rid values: {rids[:5]}")

# Extract all script tags content
script_pattern = re.compile(r'<script[^>]*>(.*?)</script>', re.DOTALL)
scripts = script_pattern.findall(html)
print(f"\nFound {len(scripts)} script blocks")

# Look for audio/API related code in scripts
for i, script in enumerate(scripts):
    if any(kw in script.lower() for kw in ['audio', 'mp3', 'play', 'rid', 'api', 'fetch', 'ajax', 'music', 'song']):
        print(f"\n=== Script block {i} (length: {len(script)}) ===")
        print(script[:3000])
        if len(script) > 3000:
            print(f"... (truncated, total {len(script)} chars)")

# Also look for external JS files
js_files = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
print(f"\n--- External JS files ---")
for f in js_files:
    print(f"  {f}")
