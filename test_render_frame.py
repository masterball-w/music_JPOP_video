#!/usr/bin/env python3
"""
生成一个测试视频帧，检查实际渲染效果
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json
from modules.video_generator_v3 import VideoGenerator, TextRenderer, find_japanese_font
from PIL import Image, ImageDraw, ImageFont

def test_render():
    """测试实际渲染"""
    # 1. 检查字体
    font_path = find_japanese_font()
    print(f"字体路径: {font_path}")
    
    # 2. 创建 TextRenderer
    renderer = TextRenderer()
    print(f"renderer.font_path: {renderer.font_path}")
    print(f"renderer.bold_font_path: {renderer.bold_font_path}")
    
    # 3. 测试不同尺寸的字体
    for size in [28, 36, 48, 56, 72]:
        font = renderer.font(size)
        bold = renderer.bold_font(size)
        print(f"\n  size={size}:")
        print(f"    font: {type(font).__name__}, name={font.getname()}")
        print(f"    bold: {type(bold).__name__}, name={bold.getname()}")
        
        # 测试渲染
        test_text = "夜に駆ける 残酷な天使のテーゼ 僕が死のうと思ったのは"
        img = renderer.render(test_text, size, color=(255, 255, 255))
        print(f"    render size: {img.size}")
        
        # 检查是否有像素
        pixels = list(img.getdata())
        has_content = sum(1 for p in pixels if p[3] > 0)
        print(f"    has_content pixels: {has_content}")
    
    # 4. 加载实际的分析数据，测试 note card 渲染
    analysis_file = Path("data/analysis/YOASOBI_夜に駆ける.json")
    if analysis_file.exists():
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
        
        print(f"\n=== 测试 Note Card 渲染 ===")
        top_notes = analysis.get("top_notes", [])
        for i, note in enumerate(top_notes[:3]):
            print(f"\n  Note {i}: {note.get('type')} - {note.get('data', {}).get('word', '')}")
            card_img = renderer.render_note_card(note, width=900)
            print(f"    card size: {card_img.size}")
            pixels = list(card_img.getdata())
            has_content = sum(1 for p in pixels if p[3] > 0)
            print(f"    has_content pixels: {has_content}")
            card_img.save(f"data/test_note_{i}.png")
            print(f"    saved: data/test_note_{i}.png")
    
    # 5. 直接测试 Pillow 渲染中文字符
    print(f"\n=== 直接 Pillow 渲染测试 ===")
    font = ImageFont.truetype(font_path, 56, index=0)
    test_lines = [
        "沈むように溶けてゆくように",
        "二人だけの空が広がる夜に",
        "「さよなら」だけだった",
        "词汇: 人 (ひと) - person",
        "语法: ～ように 表示比喻",
        "JLPT N5 级别词汇",
    ]
    
    img = Image.new("RGBA", (1080, 400), (15, 15, 25, 255))
    draw = ImageDraw.Draw(img)
    y = 10
    for line in test_lines:
        draw.text((20, y), line, font=font, fill=(255, 255, 255, 255))
        y += 60
    img.save("data/test_direct_render.png")
    print(f"  已保存: data/test_direct_render.png")
    
    # 6. 检查字体文件是否真的包含这些字符
    print(f"\n=== 检查字体字符覆盖 ===")
    # 获取字体的 cmap
    try:
        font_test = ImageFont.truetype(font_path, 56, index=0)
        # 检查 getname
        print(f"  Font name: {font_test.getname()}")
        
        # 测试一些关键字符
        critical_chars = "夜駆群青紅蓮華残酷天使沈溶僕死思烏森羅清浄事祓極楽土妄感傷代償連盟"
        for ch in critical_chars:
            test_img = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
            d = ImageDraw.Draw(test_img)
            d.text((5, 5), ch, font=font_test, fill=(255, 255, 255, 255))
            pixels = list(test_img.getdata())
            has = sum(1 for p in pixels if p[3] > 0)
            status = "✓" if has > 10 else "✗"
            if has <= 10:
                print(f"  {status} '{ch}' (U+{ord(ch):04X}) pixels={has}")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == '__main__':
    test_render()
