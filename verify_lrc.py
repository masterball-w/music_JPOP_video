"""验证LRC解析后的翻译匹配情况"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from batch_process import parse_lrc_file, lrc_to_serialized

lrc_path = Path("data/audio/YOASOBI - 夜に駆ける.lrc")
result = parse_lrc_file(lrc_path)
if result is None:
    print("解析失败")
    sys.exit(1)

lines = result["lines"]

print(f"标题: {result.get('title')}")
print(f"歌手: {result.get('artist')}")
print(f"总行数: {len(lines)}")
print("=" * 80)

# 统计无翻译的歌词行
no_translation = []
has_translation = 0
for i, line in enumerate(lines):
    text = line["text"]
    translation = line.get("translation")
    if translation:
        has_translation += 1
    else:
        no_translation.append((i, text))

print(f"有翻译: {has_translation} 行")
print(f"无翻译: {len(no_translation)} 行")
print("=" * 80)
print("无翻译的行:")
for idx, text in no_translation:
    print(f"  [{idx}] {text}")

print("=" * 80)
print("前30行解析结果:")
for i, line in enumerate(lines[:30]):
    text = line["text"]
    translation = line.get("translation")
    print(f"  [{i}] {text}")
    if translation:
        print(f"       -> {translation}")
