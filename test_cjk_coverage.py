#!/usr/bin/env python3
"""用 LRC 中实际的中文字符精确测试字体覆盖"""
from PIL import Image, ImageDraw, ImageFont
import os, re

# 从 LRC 文件中提取所有中文字符
lrc_dir = "data/audio"
all_chinese_chars = set()
for lrc_file in sorted(os.listdir(lrc_dir)):
    if not lrc_file.endswith('.lrc'):
        continue
    with open(os.path.join(lrc_dir, lrc_file), 'r', encoding='utf-8') as f:
        for line in f:
            for ch in line:
                # 中日韩统一表意文字
                if '\u4e00' <= ch <= '\u9fff' or '\u3400' <= ch <= '\u4dbf':
                    all_chinese_chars.add(ch)

print(f"从 LRC 中提取了 {len(all_chinese_chars)} 个不重复的中文字符")

# 同时收集分析数据中的中文字符
analysis_dir = "data/analysis"
for afile in os.listdir(analysis_dir):
    if not afile.endswith('.json'):
        continue
    import json
    with open(os.path.join(analysis_dir, afile), 'r', encoding='utf-8') as f:
        data = json.load(f)
    text = json.dumps(data, ensure_ascii=False)
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            all_chinese_chars.add(ch)

print(f"加上分析数据后共 {len(all_chinese_chars)} 个中文字符\n")

# 测试字体
fonts_to_test = [
    ("YuGothB.ttc", "游ゴシック Bold"),
    ("msyh.ttc", "微软雅黑"),
    ("msyhbd.ttc", "微软雅黑粗体"),
    ("simhei.ttf", "黑体"),
]

for font_name, font_label in fonts_to_test:
    path = f"C:/Windows/Fonts/{font_name}"
    if not os.path.exists(path):
        print(f"{font_label}: 不存在")
        continue
    
    font = ImageFont.truetype(path, 40, index=0)
    
    missing = []
    for ch in sorted(all_chinese_chars):
        img = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((5, 5), ch, font=font, fill=(255, 255, 255, 255))
        pixels = list(img.getdata())
        has = sum(1 for p in pixels if p[3] > 0)
        if has < 5:
            missing.append((ch, f"U+{ord(ch):04X}"))
    
    if missing:
        print(f"{font_label}: ✗ 缺失 {len(missing)} 个字符")
        for ch, code in missing[:20]:
            print(f"  '{ch}' ({code})")
        if len(missing) > 20:
            print(f"  ... 还有 {len(missing) - 20} 个")
    else:
        print(f"{font_label}: ✓ 全部 {len(all_chinese_chars)} 个字符都支持")
