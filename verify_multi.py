"""验证多首歌曲的LRC解析结果"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from batch_process import parse_lrc_file

test_songs = [
    "YOASOBI - 夜に駆ける",
    "ANZA - 扉をあけて",
    "米津玄師 - Lemon",
    "RADWIMPS - 前前前世",
    "LiSA - 紅蓮華",
]

results = []
for song in test_songs:
    lrc_path = Path(f"data/audio/{song}.lrc")
    if not lrc_path.exists():
        results.append(f"[MISS] {song}: LRC not found")
        continue
    result = parse_lrc_file(lrc_path)
    if result is None:
        results.append(f"[FAIL] {song}: parse failed")
        continue
    lines = result["lines"]
    total = len(lines)
    no_trans = sum(1 for ln in lines if not ln.get("translation"))
    has_trans = total - no_trans
    results.append(f"[OK] {song}: total={total}, has_trans={has_trans}, no_trans={no_trans}")

out = "\n".join(results)
with open("verify_multi.txt", "w", encoding="utf-8") as f:
    f.write(out)
print(out)
