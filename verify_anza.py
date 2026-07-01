"""检查ANZA歌曲的无翻译行"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from batch_process import parse_lrc_file

lrc_path = Path("data/audio/ANZA - 扉をあけて.lrc")
result = parse_lrc_file(lrc_path)
lines = result["lines"]

out = []
for i, line in enumerate(lines):
    text = line["text"]
    translation = line.get("translation")
    out.append(f"[{i}] {text}")
    if translation:
        out.append(f"    -> {translation}")
    else:
        out.append(f"    -> (无翻译)")

with open("verify_anza.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Saved to verify_anza.txt")
