#!/usr/bin/env python3
"""测试实际的字体加载流程，模拟 video_generator_v3 的行为"""
from PIL import Image, ImageDraw, ImageFont
import os

# 模拟 video_generator_v3 的字体查找
def find_japanese_font():
    candidates = [
        "C:/Windows/Fonts/YuGothB.ttc",
        "C:/Windows/Fonts/YuGothM.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/YuGothR.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/msmincho.ttc",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

font_path = find_japanese_font()
print(f"Selected font: {font_path}")

# 模拟 TextRenderer 的 font() 方法
# 注意：ImageFont.truetype(path, size) 不指定 index 时默认 index=0
font = ImageFont.truetype(font_path, 56)
print(f"Font type: {type(font)}")
print(f"Font name: {font.getname()}")

# 测试实际歌曲歌词中的字符
test_lines = [
    "沈むように溶けてゆくように",
    "二人だけの空が広がる夜に",
    "「さよなら」だけだった",
    "その一言で全てが分かった",
    "日が沈み出した空と君の姿",
    "フェンス越しに重なっていた",
    "残酷な天使のテーゼ",
    "少年よ神話になれ",
    "紅蓮華",
    "強く強く強く",
    "僕が死のうと思ったのは",
    "烏 - Raven",
    "森羅清浄事祓",
    "極楽浄土",
    "妄想感傷代償連盟",
    "夜に駆ける",
    "群青",
    "前前前世",
    "夢灯籠",
    "スパークル",
    "扉をあけて",
    "渡月橋 ～君 想ふ～",
    "柴 鱼 の c a l l i n g",
    "悪魔の子",
    "老人と海",
    "鳥の詩",
    "君が好きだと叫びたい",
    "世界が終るまでは…",
    "ブルーバード",
    "はいよろこんで",
    "T氏の話を信じるな",
    "うそつきマカロン",
    "バケモノの唄",
    " PLANET",
    "ひとり上手",
    "銀の龍の背に乗って",
    "君だけを守りたい",
    "僕が死のうと思ったのは",
    "心做し",
    "First Love",
    "One Last Kiss",
    "Beautiful World",
    "ラブ・ストーリーは突然に",
    "One Love",
    "MY ALL",
    "Barricades",
    "Call of Silence",
    "JANE Doe",
    "BOW AND ARROW",
    "IRIS OUT",
    "LOSER",
    "Lemon",
    "Avid",
    "aLIEz",
    "Unravel",
    "STYX HELIX",
    "SPECIALZ",
    "AIZO",
    "Ref_rain",
    "Brave Shine",
    "うっせぇわ",
    "NIGHT DANCER",
    "逃避行",
    "Rage your dream",
    "Stay With Me",
    "only my railgun",
    "シルエット",
    "ありがとう…",
    "第六感",
    "Tokyo Drift",
    "Episode 33",
    "DAY BY DAY",
    "VISIONS",
    "Stay with me",
    "なんでもないや",
    "赤と青",
    "ウルトラマンギンガの歌",
    "キボウノカケラ",
    "願い〜あの頃のキミへ〜",
    "secret base 〜君がくれたもの〜",
    "Starlight",
    "少女A",
    "そばにいるね",
    "残酷な天使のテーゼ",
    "Execution Clap",
    "ブレインロット",
    "恋愛サーキュレーション",
    "You & Me",
    "青い果実",
    "光るなら",
    "Cry For Me",
    "ヤラララ",
    "Lightning Moment",
    "Promise",
    "DAN DAN 心魅かれてく",
    "極楽浄土",
    "Sunshine Girl",
    "Mr. Broken Heart",
    "真夜中のドア Stay With Me",
    "バカみたいに",
    "英雄",
]

# 渲染测试
img = Image.new("RGBA", (400, 80), (0, 0, 0, 255))
draw = ImageDraw.Draw(img)

failed = []
for line in test_lines:
    try:
        test_img = Image.new("RGBA", (800, 80), (0, 0, 0, 0))
        d = ImageDraw.Draw(test_img)
        bbox = d.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        d.text((10, 10), line, font=font, fill=(255, 255, 255, 255))
        pixels = list(test_img.getdata())
        has_content = any(p[3] > 0 for p in pixels)
        
        if not has_content or w <= 0:
            failed.append(line)
    except Exception as e:
        failed.append(f"{line} (err: {e})")

if failed:
    print(f"\n❌ 渲染失败 ({len(failed)}):")
    for f in failed:
        print(f"  - {f}")
else:
    print(f"\n✓ 所有 {len(test_lines)} 行歌词渲染正常")

# 额外检查：逐字符检查每个汉字是否有实际像素
print("\n=== 逐字符检查 ===")
all_chars = set()
for line in test_lines:
    for ch in line:
        if ord(ch) > 127:  # 非ASCII
            all_chars.add(ch)

print(f"共 {len(all_chars)} 个非ASCII字符需要检查")

missing_chars = []
for ch in sorted(all_chars):
    test_img = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(test_img)
    d.text((5, 5), ch, font=font, fill=(255, 255, 255, 255))
    pixels = list(test_img.getdata())
    has_content = any(p[3] > 0 for p in pixels)
    if not has_content:
        missing_chars.append((ch, hex(ord(ch))))

if missing_chars:
    print(f"\n❌ 缺失字符 ({len(missing_chars)}):")
    for ch, code in missing_chars:
        print(f"  '{ch}' (U+{code[2:].upper().zfill(4)})")
else:
    print(f"\n✓ 所有字符渲染正常")

# 保存一个测试渲染图
test_img = Image.new("RGBA", (1080, 600), (20, 20, 40, 255))
d = ImageDraw.Draw(test_img)
y = 10
for i, line in enumerate(test_lines[:15]):
    d.text((20, y), line, font=font, fill=(255, 255, 255, 255))
    y += 40
test_img.save("data/font_test_output.png")
print(f"\n测试图片已保存到 data/font_test_output.png")
