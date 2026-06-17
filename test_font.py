#!/usr/bin/env python3
"""测试字体渲染，找出无法显示的汉字"""
from PIL import Image, ImageDraw, ImageFont
import os

# 候选字体
fonts = [
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/YuGothM.ttc",
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
    "C:/Windows/Fonts/msmincho.ttc",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
]

# 测试字符集：包含常见日语汉字、特殊字符
test_chars = [
    "夜に駆ける", "群青", "紅蓮華", "残酷な天使のテーゼ",
    "沈むように溶けてゆく", "僕が死のうと思ったのは",
    "烏", "森羅清浄事祓", "極楽浄土", "妄想感傷代償連盟",
    "絆", "鳥の詩", "扉をあけて", "渡月橋",
    "柴魚", "悪魔の子", "老人と海",
    "前前前世", "夢灯籠", "スパークル",
    "一", "二", "三", "日", "月", "火", "水", "木", "金", "土",
    "曜", "鬱", "齋藤", "髙橋", "竜", "崎", "辻", "込",
    "々", "ー", "♪", "☆", "★", "♥",
    "あいうえお", "アイウエオ",
]

print("=== 字体渲染测试 ===\n")

for font_path in fonts:
    if not os.path.exists(font_path):
        continue
    
    print(f"\n字体: {os.path.basename(font_path)}")
    
    # 尝试不同 face_index
    for face_index in range(3):
        try:
            font = ImageFont.truetype(font_path, 40, index=face_index)
        except Exception:
            break
        
        # 测试每个字符
        failed = []
        for text in test_chars:
            try:
                img = Image.new("RGBA", (200, 60), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                bbox = draw.textbbox((0, 0), text, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                # 检查是否渲染出内容（非空bbox）
                if w <= 0 or h <= 0:
                    failed.append(text)
                    continue
                # 检查像素是否被绘制
                draw.text((10, 10), text, font=font, fill=(255, 255, 255, 255))
                pixels = list(img.getdata())
                has_content = any(p[3] > 0 for p in pixels)
                if not has_content:
                    failed.append(text)
            except Exception as e:
                failed.append(f"{text} (err: {e})")
        
        if failed:
            print(f"  face_index={face_index}: 失败 {len(failed)} 个: {failed[:10]}")
        else:
            print(f"  face_index={face_index}: ✓ 全部通过")

# 额外检查：找出 YuGothB 中缺失的字符
print("\n\n=== 详细检查 YuGothB.ttc ===")
font_path = "C:/Windows/Fonts/YuGothB.ttc"
for face_index in range(5):
    try:
        font = ImageFont.truetype(font_path, 40, index=face_index)
    except Exception:
        print(f"  face_index={face_index}: 无法加载")
        break
    
    # 获取字体支持的字符
    try:
        cmap = font.get_variation_names() if hasattr(font, 'get_variation_names') else set()
    except:
        pass
    
    failed = []
    for text in test_chars:
        try:
            img = Image.new("RGBA", (200, 60), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), text, font=font, fill=(255, 255, 255, 255))
            pixels = list(img.getdata())
            has_content = any(p[3] > 0 for p in pixels)
            if not has_content:
                failed.append(text)
        except Exception as e:
            failed.append(f"{text} ({e})")
    
    if failed:
        print(f"  face_index={face_index}: 失败 {len(failed)}: {failed}")
    else:
        print(f"  face_index={face_index}: ✓ 全部通过")
