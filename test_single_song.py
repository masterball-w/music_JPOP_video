#!/usr/bin/env python3
"""
测试单首歌曲的完整处理流程
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from batch_process import (
    load_config, parse_lrc_file, lrc_to_serialized,
    find_matching_audio, process_single_song
)
from modules.lyrics_serializer import LyricsSerializer
from modules.jp_analyzer import JPAnalyzer
from modules.ai_translator import AITranslator
from modules.video_generator_v3 import VideoGenerator
from rich.console import Console

console = Console()

def test_single_song(song_name=None):
    """测试单首歌曲"""
    # 选择测试歌曲
    if song_name is None:
        song_name = "YOASOBI - 夜に駆ける"
    
    console.print(f"\n[bold cyan]=== 测试歌曲: {song_name} ===[/bold cyan]\n")
    
    # 加载配置
    config = load_config()
    
    # 初始化模块
    serializer = LyricsSerializer(config)
    analyzer = JPAnalyzer(config)
    translator = AITranslator(config)
    generator = VideoGenerator(config)
    
    # 设置路径
    audio_dir = Path(config["paths"]["data_dir"]) / "audio"
    lrc_path = audio_dir / f"{song_name}.lrc"
    
    if not lrc_path.exists():
        console.print(f"[red]LRC文件不存在: {lrc_path}[/red]")
        return
    
    # 处理歌曲
    success = process_single_song(
        lrc_path=lrc_path,
        audio_dir=audio_dir,
        config=config,
        serializer=serializer,
        analyzer=analyzer,
        translator=translator,
        generator=generator,
        index=1,
        total=1
    )
    
    if success:
        console.print(f"\n[bold green]✓ 测试成功！[/bold green]")
    else:
        console.print(f"\n[bold red]✗ 测试失败[/bold red]")
    
    return success

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="测试歌曲视频生成")
    parser.add_argument("song", nargs="?", default=None, help="歌曲名称（不含.lrc后缀）")
    args = parser.parse_args()
    test_single_song(args.song)
