#!/usr/bin/env python3
"""
检查字体加载的详细信息和可能的 fallback 情况
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from modules.video_generator_v3 import TextRenderer, find_japanese_font, find_japanese_font_bold
from PIL import Image, ImageDraw, ImageFont

def check_font_loading():
    """检查字体加载详情"""
    print("=== 字体加载检查 ===\n")
    
    # 检查 find_japanese_font
    font_path = find_japanese_font()
    bold_path = find_japanese_font_bold()
    
    print(f"普通字体路径: {font_path}")
    print(f"粗体字体路径: {bold_path}")
    
    # 检查 TextRenderer
    renderer = TextRenderer()
    print(f"\nTextRenderer 使用的字体:")
    print(f"  font_path: {renderer.font_path}")
    print(f"  bold_font_path: {renderer.bold_font_path}")
    
    # 测试不同尺寸的字体加载
    print("\n=== 测试不同尺寸字体加载 ===")
    for size in [32, 48, 64, 80]:
        try:
            font = renderer.font(size)
            bold = renderer.bold_font(size)
            print(f"  {size}pt: 普通={type(font).__name__}, 粗体={type(bold).__name__}")
            
            # 检查是否是默认字体（fallback）
            if isinstance(font, ImageFont.ImageFont):
                print(f"    ⚠️  警告: {size}pt 普通字体使用了默认字体!")
            if isinstance(bold, ImageFont.ImageFont):
                print(f"    ⚠️  警告: {size}pt 粗体使用了默认字体!")
                
        except Exception as e:
            print(f"  {size}pt: 错误 - {e}")
    
    # 测试实际渲染
    print("\n=== 测试实际渲染（包含可能的边缘情况）===")
    test_texts = [
        "夜に駆ける",
        "残酷な天使のテーゼ",
        "僕が死のうと思ったのは",
        "烏",
        "森羅清浄事祓",
        "極楽浄土",
        "妄想感傷代償連盟",
        "柴 鱼 の c a l l i n g",  # 包含空格
        "Mr. _Broken Heart_",  # 包含下划线
        "DAN DAN 心魅かれてく",  # 混合
        "First Love",  # 纯英文
        "ありがとう…",  # 包含省略号
        "ラブ・ストーリーは突然に",  # 包含中点
        "Truefool",  # 纯英文
        "Cry For Me (feat. Ami)",  # 包含括号
    ]
    
    img = Image.new('RGB', (1000, 800), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = renderer.font(40)
    
    y = 20
    for text in test_texts:
        try:
            # 渲染文本
            draw.text((20, y), text, fill=(255, 255, 255), font=font)
            
            # 获取边界框
            bbox = draw.textbbox((0, 0), text, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            
            # 检查是否渲染成功
            if width <= 0 or height <= 0:
                print(f"  ✗ '{text}' - 渲染失败 (尺寸: {width}x{height})")
                draw.text((20, y), f"FAILED: {text}", fill=(255, 0, 0), font=font)
            else:
                print(f"  ✓ '{text}' ({width}x{height})")
            
            y += 50
        except Exception as e:
            print(f"  ✗ '{text}' - 异常: {e}")
            draw.text((20, y), f"ERROR: {text} - {e}", fill=(255, 0, 0), font=font)
            y += 50
    
    # 保存测试图像
    output_path = Path("data/test_font_detailed.png")
    img.save(output_path)
    print(f"\n测试图像已保存: {output_path}")
    
    # 检查 .ttc 文件的 font index
    print("\n=== 检查 .ttc 文件的字体索引 ===")
    if font_path and font_path.endswith('.ttc'):
        try:
            # 尝试不同的 index
            for index in range(5):
                try:
                    test_font = ImageFont.truetype(font_path, 40, index=index)
                    print(f"  Index {index}: ✓ 可用")
                except Exception:
                    print(f"  Index {index}: ✗ 不可用")
                    break
        except Exception as e:
            print(f"  错误: {e}")

if __name__ == '__main__':
    check_font_loading()
