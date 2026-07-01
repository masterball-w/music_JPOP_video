"""简化输出验证结果，只显示无翻译行"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from batch_process import parse_lrc_file

lrc_path = Path("data/audio/YOASOBI - 夜に駆ける.lrc")
result = parse_lrc_file(lrc_path)
lines = result["lines"]

no_translation = [(i, line["text"]) for i, line in enumerate(lines) if not line.get("translation")]
print(f"TITLE: {result.get('title')}")
print(f"ARTIST: {result.get('artist')}")
print(f"TOTAL: {len(lines)}")
print(f"HAS_TRANS: {len(lines) - len(no_translation)}")
print(f"NO_TRANS: {len(no_translation)}")
print("NO_TRANS_LINES:")
for idx, text in no_translation:
    print(f"  [{idx}] {text}")
