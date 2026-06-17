"""
Test script for Video Generator v3 - Enhanced Visual Effects
===============================================================
This script tests the new v3 video generator with:
- Anime background images
- Fly-in/fly-out lyric animations
- Enhanced note card animations
- Ken Burns background effect
"""

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.video_generator_v3 import VideoGenerator
from rich.console import Console

console = Console()


def load_test_data():
    """Load the existing analysis data for testing."""
    analysis_path = PROJECT_ROOT / "data" / "analysis" / "yoasobi_yoru_ni_kakeru.json"
    if not analysis_path.exists():
        console.print(f"[red]Analysis file not found: {analysis_path}[/red]")
        return None

    with open(analysis_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def test_preview_frame():
    """Test generating a preview frame with v3."""
    console.print("\n[bold cyan]=== Testing v3 Preview Frame ===[/bold cyan]")

    data = load_test_data()
    if not data:
        return

    config = {
        "paths": {
            "output_dir": str(PROJECT_ROOT / "output"),
            "assets_dir": str(PROJECT_ROOT / "assets"),
            "bg_dir": str(PROJECT_ROOT / "assets" / "backgrounds"),
        },
        "video": {
            "theme": "aurora",
            "theme_custom": {
                "background_mode": "image",
                "background_image": str(PROJECT_ROOT / "assets" / "backgrounds" / "anime_night_lake.jpg"),
                "overlay_darkness": 0.55,
            },
            "style": {
                "lyric_font_size": 56,
                "lyric_active_color": [0, 220, 255],
                "lyric_inactive_color": [210, 215, 235],
                "lyric_inactive_min_fade": 0.55,
                "romaji_font_size": 32,
                "romaji_color": [180, 180, 200],
            },
            "formats": {
                "tiktok": {"width": 1080, "height": 1920, "fps": 30},
            },
            "default_format": "tiktok",
            "max_duration_seconds": 180,
            "intro_seconds": 3,
            "outro_seconds": 2,
        }
    }

    generator = VideoGenerator(config)

    # Generate preview at different timestamps
    timestamps = [2, 8, 15, 25, 40]
    for ts in timestamps:
        console.print(f"  Generating preview at t={ts}s...")
        path = generator.generate_preview_frame(data, time=ts, format_name="tiktok")
        if path:
            console.print(f"  [green]Saved: {path}[/green]")


def test_video_generation():
    """Test generating a short video with v3."""
    console.print("\n[bold cyan]=== Testing v3 Video Generation ===[/bold cyan]")

    data = load_test_data()
    if not data:
        return

    # Limit to first few lines for quick testing
    test_data = data.copy()
    test_data["analyzed_lines"] = data["analyzed_lines"][:8]

    config = {
        "paths": {
            "output_dir": str(PROJECT_ROOT / "output"),
            "assets_dir": str(PROJECT_ROOT / "assets"),
            "bg_dir": str(PROJECT_ROOT / "assets" / "backgrounds"),
        },
        "video": {
            "theme": "aurora",
            "theme_custom": {
                "background_mode": "image",
                "background_image": str(PROJECT_ROOT / "assets" / "backgrounds" / "anime_night_lake.jpg"),
                "overlay_darkness": 0.55,
            },
            "style": {
                "lyric_font_size": 56,
                "lyric_active_color": [0, 220, 255],
                "lyric_inactive_color": [210, 215, 235],
                "lyric_inactive_min_fade": 0.55,
                "romaji_font_size": 32,
                "romaji_color": [180, 180, 200],
            },
            "formats": {
                "tiktok": {"width": 1080, "height": 1920, "fps": 30},
            },
            "default_format": "tiktok",
            "max_duration_seconds": 60,
            "intro_seconds": 2,
            "outro_seconds": 1,
        }
    }

    generator = VideoGenerator(config)

    audio_path = PROJECT_ROOT / "assets" / "audio" / "yoru_ni_kakeru.mp3"
    audio = str(audio_path) if audio_path.exists() else None

    console.print("  Generating test video (first 8 lines)...")
    path = generator.generate_video(
        test_data,
        audio_path=audio,
        format_name="tiktok",
        output_name="test_v3_enhanced"
    )
    if path:
        console.print(f"  [green]Saved: {path}[/green]")


def test_different_backgrounds():
    """Test with different background images."""
    console.print("\n[bold cyan]=== Testing Different Backgrounds ===[/bold cyan]")

    data = load_test_data()
    if not data:
        return

    test_data = data.copy()
    test_data["analyzed_lines"] = data["analyzed_lines"][:5]

    backgrounds = [
        ("anime_night_lake.jpg", "Night Lake"),
        ("anime_city_night.jpg", "City Night"),
        ("anime_shrine_dusk.jpg", "Shrine Dusk"),
        ("anime_starry_sky.jpg", "Starry Sky"),
        ("anime_sunset_country.jpg", "Sunset Country"),
    ]

    for bg_file, bg_name in backgrounds:
        console.print(f"\n  Testing background: {bg_name}")

        config = {
            "paths": {
                "output_dir": str(PROJECT_ROOT / "output"),
                "assets_dir": str(PROJECT_ROOT / "assets"),
                "bg_dir": str(PROJECT_ROOT / "assets" / "backgrounds"),
            },
            "video": {
                "theme": "aurora",
                "theme_custom": {
                    "background_mode": "image",
                    "background_image": str(PROJECT_ROOT / "assets" / "backgrounds" / bg_file),
                    "overlay_darkness": 0.55,
                },
                "style": {
                    "lyric_font_size": 56,
                    "lyric_active_color": [0, 220, 255],
                    "lyric_inactive_color": [210, 215, 235],
                    "lyric_inactive_min_fade": 0.55,
                    "romaji_font_size": 32,
                    "romaji_color": [180, 180, 200],
                },
                "formats": {
                    "tiktok": {"width": 1080, "height": 1920, "fps": 30},
                },
                "default_format": "tiktok",
                "max_duration_seconds": 30,
                "intro_seconds": 2,
                "outro_seconds": 1,
            }
        }

        generator = VideoGenerator(config)
        path = generator.generate_preview_frame(
            test_data,
            time=5,
            format_name="tiktok"
        )
        if path:
            # Rename to include background name
            new_path = Path(path).parent / f"preview_v3_{bg_name.lower().replace(' ', '_')}.png"
            Path(path).rename(new_path)
            console.print(f"  [green]Saved: {new_path}[/green]")


if __name__ == "__main__":
    console.print("[bold magenta]JP Music Video Generator v3 - Test Suite[/bold magenta]")
    console.print("=" * 50)

    # Run tests
    test_preview_frame()
    test_different_backgrounds()
    # test_video_generation()  # Uncomment to test full video generation

    console.print("\n[bold green]All tests completed![/bold green]")
