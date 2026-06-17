#!/usr/bin/env python3
"""
用实际视频数据测试渲染，复现字体问题
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json
from modules.video_generator_v3 import VideoGenerator, TextRenderer
from PIL import Image, ImageDraw, ImageFont

def test_with_actual_data():
    """用实际分析数据测试渲染"""
    # 加载配置
    from batch_process import load_config
    config = load_config()
    
    # 创建 VideoGenerator
    generator = VideoGenerator(config)
    
    # 加载实际的分析数据
    analysis_file = Path("data/analysis/YOASOBI_夜に駆ける.json")
    if not analysis_file.exists():
        print(f"找不到分析文件: {analysis_file}")
        return
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    print(f"=== 测试实际数据渲染 ===")
    print(f"标题: {analysis['title']}")
    print(f"艺术家: {analysis['artist']}")
    print(f"总行数: {analysis['total_lines']}")
    
    # 测试渲染歌词行
    print(f"\n=== 测试歌词行渲染 ===")
    lines = analysis.get('analyzed_lines', [])
    test_lines = lines[:10]  # 测试前10行
    
    for i, line in enumerate(test_lines):
        text = line.get('text', '')
        romaji = line.get('romaji', '')
        
        print(f"\n行 {i}: {text}")
        print(f"  罗马音: {romaji}")
        
        # 渲染歌词
        lyric_img = generator.R.render(text, 56, color=(255, 255, 255))
        print(f"  歌词渲染尺寸: {lyric_img.size}")
        
        # 检查是否有内容
        pixels = list(lyric_img.getdata())
        has_content = sum(1 for p in pixels if p[3] > 0)
        print(f"  有效像素: {has_content}")
        
        if has_content < 100:
            print(f"  ⚠️ 警告: 渲染可能有问题!")
            lyric_img.save(f"data/test_line_{i}_problem.png")
        
        # 如果有词汇注释，测试渲染
        vocab = line.get('vocabulary', [])
        if vocab:
            print(f"  词汇注释: {len(vocab)} 个")
            for j, v in enumerate(vocab[:2]):  # 只测试前2个
                word = v.get('word', '')
                reading = v.get('reading', '')
                meaning = v.get('meaning', '')
                
                print(f"    词汇 {j}: {word} ({reading}) - {meaning}")
                
                # 渲染词汇
                word_img = generator.R.render(word, 48, color=(255, 255, 255))
                print(f"      词汇渲染尺寸: {word_img.size}")
                
                pixels = list(word_img.getdata())
                has_content = sum(1 for p in pixels if p[3] > 0)
                print(f"      有效像素: {has_content}")
                
                if has_content < 50:
                    print(f"      ⚠️ 警告: 词汇渲染可能有问题!")
                    word_img.save(f"data/test_vocab_{i}_{j}_problem.png")
    
    # 测试渲染完整的 note card
    print(f"\n=== 测试 Note Card 渲染 ===")
    top_notes = analysis.get('top_notes', [])
    for i, note in enumerate(top_notes[:5]):
        note_type = note.get('type', '')
        data = note.get('data', {})
        
        if note_type == 'vocabulary':
            word = data.get('word', '')
            reading = data.get('reading', '')
            meaning = data.get('meaning', '')
            jlpt = data.get('jlpt_level', '')
            
            print(f"\nNote {i}: {word} ({reading})")
            print(f"  含义: {meaning}")
            print(f"  JLPT: {jlpt}")
            
            # 渲染 note card
            card_img = generator.R.render_note_card(note, width=900)
            print(f"  Card 尺寸: {card_img.size}")
            
            pixels = list(card_img.getdata())
            has_content = sum(1 for p in pixels if p[3] > 0)
            print(f"  有效像素: {has_content}")
            
            card_img.save(f"data/test_card_{i}.png")
            print(f"  已保存: data/test_card_{i}.png")
    
    # 测试渲染一个完整的视频帧
    print(f"\n=== 测试完整视频帧渲染 ===")
    try:
        # 创建一个测试时间点
        test_time = 10.0  # 10秒处
        
        # 调用 _render_frame
        W, H = 1080, 1920
        from modules.video_generator_v3 import EnhancedBackground, ParticleEngine
        
        bg_engine = EnhancedBackground(W, H)
        particles = ParticleEngine(W, H)
        
        frame = generator._render_frame(test_time, W, H, analysis, bg_engine, particles)
        
        print(f"帧尺寸: {frame.size}")
        pixels = list(frame.getdata())
        has_content = sum(1 for p in pixels if p[3] > 0)
        print(f"有效像素: {has_content}")
        
        frame.save("data/test_full_frame.png")
        print(f"已保存: data/test_full_frame.png")
        
    except Exception as e:
        print(f"渲染帧时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_with_actual_data()
