"""检查歌词跳转逻辑"""
import json

with open("data/analysis/YOASOBI_夜に駆ける.json", "r", encoding="utf-8") as f:
    d = json.load(f)

lines = d.get("analyzed_lines", [])

def find_active(lines, t):
    for i, ln in enumerate(lines):
        s = ln.get("start", 0) or 0
        e = ln.get("end", 0) or 0
        if s <= t < e:
            return i
    return -1

# 检查不同时间点的歌词
test_times = [0, 0.5, 1, 3, 5, 9, 15, 20, 31, 32, 35, 60, 100, 150, 200, 245, 247]
print(f"{'time':>6} {'idx':>3} {'text'}")
print("-" * 60)
for t in test_times:
    idx = find_active(lines, t)
    if idx >= 0:
        text = lines[idx].get("text", "")[:40]
        start = lines[idx].get("start", 0)
        end = lines[idx].get("end", 0)
        print(f"{t:6.1f} [{idx:2d}] {text}  ({start:.1f}-{end:.1f})")
    else:
        print(f"{t:6.1f} [--] (no active line)")
