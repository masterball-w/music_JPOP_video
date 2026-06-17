"""
Lyrics Scraper Module
=====================
Scrapes Japanese lyrics from various online sources.
Supports: Uta-Net, 歌詞ナビ (KashiNavi), UtaMap.
"""

import json
import os
import re
import time
import random
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()


class LyricsScraper:
    """Scrape lyrics from Japanese lyrics websites."""

    # Search URL templates
    SEARCH_URLS = {
        "uta_net": "https://www.uta-net.com/search/?Aselect=2&Keyword={query}&Bselect=4",
        "kashinavi": "https://kashinavi.com/search.php?kashi={query}",
        "utamap": "https://www.utamap.com/searchkasi.php?searchname=title&word={query}",
    }

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }

    def __init__(self, config: dict):
        self.config = config
        self.lyrics_cfg = config.get("lyrics", {})
        self.delay = self.lyrics_cfg.get("request_delay", 2.0)
        self.sources = self.lyrics_cfg.get("sources", ["uta_net"])
        self.data_dir = Path(config["paths"]["data_dir"]) / "lyrics"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _polite_delay(self):
        """Add random delay between requests."""
        time.sleep(self.delay + random.uniform(0.5, 1.5))

    def _safe_request(self, url: str, encoding: str = None) -> Optional[requests.Response]:
        """Make a safe HTTP request with error handling."""
        try:
            self._polite_delay()
            resp = self.session.get(url, timeout=15)
            if encoding:
                resp.encoding = encoding
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            console.print(f"  [red]Request failed: {e}[/red]")
            return None

    # ========== Uta-Net ==========

    def _search_uta_net(self, title: str, artist: str) -> Optional[str]:
        """Search Uta-Net for a song and return the lyrics page URL."""
        query = quote(f"{title} {artist}")
        url = self.SEARCH_URLS["uta_net"].format(query=query)
        resp = self._safe_request(url)
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        # Find first result link
        results = soup.select("td.side a[href*='/song/']")
        for link in results:
            href = link.get("href", "")
            if href and "/song/" in href:
                # Verify title matches approximately
                text = link.get_text(strip=True)
                if any(c in text for c in title[:3]):
                    return urljoin("https://www.uta-net.com", href)

        # Fallback: first result
        if results:
            href = results[0].get("href", "")
            return urljoin("https://www.uta-net.com", href)
        return None

    def _scrape_uta_net(self, url: str) -> Optional[dict]:
        """Scrape lyrics from a Uta-Net song page."""
        # Uta-Net loads lyrics via AJAX; construct the kashi URL
        match = re.search(r"/song/(\d+)/", url)
        if not match:
            return None

        song_id = match.group(1)
        kashi_url = f"https://www.uta-net.com/user/phplib/svg/showkashi.php?ID={song_id}&width=600&height=400&fontsize=14"

        resp = self._safe_request(kashi_url)
        if not resp:
            # Fallback: try the direct song page
            resp = self._safe_request(url)
            if not resp:
                return None
            soup = BeautifulSoup(resp.text, "lxml")
            # Look for lyrics in itemprop
            lyrics_div = soup.select_one("[itemprop='text']")
            if lyrics_div:
                raw_text = lyrics_div.get_text(separator="\n", strip=True)
                return {"raw": raw_text, "source": "uta_net", "url": url}

        # Parse SVG-based lyrics
        soup = BeautifulSoup(resp.text, "lxml")
        texts = soup.find_all("text")
        if texts:
            lines = [t.get_text(strip=True) for t in texts if t.get_text(strip=True)]
            raw_text = "\n".join(lines)
            return {"raw": raw_text, "source": "uta_net", "url": url}

        # Try plain text from response
        raw_text = resp.text.strip()
        if raw_text and len(raw_text) > 20:
            # Remove HTML tags
            clean = BeautifulSoup(raw_text, "lxml").get_text(separator="\n", strip=True)
            return {"raw": clean, "source": "uta_net", "url": url}

        return None

    # ========== KashiNavi ==========

    def _search_kashinavi(self, title: str, artist: str) -> Optional[str]:
        """Search KashiNavi for a song."""
        query = quote(f"{title}")
        url = self.SEARCH_URLS["kashinavi"].format(query=query)
        resp = self._safe_request(url)
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        results = soup.select("a[href*='/kashi/']")
        for link in results:
            href = link.get("href", "")
            if href and "/kashi/" in href:
                return urljoin("https://kashinavi.com", href)
        return None

    def _scrape_kashinavi(self, url: str) -> Optional[dict]:
        """Scrape lyrics from KashiNavi."""
        resp = self._safe_request(url, encoding="utf-8")
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        # KashiNavi uses div.kashi_view
        lyrics_div = soup.select_one("div.kashi_view") or soup.select_one("div#kashi_area")
        if lyrics_div:
            raw_text = lyrics_div.get_text(separator="\n", strip=True)
            return {"raw": raw_text, "source": "kashinavi", "url": url}
        return None

    # ========== UtaMap ==========

    def _search_utamap(self, title: str, artist: str) -> Optional[str]:
        """Search UtaMap for a song."""
        query = quote(title)
        url = self.SEARCH_URLS["utamap"].format(query=query)
        resp = self._safe_request(url, encoding="EUC-JP")
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        results = soup.select("a[href*='/lyrics/']")
        for link in results:
            href = link.get("href", "")
            if href and "/lyrics/" in href:
                return urljoin("https://www.utamap.com", href)
        return None

    def _scrape_utamap(self, url: str) -> Optional[dict]:
        """Scrape lyrics from UtaMap."""
        resp = self._safe_request(url, encoding="EUC-JP")
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        lyrics_div = soup.select_one("div.box_lyric") or soup.select_one("span.lyric_word")
        if lyrics_div:
            raw_text = lyrics_div.get_text(separator="\n", strip=True)
            return {"raw": raw_text, "source": "utamap", "url": url}
        return None

    # ========== Main Methods ==========

    def search_and_scrape(self, title: str, artist: str, song_id: str = "") -> Optional[dict]:
        """
        Try each configured source to find and scrape lyrics.
        Returns dict with 'raw' lyrics text, 'source', and 'url'.
        """
        console.print(f"\n  Searching: [cyan]{title}[/cyan] by [green]{artist}[/green]")

        for source in self.sources:
            try:
                # Search
                search_fn = getattr(self, f"_search_{source}", None)
                scrape_fn = getattr(self, f"_scrape_{source}", None)
                if not search_fn or not scrape_fn:
                    continue

                console.print(f"    Trying {source}...", end=" ")
                url = search_fn(title, artist)
                if not url:
                    console.print("[dim]not found[/dim]")
                    continue

                console.print(f"found!")
                # Scrape
                result = scrape_fn(url)
                if result:
                    # Add metadata
                    result["title"] = title
                    result["artist"] = artist
                    result["song_id"] = song_id
                    console.print(f"    [green]Lyrics obtained from {source}[/green] ({len(result['raw'])} chars)")
                    return result
                else:
                    console.print("    [yellow]scraping failed[/yellow]")

            except Exception as e:
                console.print(f"    [red]Error with {source}: {e}[/red]")

        console.print(f"  [red]Could not fetch lyrics for '{title}' from any source[/red]")
        return None

    def save_lyrics(self, lyrics_data: dict, filename: str) -> Path:
        """Save lyrics to a JSON file."""
        output_path = self.data_dir / f"{filename}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(lyrics_data, f, ensure_ascii=False, indent=2)
        return output_path

    def scrape_batch(self, songs: list[dict]) -> list[dict]:
        """Scrape lyrics for a batch of songs."""
        results = []
        total = len(songs)

        for i, song in enumerate(songs, 1):
            console.print(f"\n[{i}/{total}] ", end="")

            # Check if already cached
            safe_id = re.sub(r'[^\w\-]', '_', song["id"])
            cache_path = self.data_dir / f"{safe_id}.json"
            if cache_path.exists():
                console.print(f"[dim]Cached: {song['title']}[/dim]")
                with open(cache_path, "r", encoding="utf-8") as f:
                    results.append(json.load(f))
                continue

            lyrics = self.search_and_scrape(
                title=song["title"],
                artist=song["artist"],
                song_id=song["id"],
            )

            if lyrics:
                self.save_lyrics(lyrics, safe_id)
                results.append(lyrics)

        console.print(f"\n[green]Lyrics obtained: {len(results)}/{total}[/green]")
        return results

    def load_local_lyrics(self, text: str, title: str = "", artist: str = "") -> dict:
        """Load lyrics from a local text string (manual input)."""
        return {
            "raw": text.strip(),
            "title": title,
            "artist": artist,
            "source": "local",
            "url": "",
        }

    def load_lrc_file(self, lrc_path: str) -> Optional[dict]:
        """
        Parse an LRC file (with timestamps) into structured lyrics.
        Format: [mm:ss.xx] lyrics line
        Automatically merges Chinese translation lines with their Japanese counterparts.
        """
        path = Path(lrc_path)
        if not path.exists():
            console.print(f"[red]LRC file not found: {lrc_path}[/red]")
            return None

        # Phase 1: read all timed lines
        timed_lines = []
        metadata = {}
        lrc_pattern = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\]\s*(.*)')
        meta_pattern = re.compile(r'\[([a-zA-Z#]+):(.*)\]')

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                lrc_match = lrc_pattern.match(line)
                if lrc_match:
                    minutes = int(lrc_match.group(1))
                    seconds = int(lrc_match.group(2))
                    ms_str = lrc_match.group(3)
                    ms = int(ms_str) if len(ms_str) == 3 else int(ms_str) * 10
                    text = lrc_match.group(4).strip()
                    time_s = minutes * 60 + seconds + ms / 1000.0
                    if text:
                        timed_lines.append({
                            "start": round(time_s, 3),
                            "text": text,
                        })
                else:
                    meta_match = meta_pattern.match(line)
                    if meta_match:
                        metadata[meta_match.group(1)] = meta_match.group(2).strip()

        if not timed_lines:
            return None

        # Phase 2: merge Chinese translations into Japanese lines
        # Chinese translation lines follow their Japanese counterpart
        # but share the timestamp with the NEXT Japanese line.
        # Strategy: attach each Chinese line to the Japanese line before it.
        def _is_chinese(t):
            # Contains kana → Japanese
            if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', t):
                return False
            # Mostly CJK → Chinese
            cjk = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', t)
            return len(cjk) / max(len(t), 1) > 0.3

        lines = []
        i = 0
        while i < len(timed_lines):
            current = timed_lines[i]
            text = current["text"]

            if text.startswith(('词：', '曲：', '编曲', 'TME', '翻译', '原唱')):
                i += 1
                continue

            if _is_chinese(text):
                lines.append({"start": current["start"], "end": None, "text": text, "translation": None})
                i += 1
                continue

            translation = None
            if i + 1 < len(timed_lines):
                next_line = timed_lines[i + 1]
                if _is_chinese(next_line["text"]):
                    translation = next_line["text"]
                    i += 1

            lines.append({"start": current["start"], "end": None, "text": text, "translation": translation})
            i += 1

        # Phase 3: fill end times
        for i in range(len(lines) - 1):
            lines[i]["end"] = lines[i + 1]["start"]
        lines[-1]["end"] = lines[-1]["start"] + 5.0

        return {
            "lines": lines,
            "metadata": metadata,
            "title": metadata.get("ti", ""),
            "artist": metadata.get("ar", ""),
            "source": "lrc_file",
            "raw": "\n".join(l["text"] for l in lines),
        }
