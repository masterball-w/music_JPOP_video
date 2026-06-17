#!/usr/bin/env python3
"""
测试视频中的字符渲染，找出失败的字符
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from modules.video_generator_v3 import TextRenderer, find_japanese_font
from PIL import Image, ImageDraw

def test_character_rendering():
    """测试字符渲染"""
    renderer = TextRenderer()
    
    print(f"字体路径: {renderer.font_path}")
    print(f"粗体路径: {renderer.bold_font_path}")
    
    # 测试一些常见的日语字符
    test_chars = [
        '夜', 'に', '駆', 'け', 'る',  # 夜に駆ける
        '群', '青',  # 群青
        '紅', '蓮', '華',  # 紅蓮華
        '残', '酷', 'な', '天', '使', 'の', 'テ', 'ー', 'ゼ',  # 残酷な天使のテーゼ
        '沈', 'む', 'よ', 'う', 'に',  # 沈むように
        '溶', 'け', 'て', 'ゆ', 'く',  # 溶けてゆく
        '僕', 'が', '死', 'の', 'う',  # 僕が死のう
        '思', 'っ', 'た', 'の', 'は',  # と思ったのは
        '烏',  # 烏
        '森', '羅', '清', '浄', '事', '祓',  # 森羅清浄事祓
        '極', '楽', '浄', '土',  # 極楽浄土
        '妄', '想', '感', '傷', '代', '償', '連', '盟',  # 妄想感傷代償連盟
    ]
    
    # 创建测试图像
    img = Image.new('RGB', (800, 600), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font = renderer.font(40)
    
    print("\n测试字符渲染:")
    y = 20
    failed_chars = []
    
    for char in test_chars:
        try:
            # 尝试渲染
            bbox = draw.textbbox((0, 0), char, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            
            # 检查是否渲染成功（宽度和高度应该大于0）
            if width <= 0 or height <= 0:
                failed_chars.append(char)
                print(f"  ✗ '{char}' (U+{ord(char):04X}) - 渲染失败 (尺寸: {width}x{height})")
                draw.text((20, y), f"'{char}' - FAILED", fill=(255, 0, 0), font=font)
            else:
                draw.text((20, y), f"'{char}' - OK ({width}x{height})", fill=(255, 255, 255), font=font)
                print(f"  ✓ '{char}' (U+{ord(char):04X}) - 渲染成功 ({width}x{height})")
            
            y += 50
        except Exception as e:
            failed_chars.append(char)
            print(f"  ✗ '{char}' (U+{ord(char):04X}) - 异常: {e}")
            draw.text((20, y), f"'{char}' - ERROR: {e}", fill=(255, 0, 0), font=font)
            y += 50
    
    # 保存测试图像
    output_path = Path("data/test_font_render.png")
    img.save(output_path)
    print(f"\n测试图像已保存: {output_path}")
    
    if failed_chars:
        print(f"\n发现 {len(failed_chars)} 个字符渲染失败:")
        for char in failed_chars:
            print(f"  '{char}' (U+{ord(char):04X})")
    else:
        print("\n所有测试字符渲染成功！")
    
    return failed_chars

if __name__ == '__main__':
    test_character_rendering()
