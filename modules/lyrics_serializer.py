"""
Lyrics Serializer Module
========================
Converts raw lyrics text into structured JSON with time estimates.
Handles: line splitting, section detection, time estimation.
"""

import json
import re
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


class LyricsSerializer:
    """Serialize raw lyrics into time-stamped JSON format."""

    # Section header patterns
    SECTION_PATTERNS = [
        re.compile(r'^(?:【|\[|\()([^\]】\)]+)(?:\]|\]|】|\))$'),  # [Verse], (Chorus), etc.
        re.compile(r'^(Aメロ|Bメロ|サビ|Cメロ|Dメロ|間奏|イントロ|アウトロ|Bridge|Chorus|Verse|Pre-Chorus|Hook).*', re.IGNORECASE),
        re.compile(r'^-{2,}$'),  # Separator lines
    ]

    def __init__(self, config: dict):
        self.config = config
        self.data_dir = Path(config["paths"]["data_dir"])
        self.output_dir = self.data_dir / "serialized"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def detect_section(self, line: str) -> Optional[str]:
        """Detect if a line is a section header."""
        line = line.strip()
        for pattern in self.SECTION_PATTERNS:
            if pattern.match(line):
                return line
        return None

    def is_empty_or_separator(self, line: str) -> bool:
        """Check if a line is empty or a separator."""
        stripped = line.strip()
        if not stripped:
            return True
        if re.match(r'^[-=_~*]{2,}$', stripped):
            return True
        if re.match(r'^♪+$', stripped):
            return True
        return False

    def estimate_timing(self, lines: list[dict], total_duration: float = None, avg_chars_per_sec: float = 3.5) -> list[dict]:
        """
        Estimate timing for lyrics lines based on character count.
        Japanese songs average ~3-4 chars per second for singing.
        
        Args:
            lines: List of line dicts with 'text' field
            total_duration: Total song duration in seconds (optional)
            avg_chars_per_sec: Average characters sung per second
        """
        if not lines:
            return lines

        # Calculate total characters
        total_chars = sum(len(line["text"]) for line in lines)
        if total_chars == 0:
            return lines

        # If total duration is known, scale accordingly
        if total_duration:
            estimated_singing_time = total_duration * 0.75  # 75% of song is singing
            avg_chars_per_sec = total_chars / estimated_singing_time if estimated_singing_time > 0 else 3.5

        # Assign times based on character count
        current_time = 2.0  # Start with 2 second intro
        for i, line in enumerate(lines):
            char_count = len(line["text"])
            # Duration proportional to character count
            duration = max(1.5, char_count / avg_chars_per_sec)
            # Add small gap between lines
            gap = 0.3 if i < len(lines) - 1 else 0

            line["start"] = round(current_time, 3)
            line["end"] = round(current_time + duration, 3)
            current_time = line["end"] + gap

        return lines

    def parse_raw_lyrics(self, raw_text: str) -> list[dict]:
        """
        Parse raw lyrics text into structured lines.
        Returns list of line dicts.
        """
        lines = []
        current_section = "Intro"
        line_index = 0

        for raw_line in raw_text.split("\n"):
            raw_line = raw_line.strip()

            # Skip empty lines and separators
            if self.is_empty_or_separator(raw_line):
                continue

            # Check for section headers
            section = self.detect_section(raw_line)
            if section:
                current_section = section
                continue

            # Regular lyrics line
            lines.append({
                "index": line_index,
                "section": current_section,
                "text": raw_line,
                "start": None,
                "end": None,
                "romaji": None,       # To be filled later
                "translation": None,   # To be filled later
            })
            line_index += 1

        return lines

    # Comprehensive kana-to-romaji mapping (shared across instances)
    _KANA_MAP = {}

    @classmethod
    def _init_kana_map(cls):
        """Initialize the kana-to-romaji mapping table."""
        if cls._KANA_MAP:
            return

        hiragana_map = {
            'あ': 'a', 'い': 'i', 'う': 'u', 'え': 'e', 'お': 'o',
            'か': 'ka', 'き': 'ki', 'く': 'ku', 'け': 'ke', 'こ': 'ko',
            'さ': 'sa', 'し': 'shi', 'す': 'su', 'せ': 'se', 'そ': 'so',
            'た': 'ta', 'ち': 'chi', 'つ': 'tsu', 'て': 'te', 'と': 'to',
            'な': 'na', 'に': 'ni', 'ぬ': 'nu', 'ね': 'ne', 'の': 'no',
            'は': 'ha', 'ひ': 'hi', 'ふ': 'fu', 'へ': 'he', 'ほ': 'ho',
            'ま': 'ma', 'み': 'mi', 'む': 'mu', 'め': 'me', 'も': 'mo',
            'や': 'ya', 'ゆ': 'yu', 'よ': 'yo',
            'ら': 'ra', 'り': 'ri', 'る': 'ru', 'れ': 're', 'ろ': 'ro',
            'わ': 'wa', 'を': 'wo', 'ん': 'n',
            'が': 'ga', 'ぎ': 'gi', 'ぐ': 'gu', 'げ': 'ge', 'ご': 'go',
            'ざ': 'za', 'じ': 'ji', 'ず': 'zu', 'ぜ': 'ze', 'ぞ': 'zo',
            'だ': 'da', 'ぢ': 'di', 'づ': 'du', 'で': 'de', 'ど': 'do',
            'ば': 'ba', 'び': 'bi', 'ぶ': 'bu', 'べ': 'be', 'ぼ': 'bo',
            'ぱ': 'pa', 'ぴ': 'pi', 'ぷ': 'pu', 'ぺ': 'pe', 'ぽ': 'po',
            'きゃ': 'kya', 'きゅ': 'kyu', 'きょ': 'kyo',
            'しゃ': 'sha', 'しゅ': 'shu', 'しょ': 'sho',
            'ちゃ': 'cha', 'ちゅ': 'chu', 'ちょ': 'cho',
            'にゃ': 'nya', 'にゅ': 'nyu', 'にょ': 'nyo',
            'ひゃ': 'hya', 'ひゅ': 'hyu', 'ひょ': 'hyo',
            'みゃ': 'mya', 'みゅ': 'myu', 'みょ': 'myo',
            'りゃ': 'rya', 'りゅ': 'ryu', 'りょ': 'ryo',
            'ぎゃ': 'gya', 'ぎゅ': 'gyu', 'ぎょ': 'gyo',
            'じゃ': 'ja', 'じゅ': 'ju', 'じょ': 'jo',
            'びゃ': 'bya', 'びゅ': 'byu', 'びょ': 'byo',
            'ぴゃ': 'pya', 'ぴゅ': 'pyu', 'ぴょ': 'pyo',
            'ぁ': 'a', 'ぃ': 'i', 'ぅ': 'u', 'ぇ': 'e', 'ぉ': 'o',
        }
        katakana_map = {}
        for h, r in hiragana_map.items():
            # Convert hiragana key to katakana
            k = "".join(chr(ord(c) + 0x60) for c in h)
            katakana_map[k] = r
        # Special katakana-only entries
        katakana_map['ッ'] = ''  # small tsu handled separately
        katakana_map['ー'] = ''  # long vowel mark handled separately

        cls._KANA_MAP = {**katakana_map, **hiragana_map}
        # Sort by key length (longest first for greedy matching)
        cls._KANA_SORTED = sorted(cls._KANA_MAP.items(), key=lambda x: -len(x[0]))

    def _kana_to_romaji(self, kana_str: str) -> str:
        """Convert a kana string to romaji."""
        self._init_kana_map()
        result = kana_str

        # Handle small tsu (っ/ッ) - doubles the following consonant
        result = re.sub(r'[っッ](.)', lambda m: m.group(1), result)

        # Handle long vowel mark (ー) by doubling the previous vowel
        result = re.sub(r'ー', '', result)

        # Temporarily replace standalone ん/ン with a placeholder to avoid
        # confusion with な/に/ぬ/ね/の etc.
        result = result.replace('ん', '\x01').replace('ン', '\x01')

        # Convert kana to romaji (longest match first)
        for kana, roma in self._KANA_SORTED:
            if kana not in ('ん', 'ン'):  # skip, already replaced
                result = result.replace(kana, roma)

        # Replace placeholder with 'n'
        result = result.replace('\x01', 'N')

        # Handle N before vowels: add apostrophe only when N is followed by
        # a vowel (to distinguish from na/ni/nu/ne/no)
        result = re.sub(r"N([aeiou])", r"n'\1", result)
        # N before consonants or end of string → just 'n'
        result = result.replace('N', 'n')

        return result

    def to_romaji(self, text: str) -> str:
        """
        Convert Japanese text to romaji with proper word spacing.
        Uses Janome tokenization to identify word boundaries, then converts
        each word's reading to romaji individually.
        """
        try:
            from janome.tokenizer import Tokenizer
            t = Tokenizer()
            romaji_words = []

            for token in t.tokenize(text):
                surface = token.surface
                pos = token.part_of_speech.split(',')[0] if token.part_of_speech else ''

                # Skip punctuation and whitespace
                if surface in ' \u3000' or pos in ('記号', 'BOS/EOS'):
                    # But keep certain punctuation as spaces
                    if surface in ' 、。！？「」『』（）()':
                        romaji_words.append('')
                    continue

                # Get the reading (katakana) from Janome
                reading = token.reading if (token.reading and token.reading != '*') else surface

                # Convert this word's reading to romaji
                roma = self._kana_to_romaji(reading)
                if roma:
                    romaji_words.append(roma)

            # Join with spaces between words
            result = " ".join(w for w in romaji_words if w)
            # Clean up multiple spaces
            result = re.sub(r'\s+', ' ', result).strip()

            return result

        except ImportError:
            return ""

    def serialize(self, lyrics_data: dict, total_duration: float = None) -> dict:
        """
        Serialize lyrics into structured JSON with timestamps.
        
        Args:
            lyrics_data: Dict from LyricsScraper with 'raw' text
            total_duration: Total song duration in seconds (optional)
            
        Returns:
            Dict with structured, time-stamped lyrics
        """
        raw_text = lyrics_data.get("raw", "")
        if not raw_text:
            return lyrics_data

        # Parse into lines
        lines = self.parse_raw_lyrics(raw_text)

        if not lines:
            console.print("[yellow]No lyrics lines found in raw text[/yellow]")
            return lyrics_data

        # Estimate timing
        lines = self.estimate_timing(lines, total_duration)

        # Add romaji readings
        for line in lines:
            line["romaji"] = self.to_romaji(line["text"])

        # Build output structure
        output = {
            "title": lyrics_data.get("title", ""),
            "artist": lyrics_data.get("artist", ""),
            "song_id": lyrics_data.get("song_id", ""),
            "source": lyrics_data.get("source", ""),
            "total_duration": total_duration,
            "total_lines": len(lines),
            "sections": {},
            "lines": lines,
        }

        # Group by sections
        for line in lines:
            section = line.get("section", "Unknown")
            if section not in output["sections"]:
                output["sections"][section] = []
            output["sections"][section].append(line["index"])

        return output

    def serialize_batch(self, lyrics_list: list[dict], durations: dict = None) -> list[dict]:
        """
        Serialize a batch of lyrics.
        
        Args:
            lyrics_list: List of lyrics dicts from scraper
            durations: Dict mapping song_id -> duration_seconds (optional)
        """
        results = []
        durations = durations or {}

        console.print(f"\n[bold cyan]=== Serializing Lyrics ===[/bold cyan]")

        for i, lyrics in enumerate(lyrics_list, 1):
            title = lyrics.get("title", "Unknown")
            song_id = lyrics.get("song_id", f"song_{i}")
            duration = durations.get(song_id)

            console.print(f"  [{i}/{len(lyrics_list)}] {title}...", end=" ")

            serialized = self.serialize(lyrics, total_duration=duration)

            if serialized.get("lines"):
                # Save to file
                safe_id = re.sub(r'[^\w\-]', '_', song_id)
                output_path = self.output_dir / f"{safe_id}.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(serialized, f, ensure_ascii=False, indent=2)

                console.print(f"[green]{serialized['total_lines']} lines[/green]")
                results.append(serialized)
            else:
                console.print("[yellow]skipped (no lines)[/yellow]")

        console.print(f"\n[green]Serialized: {len(results)}/{len(lyrics_list)} songs[/green]")
        return results

    def load_serialized(self, song_id: str) -> Optional[dict]:
        """Load a previously serialized lyrics file."""
        safe_id = re.sub(r'[^\w\-]', '_', song_id)
        path = self.output_dir / f"{safe_id}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
