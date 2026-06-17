#!/usr/bin/env python3
"""
批量处理所有歌曲：LRC → 序列化 → 分析 → 生成视频
"""
import json
import re
import sys
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.lyrics_serializer import LyricsSerializer
from modules.jp_analyzer import JPAnalyzer
from modules.ai_translator import AITranslator
from modules.video_generator_v3 import VideoGenerator

console = Console()


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


def parse_lrc_file(lrc_path: Path) -> Optional[dict]:
    """解析 LRC 文件，返回带时间戳的歌词数据"""
    lines = []
    metadata = {}
    lrc_pattern = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\]\s*(.*)')
    meta_pattern = re.compile(r'\[([a-zA-Z#]+):(.*)\]')

    try:
        with open(lrc_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # 跳过 markdown 代码块标记
                if line.startswith('```'):
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
                        lines.append({
                            "start": round(time_s, 3),
                            "end": None,
                            "text": text,
                        })
                else:
                    meta_match = meta_pattern.match(line)
                    if meta_match:
                        metadata[meta_match.group(1)] = meta_match.group(2).strip()

        if not lines:
            return None

        # Fill end times
        for i in range(len(lines) - 1):
            lines[i]["end"] = lines[i + 1]["start"]
        lines[-1]["end"] = lines[-1]["start"] + 5.0

        return {
            "lines": lines,
            "metadata": metadata,
            "title": metadata.get("ti", ""),
            "artist": metadata.get("ar", ""),
        }
    except Exception as e:
        console.print(f"[red]Error parsing {lrc_path}: {e}[/red]")
        return None


def lrc_to_serialized(lrc_data: dict, serializer: LyricsSerializer) -> dict:
    """将 LRC 数据转换为序列化格式（保留原始时间戳）"""
    lines = lrc_data.get("lines", [])
    serialized_lines = []

    for i, line in enumerate(lines):
        text = line.get("text", "")
        start = line.get("start", 0)
        end = line.get("end", 0)

        # 添加罗马音
        romaji = serializer.to_romaji(text)

        serialized_lines.append({
            "index": i,
            "text": text,
            "romaji": romaji,
            "start": start,
            "end": end,
            "section": "Unknown",
            "duration": end - start if end and start else 0,
        })

    return {
        "title": lrc_data.get("title", ""),
        "artist": lrc_data.get("artist", ""),
        "song_id": lrc_data.get("song_id", ""),
        "source": "lrc",
        "total_duration": lines[-1]["end"] if lines else 0,
        "total_lines": len(serialized_lines),
        "sections": {},
        "lines": serialized_lines,
    }


def find_matching_audio(title: str, artist: str, audio_dir: Path) -> Optional[str]:
    """查找匹配的音频文件"""
    if not audio_dir.exists():
        return None

    def normalize(s: str) -> str:
        """标准化字符串用于比较"""
        s = re.sub(r'[_\-\s\.]+', '', s.lower())
        return s

    title_norm = normalize(title)
    artist_norm = normalize(artist) if artist else ""

    # 搜索所有音频文件
    all_audio_files = []
    for ext in (".mp3", ".wav", ".m4a", ".flac", ".ogg"):
        all_audio_files.extend(list(audio_dir.glob(f"*{ext}")))

    best_match = None
    best_score = 0

    for audio_file in all_audio_files:
        filename = audio_file.stem
        filename_norm = normalize(filename)

        score = 0

        # 标题匹配
        if title_norm in filename_norm or filename_norm in title_norm:
            score += 60

        # 艺术家匹配
        if artist_norm and artist_norm in filename_norm:
            score += 40

        # 精确匹配
        if title_norm == filename_norm:
            score += 100

        if score > best_score:
            best_score = score
            best_match = str(audio_file)

    if best_score >= 25 and title and title.strip():
        return best_match
    return None


def process_single_song(
    lrc_path: Path,
    audio_dir: Path,
    config: dict,
    serializer: LyricsSerializer,
    analyzer: JPAnalyzer,
    translator: AITranslator,
    generator: VideoGenerator,
    index: int,
    total: int
) -> bool:
    """处理单首歌曲"""
    console.print(f"\n[bold cyan][{index}/{total}][/bold cyan] Processing: {lrc_path.stem}")

    # 1. 解析 LRC
    lrc_data = parse_lrc_file(lrc_path)
    if not lrc_data:
        console.print(f"  [red]Failed to parse LRC[/red]")
        return False

    title = lrc_data.get("title", lrc_path.stem)
    artist = lrc_data.get("artist", "")

    if not title:
        title = lrc_path.stem

    console.print(f"  Title: {title}")
    console.print(f"  Artist: {artist}")

    # 2. 查找音频
    audio_path = find_matching_audio(title, artist, audio_dir)
    if audio_path:
        console.print(f"  [dim]Audio: {Path(audio_path).name}[/dim]")
    else:
        console.print(f"  [yellow]No matching audio found[/yellow]")

    # 3. 序列化（使用 LRC 时间戳）
    console.print(f"  Serializing...")
    lrc_data["song_id"] = f"{artist}_{title}".replace(" ", "_") if artist else title
    serialized = lrc_to_serialized(lrc_data, serializer)
    if not serialized or not serialized.get("lines"):
        console.print(f"  [red]Serialization failed[/red]")
        return False

    # 4. 分析
    console.print(f"  Analyzing...")
    analysis = analyzer.analyze_song(serialized)
    if not analysis:
        console.print(f"  [red]Analysis failed[/red]")
        return False

    # 4.5. AI 翻译为中文
    console.print(f"  Translating to Chinese...")
    analysis = translator.translate_song_analysis(analysis)

    # 保存分析结果
    song_id = serialized.get("song_id", f"song_{index}")
    safe_id = re.sub(r'[^\w\-]', '_', song_id)
    analysis_path = Path(config["paths"]["data_dir"]) / "analysis" / f"{safe_id}.json"
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
    console.print(f"  [dim]Analysis saved: {analysis_path.name}[/dim]")

    # 5. 生成视频
    console.print(f"  Generating video...")
    try:
        video_path = generator.generate_video(analysis, audio_path=audio_path)
        if video_path:
            console.print(f"  [green]✓ Video: {Path(video_path).name}[/green]")
            return True
        else:
            console.print(f"  [red]Video generation failed[/red]")
            return False
    except Exception as e:
        console.print(f"  [red]Error generating video: {e}[/red]")
        return False


def main():
    console.print("[bold cyan]=== 批量处理所有歌曲 ===[/bold cyan]\n")

    # 加载配置
    config = load_config()

    # 初始化模块
    serializer = LyricsSerializer(config)
    analyzer = JPAnalyzer(config)
    translator = AITranslator(config)
    generator = VideoGenerator(config)

    # 扫描 LRC 文件
    audio_dir = Path(config["paths"]["data_dir"]) / "audio"
    lrc_files = sorted(audio_dir.glob("*.lrc"))

    if not lrc_files:
        console.print(f"[red]No LRC files found in {audio_dir}[/red]")
        return

    console.print(f"Found {len(lrc_files)} LRC files\n")

    # 处理所有歌曲
    success_count = 0
    fail_count = 0

    for i, lrc_path in enumerate(lrc_files, 1):
        try:
            success = process_single_song(
                lrc_path=lrc_path,
                audio_dir=audio_dir,
                config=config,
                serializer=serializer,
                analyzer=analyzer,
                translator=translator,
                generator=generator,
                index=i,
                total=len(lrc_files)
            )
            if success:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            console.print(f"  [red]Unexpected error: {e}[/red]")
            fail_count += 1

    # 总结
    console.print(f"\n[bold green]=== 处理完成 ===[/bold green]")
    console.print(f"成功: {success_count}")
    console.print(f"失败: {fail_count}")
    console.print(f"总计: {len(lrc_files)}")


if __name__ == "__main__":
    main()
