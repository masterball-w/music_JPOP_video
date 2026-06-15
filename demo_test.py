"""
Demo test script - Tests the full pipeline with one song.
Provides lyrics directly to avoid scraping dependencies.
"""

import json
import os
import sys
from pathlib import Path

# Fix Windows console encoding
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from modules.spotify_fetcher import SpotifyFetcher
from modules.lyrics_scraper import LyricsScraper
from modules.lyrics_serializer import LyricsSerializer
from modules.jp_analyzer import JPAnalyzer
from modules.video_generator import VideoGenerator
from rich.console import Console

console = Console(force_terminal=False, legacy_windows=False)


def main():
    # Load config
    with open(PROJECT_ROOT / "config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Resolve relative paths
    for key in ("data_dir", "output_dir", "assets_dir", "font_dir", "bg_dir"):
        if key in config.get("paths", {}):
            path = Path(config["paths"][key])
            if not path.is_absolute():
                config["paths"][key] = str(PROJECT_ROOT / path)

    # Test song: YOASOBI - 夜に駆ける (Yoru ni Kakeru / Racing Into the Night)
    lyrics_text = """【イントロ】
沈むように 溶けてゆくように
二人だけの空が広がる夜に

【Aメロ】
「さよなら」だけが人生だ
また来世で会おうぜ
君の瞳に映る僕は
どんな顔をしているかな

【Bメロ】
嘘みたいな日々を生きて
本当の気持ちがわからない
君といるときだけ
心臓が鳴るんだ

【サビ】
沈むように 溶けてゆくように
二人だけの空が広がる夜に
「さよなら」じゃなくて
またいつか会える気がした

【Aメロ2】
言葉にできない想いを
胸の奥にしまっていた
君が笑うそれだけで
全部どうでもよくなった

【Bメロ2】
繰り返す日々の中で
君だけが輝いて見えた
触れられない距離さえも
愛しく思えたんだ

【サビ2】
沈むように 溶けてゆくように
二人だけの空が広がる夜に
「さよなら」じゃなくて
またいつか会える気がした

【Cメロ】
もしも生まれ変われたなら
また君を探してしまうだろう
この手を離さないで
最後に笑って

【ラスサビ】
沈むように 溶けてゆくように
二人だけの空が広がる夜に
「ありがとう」じゃなくて
「またね」って手を振った

沈むように 溶けてゆくように
二人だけの空が広がる夜に
"""

    console.print("\n[bold cyan]========================================[/bold cyan]")
    console.print("[bold cyan]  Demo: YOASOBI - 夜に駆ける[/bold cyan]")
    console.print("[bold cyan]========================================[/bold cyan]")

    # Step 1: Create lyrics data
    console.print("\n[bold]Step 1: Preparing lyrics...[/bold]")
    scraper = LyricsScraper(config)
    lyrics_data = scraper.load_local_lyrics(
        lyrics_text,
        title="夜に駆ける",
        artist="YOASOBI",
    )
    lyrics_data["song_id"] = "yoasobi_yoru_ni_kakeru"
    console.print(f"  Lyrics loaded: {len(lyrics_data['raw'])} chars")

    # Step 2: Serialize
    console.print("\n[bold]Step 2: Serializing lyrics...[/bold]")
    serializer = LyricsSerializer(config)
    serialized = serializer.serialize(lyrics_data, total_duration=255)  # ~4:15 duration

    # Save serialized
    safe_id = "yoasobi_yoru_ni_kakeru"
    ser_path = Path(config["paths"]["data_dir"]) / "serialized" / f"{safe_id}.json"
    ser_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ser_path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)
    console.print(f"  Saved: {ser_path}")
    console.print(f"  Lines: {serialized['total_lines']}")
    console.print(f"  Sections: {list(serialized['sections'].keys())}")

    # Show a few lines
    for line in serialized["lines"][:5]:
        console.print(f"    [{line['start']:.1f}s - {line['end']:.1f}s] {line['text']}")

    # Step 3: Analyze
    console.print("\n[bold]Step 3: Analyzing Japanese knowledge points...[/bold]")
    analyzer = JPAnalyzer(config)
    analysis = analyzer.analyze_song(serialized)

    # Save analysis
    analysis_path = Path(config["paths"]["data_dir"]) / "analysis" / f"{safe_id}.json"
    analysis_path.parent.mkdir(parents=True, exist_ok=True)
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
    console.print(f"  Saved: {analysis_path}")

    # Show top notes
    console.print("\n  [bold]Top Knowledge Notes:[/bold]")
    for note in analysis["top_notes"][:8]:
        try:
            if note["type"] == "vocabulary":
                d = note["data"]
                console.print(f"    [{d['jlpt_level']}] {d['word']} ({d['reading']}) = {d['meaning']}")
            else:
                d = note["data"]
                pattern = d.get("pattern", "").replace("\u301c", "~")
                console.print(f"    [{d['level']}] {pattern} -> {d['meaning']}")
        except UnicodeEncodeError:
            pass  # Skip if console can't encode

    # Step 4: Generate preview frame
    console.print("\n[bold]Step 4: Generating preview frame...[/bold]")
    generator = VideoGenerator(config)
    preview_path = generator.generate_preview_frame(analysis, format_name="tiktok")
    if preview_path:
        console.print(f"  [green]Preview: {preview_path}[/green]")

    # Step 5: Generate short video (first 30 seconds only for demo)
    console.print("\n[bold]Step 5: Generating demo video (30s)...[/bold]")
    # Temporarily limit duration for demo
    config["video"]["max_duration_seconds"] = 30
    generator2 = VideoGenerator(config)
    video_path = generator2.generate_video(analysis, format_name="tiktok", output_name="demo_yoru_ni_kakeru")
    if video_path:
        console.print(f"  [green]Video: {video_path}[/green]")

    console.print("\n[bold green]Demo complete![/bold green]")


if __name__ == "__main__":
    main()
