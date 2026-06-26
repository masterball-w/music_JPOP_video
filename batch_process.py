#!/usr/bin/env python3
"""
批量处理所有歌曲：LRC → 序列化 → 分析 → 生成视频
"""
import html
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


def _is_chinese(text: str) -> bool:
    """判断文本是否为中文翻译行。
    如果包含日文假名（平假名/片假名），则判定为日文。
    否则如果包含较多中文字符，则判定为中文。
    """
    # 包含日文假名 → 日文
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
        return False
    # 包含较多中文字符 → 中文
    cjk = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', text)
    return len(cjk) / max(len(text), 1) > 0.3


def parse_lrc_file(lrc_path: Path) -> Optional[dict]:
    """解析 LRC 文件，返回带时间戳的歌词数据
    自动将中文翻译行合并到对应的日文行中。
    """
    # 第一阶段：读取所有带时间戳的行
    timed_lines = []
    metadata = {}
    lrc_pattern = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\]\s*(.*)')
    meta_pattern = re.compile(r'\[([a-zA-Z#]+):(.*)\]')

    try:
        with open(lrc_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('```'):
                    continue

                lrc_match = lrc_pattern.match(line)
                if lrc_match:
                    minutes = int(lrc_match.group(1))
                    seconds = int(lrc_match.group(2))
                    ms_str = lrc_match.group(3)
                    ms = int(ms_str) if len(ms_str) == 3 else int(ms_str) * 10
                    text = lrc_match.group(4).strip()
                    # 解码 HTML 实体（如 &quot; &amp; &lt; &gt;）
                    text = html.unescape(text)
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

        # 第二阶段：合并中文翻译到日文行
        # LRC 结构分析：
        # 中文翻译行的时间戳通常等于"被翻译日文行的下一句日文行"的开始时间
        # 即：翻译行出现在被翻译日文行之后，时间戳=下一句日文行的开始时间
        # 例如:
        #   [00:10.00]どうやってこうやって          ← 日文A
        #   [00:13.00]要怎么做？就这么做              ← 翻译A（时间戳=日文B的开始时间）
        #   [00:13.00]またほら君と話そうか            ← 日文B
        #
        # 策略：缓存翻译行，遇到下一个日文行时触发批量匹配
        # 当连续出现多个翻译行时（如 日文A,日文B,翻译A,翻译B,日文C），
        # 按顺序匹配到"除当前日文行外的未翻译日文行"（翻译A→A, 翻译B→B）
        # 这样可避免"最近未翻译行"策略把翻译A错误匹配到最后添加的日文B
        lines = []
        pending_translations = []  # 待匹配的翻译行缓存

        def flush_pending_translations(exclude_last=False):
            """将缓存的翻译按顺序匹配到未翻译日文行。
            exclude_last=True 时，排除最后添加的日文行（因为当前正准备添加新日文行，
            该新日文行还没有翻译）。
            """
            if not pending_translations:
                return
            # 收集未翻译日文行的索引
            untranslated = []
            for k, ln in enumerate(lines):
                if not _is_chinese(ln["text"]) and not ln.get("translation"):
                    untranslated.append(k)
            # 排除最后添加的日文行（如果需要）
            if exclude_last and untranslated:
                untranslated.pop()
            # 按顺序匹配
            for j, trans_text in enumerate(pending_translations):
                if j < len(untranslated):
                    idx = untranslated[j]
                    if lines[idx].get("translation"):
                        lines[idx]["translation"] += trans_text
                    else:
                        lines[idx]["translation"] = trans_text
                else:
                    # 没有足够的未翻译日文行，追加到行末尾作为单独行
                    lines.append({"start": 0, "text": trans_text, "translation": None})
            pending_translations.clear()

        for current in timed_lines:
            text = current["text"]

            # 跳过元信息行（如词曲作者、著作权等）
            if text.startswith(('词：', '曲：', '编曲', 'TME', '翻译', '原唱')):
                continue

            # 跳过标题行（格式为"歌曲名 - 艺术家"，通常在LRC首行）
            title = metadata.get("ti", "")
            artist = metadata.get("ar", "")
            if title and artist and text == f"{title} - {artist}":
                continue
            if title and text == title:
                continue

            if _is_chinese(text):
                # 中文翻译行：缓存起来，等待批量匹配
                pending_translations.append(text)
                continue

            # 日文行：先触发批量匹配，再添加日文行
            # 此时lines中的最后一个是上一个日文行（还未添加当前日文行），
            # 所以所有未翻译日文行都可以被匹配
            flush_pending_translations(exclude_last=False)
            lines.append({"start": current["start"], "text": text, "translation": None})

        # 文件结束：处理剩余的待匹配翻译
        flush_pending_translations(exclude_last=False)

        # 第三阶段：填充结束时间
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
        translation = line.get("translation")

        # 添加罗马音
        romaji = serializer.to_romaji(text)

        serialized_lines.append({
            "index": i,
            "text": text,
            "romaji": romaji,
            "translation": translation,
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

    # 检查视频是否已存在 — 跳过整首歌的处理
    safe_video_name = re.sub(r'[^\w\-\u3000-\u9fff\uff00-\uffef]', '_', f"{title}_{artist}")
    expected_video = Path(config["paths"]["output_dir"]) / "videos" / f"{safe_video_name}_tiktok.mp4"
    if expected_video.exists():
        console.print(f"  [yellow]Skip (video exists): {expected_video.name}[/yellow]")
        return True

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

    # 4.5. AI 深度分析歌词知识点（提取词汇和语法，中文释义）
    console.print(f"  AI analyzing lyrics...")
    analysis = translator.analyze_lyrics_with_ai(analysis)

    # 4.6. AI 翻译为中文（翻译本地分析中的英文释义）
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
            console.print(f"  [green][OK] Video: {Path(video_path).name}[/green]")
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
