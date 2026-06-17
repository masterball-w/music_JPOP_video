#!/usr/bin/env python3
"""测试哪些字体同时支持中日文"""
from PIL import Image, ImageDraw, ImageFont
import os

# 候选字体
fonts = [
    ("msyh.ttc", "微软雅黑"),
    ("msyhbd.ttc", "微软雅黑粗体"),
    ("simhei.ttf", "黑体"),
    ("simsun.ttc", "宋体"),
    ("YuGothB.ttc", "游ゴシック Bold"),
    ("meiryo.ttc", "Meiryo"),
    ("msgothic.ttc", "MS Gothic"),
]

# 测试：日文 + 中文
test_texts = [
    ("日文", "夜に駆ける 残酷な天使のテーゼ"),
    ("中文", "像是沉溺溶化一般 在只有你我二人的广阔夜空之下"),
    ("混合", "夜に駆ける - 像是沉溺溶化一般"),
    ("中文注释", "词汇: 人 (ひと) - person"),
    ("中文注释2", "语法: ～ように 表示比喻"),
    ("中文注释3", "JLPT N5 级别词汇"),
]

for font_name, font_label in fonts:
    path = f"C:/Windows/Fonts/{font_name}"
    if not os.path.exists(path):
        print(f"\n{font_label} ({font_name}): 不存在")
        continue
    
    print(f"\n{font_label} ({font_name}):")
    
    for face_index in range(3):
        try:
            font = ImageFont.truetype(path, 40, index=face_index)
        except Exception:
            break
        
        all_ok = True
        for category, text in test_texts:
            img = Image.new("RGBA", (800, 60), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.text((10, 10), text, font=font, fill=(255, 255, 255, 255))
            pixels = list(img.getdata())
            has_content = sum(1 for p in pixels if p[3] > 0)
            
            if has_content < 200:
                print(f"  face={face_index} ✗ {category}: 渲染失败 (pixels={has_content})")
                all_ok = False
        
        if all_ok:
            print(f"  face={face_index} ✓ 全部通过")
