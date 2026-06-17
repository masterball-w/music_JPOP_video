#!/usr/bin/env python3
"""Find where audio src is set in player page"""
import requests
import re

url = "https://higequ.com/player/234817642/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers, timeout=30)
response.encoding = 'utf-8'
html = response.text

# Find the main script block - look for audioElement assignment
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, flags=re.DOTALL)
for i, script in enumerate(scripts):
    if 'audioElement' in script or 'audio' in script.lower():
        # Print the beginning of the script to find audio src setup
        print(f"=== Script {i} (len={len(script)}) ===")
        # Find audioElement.src or audio src assignment
        src_matches = re.findall(r'(audio[^;]{0,200}(?:src|url)[^;]{0,200})', script, re.IGNORECASE)
        for m in src_matches:
            print(f"  SRC MATCH: {m[:300]}")

        # Also look for any URL patterns
        url_matches = re.findall(r'https?://[^\s"\'<>]+', script)
        print(f"\n  URLs in script:")
        for u in url_matches:
            print(f"    {u}")

        # Print first 2000 chars to see initialization
        print(f"\n  First 2000 chars:")
        print(script[:2000])

# Also look for modal.js content
print("\n\n=== Looking for modal.js ===")
modal_resp = requests.get("https://higequ.com/assets/js/modal.js", headers=headers, timeout=30)
print(f"Status: {modal_resp.status_code}")
print(modal_resp.text[:3000])
