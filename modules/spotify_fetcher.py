"""
Spotify Fetcher Module
======================
Fetches popular Japanese songs from Spotify using spotipy.
Falls back to a curated list if Spotify API is unavailable.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    HAS_SPOTIPY = True
except ImportError:
    HAS_SPOTIPY = False

from rich.console import Console
from rich.table import Table

console = Console()


class SpotifyFetcher:
    """Fetch popular Japanese songs from Spotify."""

    # Curated fallback list of popular Japanese songs
    FALLBACK_SONGS = [
        {"title": "Lemon", "artist": "米津玄師", "album": "Lemon", "year": 2018},
        {"title": "Pretender", "artist": "Official髭男dism", "album": "Traveler", "year": 2019},
        {"title": "夜に駆ける", "artist": "YOASOBI", "album": "THE BOOK", "year": 2020},
        {"title": "怪物", "artist": "YOASOBI", "album": "THE BOOK 2", "year": 2021},
        {"title": "ドライフラワー", "artist": "優里", "album": "壱", "year": 2020},
        {"title": "群青", "artist": "YOASOBI", "album": "THE BOOK", "year": 2020},
        {"title": "Subtitle", "artist": "Official髭男dism", "album": "Editorial", "year": 2022},
        {"title": "新時代", "artist": "Ado", "album": "ウタの歌 ONE PIECE FILM RED", "year": 2022},
        {"title": "アイドル", "artist": "YOASOBI", "album": "THE BOOK 3", "year": 2023},
        {"title": "KICK BACK", "artist": "米津玄師", "album": "KICK BACK", "year": 2022},
        {"title": "Blinding Sunrise", "artist": "YOASOBI", "album": "THE BOOK 3", "year": 2023},
        {"title": "Overdose", "artist": "なとり", "album": "Overdose", "year": 2022},
        {"title": "青のすみか", "artist": "キタニタツヤ", "album": "青のすみか", "year": 2023},
        {"title": "Specialz", "artist": "King Gnu", "album": "THE LAND", "year": 2023},
        {"title": "BOW AND ARROW", "artist": "米津玄師", "album": "BOW AND ARROW", "year": 2024},
        {"title": "唱", "artist": "Ado", "album": "唱", "year": 2023},
        {"title": "晩餐歌", "artist": "tuki.", "album": "晩餐歌", "year": 2023},
        {"title": "花", "artist": "back number", "album": "アンコール", "year": 2016},
        {"title": "前前前世", "artist": "RADWIMPS", "album": "君の名は。", "year": 2016},
        {"title": "スパークル", "artist": "RADWIMPS", "album": "君の名は。", "year": 2016},
        {"title": "打上花火", "artist": "DAOKO × 米津玄師", "album": "打上花火", "year": 2017},
        {"title": "感電", "artist": "米津玄師", "album": "STRAY SHEEP", "year": 2020},
        {"title": "裸の心", "artist": "あいみょん", "album": "裸の心", "year": 2020},
        {"title": "マリーゴールド", "artist": "あいみょん", "album": "瞬間的シックスセンス", "year": 2018},
        {"title": "炎", "artist": "LiSA", "album": "LEO-NiNE", "year": 2020},
        {"title": "紅蓮華", "artist": "LiSA", "album": "LEO-NiNE", "year": 2019},
        {"title": "残響散歌", "artist": "Aimer", "album": "残響散歌", "year": 2021},
        {"title": "朝が来る", "artist": "Aimer", "album": "朝が来る", "year": 2022},
        {"title": "W/X/Y", "artist": "tuki.", "album": "W/X/Y", "year": 2023},
        {"title": "ひめごと", "artist": "aiko", "album": "どうしたって伝えられないんだ", "year": 2023},
        {"title": "夏色えがおで1,2,Jump!", "artist": "μ's", "album": "Love Live!", "year": 2012},
        {"title": "うっせぇわ", "artist": "Ado", "album": "うっせぇわ", "year": 2020},
        {"title": "ギミチョコ!!", "artist": "BABYMETAL", "album": "BABYMETAL", "year": 2014},
        {"title": "Plastic Love", "artist": "竹内まりや", "album": "VARIETY", "year": 1984},
        {"title": "First Love", "artist": "宇多田ヒカル", "album": "First Love", "year": 1999},
        {"title": "Flavor Of Life", "artist": "宇多田ヒカル", "album": "ULTRA BLUE", "year": 2006},
        {"title": "CAN YOU CELEBRATE?", "artist": "安室奈美恵", "album": "CAN YOU CELEBRATE?", "year": 1997},
        {"title": "LOVEマシーン", "artist": "モーニング娘。", "album": "LOVEマシーン", "year": 1999},
        {"title": "世界に一つだけの花", "artist": "SMAP", "album": "SMAP 015/Drink! Smap!", "year": 2003},
        {"title": "ハナミズキ", "artist": "一青窈", "album": "ハナミズキ", "year": 2004},
        {"title": "secret base ～君がくれたもの～", "artist": "ZONE", "album": "secret base", "year": 2001},
        {"title": "小さな恋のうた", "artist": "MONGOL800", "album": "MESSAGE", "year": 2001},
        {"title": "天体観測", "artist": "BUMP OF CHICKEN", "album": "orbital period", "year": 2001},
        {"title": "チェリー", "artist": "スピッツ", "album": "インディゴ地平線", "year": 1996},
        {"title": " robocop", "artist": "BUMP OF CHICKEN", "album": "FLAME VEIN", "year": 1999},
        {"title": "粉雪", "artist": "レミオロメン", "album": "朝顔", "year": 2005},
        {"title": "3月9日", "artist": "レミオロメン", "album": "ether", "year": 2004},
        {"title": "ORION", "artist": "中島美嘉", "album": "VOICE", "year": 2008},
        {"title": "雪の華", "artist": "中島美嘉", "album": "LØVE", "year": 2003},
        {"title": "さくら", "artist": "森山直太朗", "album": "さくら", "year": 2003},
        {"title": "明日への扉", "artist": "I WiSH", "album": "明日への扉", "year": 2003},
        {"title": "涙そうそう", "artist": "夏川りみ", "album": "てぃだ〜太陽・風ぬ想い〜", "year": 2001},
        {"title": "栄光の架橋", "artist": "ゆず", "album": "栄光の架橋", "year": 2004},
        {"title": "桜", "artist": "コブクロ", "album": "桜", "year": 2005},
        {"title": "虹", "artist": "菅田将暉", "album": "虹", "year": 2020},
        {"title": "まちがいさがし", "artist": "菅田将暉", "album": "まちがいさがし", "year": 2019},
        {"title": "宿命", "artist": "Official髭男dism", "album": "Traveler", "year": 2019},
        {"title": "I LOVE...", "artist": "Official髭男dism", "album": "Traveler", "year": 2020},
        {"title": "ミックスナッツ", "artist": "Official髭男dism", "album": "ミックスナッツ", "year": 2022},
        {"title": "Bling-Bang-Bang-Born", "artist": "Creepy Nuts", "album": "Bling-Bang-Bang-Born", "year": 2024},
        {"title": "死ぬな!", "artist": "Creepy Nuts", "album": "Case", "year": 2021},
        {"title": "悪魔の踊り方", "artist": "キタニタツヤ", "album": "悪魔の踊り方", "year": 2022},
        {"title": "ちゅ、多様性。", "artist": "あの", "album": "ちゅ、多様性。", "year": 2022},
        {"title": "Que Sera Sera", "artist": "Mrs. GREEN APPLE", "album": "Que Sera Sera", "year": 2023},
        {"title": "ケセラセラ", "artist": "Mrs. GREEN APPLE", "album": "ケセラセラ", "year": 2023},
        {"title": "魔法", "artist": "優里", "album": "魔法", "year": 2023},
        {"title": "ビリミリ", "artist": "Ado", "album": "ビリミリ", "year": 2024},
        {"title": "GHOST", "artist": "星街すいせい", "album": "GHOST", "year": 2024},
        {"title": "ライラック", "artist": "Mrs. GREEN APPLE", "album": "ライラック", "year": 2024},
        {"title": "Apt.", "artist": "ROSE & Bruno Mars", "album": "Apt.", "year": 2024},
        {"title": "コメディー", "artist": "星野源", "album": "コメディー", "year": 2024},
        {"title": "きらり", "artist": "藤井風", "album": "HELP EVER HURT NEVER", "year": 2021},
        {"title": "死神", "artist": "藤井風", "album": "LOVE ALL SERVE ALL", "year": 2022},
        {"title": "花", "artist": "藤井風", "album": "HELP EVER HURT NEVER", "year": 2020},
        {"title": "なんでもないよ、", "artist": "マカロニえんぴつ", "album": "なんでもないよ、", "year": 2021},
        {"title": "怪獣の花唄", "artist": "Vaundy", "album": "strobo", "year": 2020},
        {"title": "東京フラッシュ", "artist": "Vaundy", "album": "strobo", "year": 2020},
        {"title": "しわあわせ", "artist": "Vaundy", "album": "strobo", "year": 2020},
        {"title": "裸の勇者", "artist": "Vaundy", "album": "裸の勇者", "year": 2022},
        {"title": "瞳", "artist": "Omoinotake", "album": "瞳", "year": 2024},
        {"title": "幾億光年", "artist": "Omoinotake", "album": "幾億光年", "year": 2024},
        {"title": "BURN", "artist": "MAPA", "album": "BURN", "year": 2024},
        {"title": "SLEEPLESS", "artist": "imase", "album": "POP CUBE", "year": 2022},
        {"title": "NIGHT DANCER", "artist": "imase", "album": "NIGHT DANCER", "year": 2023},
        {"title": "PINK BLOOD", "artist": "宇多田ヒカル", "album": "BAD MODE", "year": 2021},
        {"title": "One Last Kiss", "artist": "宇多田ヒカル", "album": "One Last Kiss", "year": 2021},
        {"title": "Mela!", "artist": "緑黄色社会", "album": "Mela!", "year": 2024},
        {"title": "キャラクター", "artist": "星野源", "album": "POP VIRUS", "year": 2018},
        {"title": "恋", "artist": "星野源", "album": "YELLOW DANCER", "year": 2016},
        {"title": "Comedy", "artist": "星野源", "album": "コメディー", "year": 2024},
        {"title": "ピースサイン", "artist": "米津玄師", "album": "BOOTLEG", "year": 2017},
        {"title": "Flamingo", "artist": "米津玄師", "album": "STRAY SHEEP", "year": 2018},
        {"title": "海の幽霊", "artist": "米津玄師", "album": "海の幽霊", "year": 2019},
        {"title": "パプリカ", "artist": "米津玄師/Foorin", "album": "パプリカ", "year": 2018},
        {"title": "馬と鹿", "artist": "米津玄師", "album": "STRAY SHEEP", "year": 2019},
        {"title": "カムパネルラ", "artist": "米津玄師", "album": "STRAY SHEEP", "year": 2020},
        {"title": "Alice", "artist": "米津玄師", "album": "LOST CORNER", "year": 2024},
    ]

    def __init__(self, config: dict):
        self.config = config
        self.spotify_cfg = config.get("spotify", {})
        self.max_songs = self.spotify_cfg.get("max_songs", 100)
        self.data_dir = Path(config["paths"]["data_dir"]) / "songs"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sp = None
        self._init_spotify()

    def _init_spotify(self):
        """Initialize Spotify API client."""
        if not HAS_SPOTIPY:
            console.print("[yellow]spotipy not installed, using fallback song list[/yellow]")
            return

        client_id = self.spotify_cfg.get("client_id", "")
        client_secret = self.spotify_cfg.get("client_secret", "")

        if client_id == "YOUR_SPOTIFY_CLIENT_ID" or not client_id:
            console.print("[yellow]Spotify API credentials not configured, using fallback list[/yellow]")
            return

        try:
            auth_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret,
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            console.print("[green]Spotify API connected successfully[/green]")
        except Exception as e:
            console.print(f"[yellow]Spotify API connection failed: {e}, using fallback[/yellow]")
            self.sp = None

    def fetch_from_spotify(self) -> list[dict]:
        """Fetch songs from Spotify playlists."""
        if not self.sp:
            return []

        songs = []
        seen_ids = set()
        playlist_ids = self.spotify_cfg.get("playlist_ids", [])

        for playlist_id in playlist_ids:
            try:
                # Extract ID from URI if needed
                if ":" in playlist_id:
                    playlist_id = playlist_id.split(":")[-1]
                if "/" in playlist_id:
                    playlist_id = playlist_id.split("/")[-1]

                results = self.sp.playlist_tracks(playlist_id, limit=100)
                for item in results.get("items", []):
                    track = item.get("track", {})
                    if not track or track["id"] in seen_ids:
                        continue
                    seen_ids.add(track["id"])

                    songs.append({
                        "id": track["id"],
                        "title": track["name"],
                        "artist": ", ".join(a["name"] for a in track["artists"]),
                        "album": track["album"]["name"],
                        "year": int(track["album"]["release_date"][:4]) if track["album"].get("release_date") else None,
                        "duration_ms": track.get("duration_ms", 0),
                        "spotify_url": track.get("external_urls", {}).get("spotify", ""),
                        "preview_url": track.get("preview_url"),
                        "popularity": track.get("popularity", 0),
                    })
                console.print(f"  Fetched {len(results.get('items', []))} tracks from playlist {playlist_id}")
            except Exception as e:
                console.print(f"[red]Error fetching playlist {playlist_id}: {e}[/red]")

        # Sort by popularity and limit
        songs.sort(key=lambda x: x.get("popularity", 0), reverse=True)
        return songs[: self.max_songs]

    def fetch_from_fallback(self) -> list[dict]:
        """Use curated fallback song list."""
        songs = []
        for i, song in enumerate(self.FALLBACK_SONGS[:self.max_songs]):
            songs.append({
                "id": f"fallback_{i:03d}",
                "title": song["title"],
                "artist": song["artist"],
                "album": song.get("album", ""),
                "year": song.get("year"),
                "duration_ms": 0,
                "spotify_url": "",
                "preview_url": None,
                "popularity": 100 - i,  # Ordered by popularity
                "source": "curated",
            })
        return songs

    def fetch_all(self) -> list[dict]:
        """
        Fetch songs: try Spotify first, fall back to curated list.
        Also loads existing songs from data/songs/ directory.
        Returns list of song dicts.
        """
        console.print("\n[bold cyan]=== Fetching Popular Japanese Songs ===[/bold cyan]")

        songs = self.fetch_from_spotify()

        if not songs:
            console.print("[yellow]Using curated fallback song list[/yellow]")
            songs = self.fetch_from_fallback()

        # Also load any existing individual song files
        existing_songs = self._load_existing_songs()
        if existing_songs:
            # Merge without duplicates (check by title+artist)
            seen = {(s["title"], s["artist"]) for s in songs}
            for es in existing_songs:
                key = (es.get("title", ""), es.get("artist", ""))
                if key not in seen and key[0]:
                    seen.add(key)
                    songs.append(es)
            console.print(f"[dim]Loaded {len(existing_songs)} existing songs from data/songs/[/dim]")

        console.print(f"\n[green]Total songs collected: {len(songs)}[/green]")

        # Display summary table
        table = Table(title="Top Songs", show_lines=False)
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="cyan")
        table.add_column("Artist", style="green")
        table.add_column("Year", style="yellow")

        for i, song in enumerate(songs[:20], 1):
            table.add_row(str(i), song["title"], song["artist"], str(song.get("year", "?")))

        console.print(table)
        if len(songs) > 20:
            console.print(f"  ... and {len(songs) - 20} more songs")

        # Save to file
        output_path = self.data_dir / "songs_list.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(songs, f, ensure_ascii=False, indent=2)
        console.print(f"\nSaved to: {output_path}")

        return songs

    def _load_existing_songs(self) -> list[dict]:
        """Load existing individual song files from data/songs/ directory."""
        songs = []
        songs_dir = self.data_dir

        if not songs_dir.exists():
            return songs

        # Check for aggregated list files first
        for list_file in songs_dir.glob("*_songs.json"):
            try:
                with open(list_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and "title" in item:
                                songs.append({
                                    "id": item.get("number", f"existing_{len(songs)}"),
                                    "title": item["title"],
                                    "artist": item.get("artist", ""),
                                    "album": item.get("album", ""),
                                    "year": item.get("year"),
                                    "duration_ms": 0,
                                    "spotify_url": "",
                                    "preview_url": None,
                                    "popularity": 100 - len(songs),
                                    "source": "existing",
                                })
                    console.print(f"  [dim]Loaded {len(songs)} from {list_file.name}[/dim]")
            except Exception as e:
                console.print(f"  [yellow]Error loading {list_file.name}: {e}[/yellow]")

        # Also check individual song files
        for song_file in songs_dir.glob("*.json"):
            if song_file.name == "songs_list.json" or "_songs" in song_file.name:
                continue
            try:
                with open(song_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "title" in data:
                    songs.append({
                        "id": data.get("number", f"existing_{len(songs)}"),
                        "title": data["title"],
                        "artist": data.get("artist", ""),
                        "album": data.get("album", ""),
                        "year": data.get("year"),
                        "duration_ms": 0,
                        "spotify_url": "",
                        "preview_url": None,
                        "popularity": 100 - len(songs),
                        "source": "existing",
                    })
            except Exception:
                pass

        return songs

    def search_song(self, title: str, artist: str) -> Optional[dict]:
        """Search for a specific song on Spotify."""
        if not self.sp:
            return None
        try:
            query = f"track:{title} artist:{artist}"
            results = self.sp.search(q=query, type="track", limit=5)
            tracks = results.get("tracks", {}).get("items", [])
            if tracks:
                track = tracks[0]
                return {
                    "id": track["id"],
                    "title": track["name"],
                    "artist": ", ".join(a["name"] for a in track["artists"]),
                    "album": track["album"]["name"],
                    "year": int(track["album"]["release_date"][:4]) if track["album"].get("release_date") else None,
                    "duration_ms": track.get("duration_ms", 0),
                    "spotify_url": track.get("external_urls", {}).get("spotify", ""),
                }
        except Exception as e:
            console.print(f"[red]Search error for '{title}': {e}[/red]")
        return None
