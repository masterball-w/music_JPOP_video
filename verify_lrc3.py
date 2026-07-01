"""检查翻译匹配是否正确"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from batch_process import parse_lrc_file

lrc_path = Path("data/audio/YOASOBI - 夜に駆ける.lrc")
result = parse_lrc_file(lrc_path)
lines = result["lines"]

out = []
# 显示所有行（含翻译）以人工核对
for i, line in enumerate(lines):
    text = line["text"]
    translation = line.get("translation")
    out.append(f"[{i}] {text}")
    if translation:
        out.append(f"    -> {translation}")
    else:
        out.append(f"    -> (无翻译)")

with open("verify_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Saved to verify_result.txt")

