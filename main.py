"""
JP Music Video Generator - Main Pipeline
=========================================
Complete pipeline: Song discovery → Lyrics scraping → Serialization → 
Analysis → Video generation.

Usage:
    python main.py                    # Full pipeline with default config
    python main.py --songs-only       # Only fetch song list
    python main.py --lyrics-only      # Only scrape lyrics
    python main.py --analyze-only     # Only analyze lyrics
    python main.py --video-only       # Only generate videos
    python main.py --song "Lemon" --artist "米津玄師"  # Process single song
    python main.py --format youtube   # Output format
    python main.py --preview          # Generate preview frame only
"""

import json
import os
import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.spotify_fetcher import SpotifyFetcher
from modules.lyrics_scraper import LyricsScraper
from modules.lyrics_serializer import LyricsSerializer
from modules.jp_analyzer import JPAnalyzer
from modules.video_generator import VideoGenerator


def load_config(config_path: str = None) -> dict:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = PROJECT_ROOT / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        console.print(f"[red]Config file not found: {config_path}[/red]")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Resolve relative paths
    for key in ("data_dir", "output_dir", "assets_dir", "font_dir", "bg_dir"):
        if key in config.get("paths", {}):
            path = Path(config["paths"][key])
            if not path.is_absolute():
                config["paths"][key] = str(PROJECT_ROOT / path)

    return config


def print_banner():
    """Print project banner."""
    banner = """
    ╔═══════════════════════════════════════════╗
    ║    🎵 JP Music Video Generator 🎵        ║
    ║                                           ║
    ║   日语流行歌曲歌词学习短视频生成工具       ║
    ║   Lyrics Learning Video Generator          ║
    ╚═══════════════════════════════════════════╝
    """
    console.print(banner, style="cyan")


# ========== Pipeline Steps ==========

def step_fetch_songs(config: dict) -> list[dict]:
    """Step 1: Fetch popular Japanese songs."""
    fetcher = SpotifyFetcher(config)
    songs = fetcher.fetch_all()
    return songs


def step_scrape_lyrics(config: dict, songs: list[dict], max_songs: int = None) -> list[dict]:
    """Step 2: Scrape lyrics for songs."""
    scraper = LyricsScraper(config)
    target_songs = songs[:max_songs] if max_songs else songs
    lyrics_list = scraper.scrape_batch(target_songs)
    return lyrics_list


def step_serialize_lyrics(config: dict, lyrics_list: list[dict]) -> list[dict]:
    """Step 3: Serialize lyrics to structured JSON."""
    serializer = LyricsSerializer(config)
    serialized = serializer.serialize_batch(lyrics_list)
    return serialized


def step_analyze(config: dict, serialized_list: list[dict]) -> list[dict]:
    """Step 4: Analyze Japanese knowledge points."""
    analyzer = JPAnalyzer(config)
    results = analyzer.analyze_batch(serialized_list)
    return results


def step_generate_videos(
    config: dict,
    analysis_results: list[dict],
    format_name: str = None,
    preview_only: bool = False,
    max_videos: int = None,
) -> list[str]:
    """Step 5: Generate videos."""
    generator = VideoGenerator(config)
    outputs = []

    target = analysis_results[:max_videos] if max_videos else analysis_results

    for i, result in enumerate(target, 1):
        title = result.get("title", "Unknown")
        console.print(f"\n[{i}/{len(target)}] {title}")

        if preview_only:
            path = generator.generate_preview_frame(result, format_name=format_name)
        else:
            path = generator.generate_video(result, format_name=format_name)

        if path:
            outputs.append(path)

    return outputs


# ========== Main Pipeline ==========

def run_pipeline(
    config: dict,
    songs_only: bool = False,
    lyrics_only: bool = False,
    analyze_only: bool = False,
    video_only: bool = False,
    format_name: str = None,
    preview_only: bool = False,
    song_title: str = None,
    song_artist: str = None,
    max_songs: int = None,
    lrc_path: str = None,
    lyrics_text: str = None,
):
    """Run the full or partial pipeline."""

    data_dir = Path(config["paths"]["data_dir"])

    # === Single song mode ===
    if song_title:
        console.print(f"\n[bold]Single song mode: {song_title}[/bold]")

        if lyrics_text:
            # Direct lyrics input
            scraper = LyricsScraper(config)
            lyrics_data = scraper.load_local_lyrics(lyrics_text, title=song_title, artist=song_artist or "")
            lyrics_list = [lyrics_data]
        elif lrc_path:
            # LRC file input
            scraper = LyricsScraper(config)
            lyrics_data = scraper.load_lrc_file(lrc_path)
            if not lyrics_data:
                console.print("[red]Failed to load LRC file[/red]")
                return
            lyrics_data["title"] = song_title
            lyrics_data["artist"] = song_artist or ""
            lyrics_list = [lyrics_data]
        else:
            # Scrape lyrics
            scraper = LyricsScraper(config)
            song = {"title": song_title, "artist": song_artist or "", "id": "single"}
            lyrics = scraper.search_and_scrape(song_title, song_artist or "", "single")
            if not lyrics:
                console.print("[red]Could not find lyrics. Use --lyrics-text or --lrc to provide them.[/red]")
                return
            lyrics_list = [lyrics]

        # Serialize
        serializer = LyricsSerializer(config)
        serialized = serializer.serialize_batch(lyrics_list)
        if not serialized:
            console.print("[red]Serialization failed[/red]")
            return

        # Analyze
        analyzer = JPAnalyzer(config)
        analysis = analyzer.analyze_batch(serialized)
        if not analysis:
            console.print("[red]Analysis failed[/red]")
            return

        # Generate video
        if not analyze_only:
            step_generate_videos(config, analysis, format_name, preview_only)

        return

    # === Batch mode ===

    # Step 1: Fetch songs
    songs = None
    if not (lyrics_only or analyze_only or video_only):
        songs = step_fetch_songs(config)
    else:
        # Try to load existing songs
        songs_path = data_dir / "songs" / "songs_list.json"
        if songs_path.exists():
            with open(songs_path, "r", encoding="utf-8") as f:
                songs = json.load(f)
            console.print(f"[dim]Loaded {len(songs)} songs from cache[/dim]")

    if songs_only:
        return

    # Step 2: Scrape lyrics
    lyrics_list = None
    if not (analyze_only or video_only):
        lyrics_list = step_scrape_lyrics(config, songs, max_songs)
    else:
        # Try to load existing lyrics
        lyrics_dir = data_dir / "lyrics"
        if lyrics_dir.exists():
            lyrics_list = []
            for f in sorted(lyrics_dir.glob("*.json")):
                with open(f, "r", encoding="utf-8") as fp:
                    lyrics_list.append(json.load(fp))
            console.print(f"[dim]Loaded {len(lyrics_list)} lyrics from cache[/dim]")

    if lyrics_only:
        return

    # Step 3: Serialize
    serialized_list = None
    if not (analyze_only or video_only):
        serialized_list = step_serialize_lyrics(config, lyrics_list or [])
    else:
        # Try to load existing serialized
        ser_dir = data_dir / "serialized"
        if ser_dir.exists():
            serialized_list = []
            for f in sorted(ser_dir.glob("*.json")):
                with open(f, "r", encoding="utf-8") as fp:
                    serialized_list.append(json.load(fp))
            console.print(f"[dim]Loaded {len(serialized_list)} serialized files from cache[/dim]")

    # Step 4: Analyze
    analysis_results = None
    if not video_only:
        analysis_results = step_analyze(config, serialized_list or [])
    else:
        # Try to load existing analysis
        analysis_dir = data_dir / "analysis"
        if analysis_dir.exists():
            analysis_results = []
            for f in sorted(analysis_dir.glob("*.json")):
                with open(f, "r", encoding="utf-8") as fp:
                    analysis_results.append(json.load(fp))
            console.print(f"[dim]Loaded {len(analysis_results)} analysis files from cache[/dim]")

    if analyze_only:
        return

    # Step 5: Generate videos
    if analysis_results:
        step_generate_videos(config, analysis_results, format_name, preview_only, max_songs)


# ========== CLI ==========

@click.command()
@click.option("--config", "-c", default=None, help="Path to config.yaml")
@click.option("--songs-only", is_flag=True, help="Only fetch song list")
@click.option("--lyrics-only", is_flag=True, help="Only scrape lyrics")
@click.option("--analyze-only", is_flag=True, help="Only analyze lyrics")
@click.option("--video-only", is_flag=True, help="Only generate videos (uses cached data)")
@click.option("--format", "-f", "format_name", default=None, help="Video format (tiktok/youtube/instagram)")
@click.option("--preview", is_flag=True, help="Generate preview frame only")
@click.option("--song", default=None, help="Process a single song by title")
@click.option("--artist", default=None, help="Artist name (used with --song)")
@click.option("--max", "-n", "max_songs", default=None, type=int, help="Max songs to process")
@click.option("--lrc", "lrc_path", default=None, help="Path to LRC file (used with --song)")
@click.option("--lyrics-text", default=None, help="Lyrics text (used with --song)")
def main(config, songs_only, lyrics_only, analyze_only, video_only,
         format_name, preview, song, artist, max_songs, lrc_path, lyrics_text):
    """JP Music Video Generator - 日语流行歌曲歌词学习短视频生成工具"""
    print_banner()

    cfg = load_config(config)

    run_pipeline(
        config=cfg,
        songs_only=songs_only,
        lyrics_only=lyrics_only,
        analyze_only=analyze_only,
        video_only=video_only,
        format_name=format_name,
        preview_only=preview,
        song_title=song,
        song_artist=artist,
        max_songs=max_songs,
        lrc_path=lrc_path,
        lyrics_text=lyrics_text,
    )

    console.print("\n[bold green]Done![/bold green]")


if __name__ == "__main__":
    main()
