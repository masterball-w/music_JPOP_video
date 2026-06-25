#!/usr/bin/env python3
"""
修复 LRC 歌词文件顺序：将翻译行重新排到对应日文行之后（同一时间戳）。

修复策略：
1. 改进 _is_chinese：只要不含日文假名且含中文字符 → 中文翻译
   （解决 "Here we go出发吧" 等中英混合行被误判为日文的问题）
2. 匹配时跳过纯 ASCII 行（如 "I've been thinking about you"），
   避免英文行消耗翻译配额
3. 采用"缓存翻译 + 批量按序匹配"策略，将翻译按顺序匹配到未翻译日文行
4. 重写 LRC：每行日文后紧跟其翻译（同一时间戳）
"""
import html
import re
import shutil
import unicodedata
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
AUDIO_DIR = PROJECT_ROOT / "data" / "audio"
BACKUP_DIR = PROJECT_ROOT / "data" / "audio_lrc_backup"


def normalize_str(s: str) -> str:
    """标准化字符串用于比较（处理不同的波浪号字符等）"""
    return unicodedata.normalize('NFKC', s)


def is_chinese(text: str) -> bool:
    """判断文本是否为中文翻译行。
    规则：
    - 含日文假名（平假名/片假名）→ 日文
    - 不含假名但含中文字符 → 中文（不论比例，解决 "Here we go出发吧" 等混合行）
    - 其余 → 非中文（日文或纯英文）
    """
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
        return False
    cjk = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', text)
    return len(cjk) > 0


def needs_translation(text: str) -> bool:
    """判断该行是否需要翻译（即是否为含 CJK 的日文行）。
    纯 ASCII 行（如英文歌词）不需要翻译，不参与匹配。
    """
    if is_chinese(text):
        return False
    cjk = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', text)
    return len(cjk) > 0


def parse_lrc(lrc_path: Path):
    """解析 LRC 文件，返回 (metadata, timed_lines)"""
    metadata = {}
    timed_lines = []
    lrc_pattern = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\]\s*(.*)')
    meta_pattern = re.compile(r'\[([a-zA-Z#]+):(.*)\]')

    with open(lrc_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('```'):
                continue
            lrc_match = lrc_pattern.match(line)
            if lrc_match:
                minutes = int(lrc_match.group(1))
                seconds = int(lrc_match.group(2))
                ms_str = lrc_match.group(3)
                ms = int(ms_str) if len(ms_str) == 3 else int(ms_str) * 10
                text = html.unescape(lrc_match.group(4).strip())
                time_s = minutes * 60 + seconds + ms / 1000.0
                if text:
                    timed_lines.append({"start": round(time_s, 3), "text": text})
            else:
                meta_match = meta_pattern.match(line)
                if meta_match:
                    metadata[meta_match.group(1)] = meta_match.group(2).strip()

    return metadata, timed_lines


def should_combine_translations(prev_trans: str, curr_trans: str) -> bool:
    """检测 curr_trans 是否是 prev_trans 的延续（分割翻译的第二部分）。
    启发式：curr_trans 以 prev_trans 的后缀开头（3+ 字符重叠）。
    例如: prev="Here we go出发吧", curr="出发吧出发吧展开双翼" → True
    """
    max_overlap = min(len(prev_trans), len(curr_trans), 10)
    for length in range(max_overlap, 2, -1):
        if prev_trans.endswith(curr_trans[:length]):
            return True
    return False


def match_translations(metadata: dict, timed_lines: list) -> list:
    """将中文翻译行匹配到对应的日文行。
    返回 lines: [{"start": float, "text": str, "translation": Optional[str]}]
    """
    lines = []
    pending_translations = []

    # 预计算标准化的标题/歌手，用于过滤标题行
    title = metadata.get("ti", "")
    artist = metadata.get("ar", "")
    title_norm = normalize_str(title) if title else ""
    artist_norm = normalize_str(artist) if artist else ""

    def flush():
        """将缓存的翻译按顺序匹配到需要翻译的日文行。"""
        if not pending_translations:
            return
        # 合并分割翻译（连续翻译在边界共享字符时合并）
        combined = [pending_translations[0]]
        for t in pending_translations[1:]:
            if should_combine_translations(combined[-1], t):
                combined[-1] = combined[-1] + t
            else:
                combined.append(t)
        # 收集需要翻译但尚未翻译的日文行索引
        untranslated = []
        for k, ln in enumerate(lines):
            if needs_translation(ln["text"]) and not ln.get("translation"):
                untranslated.append(k)
        # 按顺序匹配
        for j, trans_text in enumerate(combined):
            if j < len(untranslated):
                idx = untranslated[j]
                if lines[idx].get("translation"):
                    lines[idx]["translation"] += trans_text
                else:
                    lines[idx]["translation"] = trans_text
            else:
                # 没有足够的未翻译日文行，追加到末尾作为单独行
                lines.append({"start": 0, "text": trans_text, "translation": None})
        pending_translations.clear()

    for current in timed_lines:
        text = current["text"]

        # 跳过元信息行
        if text.startswith(('词：', '曲：', '编曲', 'TME', '翻译', '原唱')):
            continue
        # 跳过翻译署名等元信息（如"我骑在银龙的背上（歌词翻译 耿子淇）"）
        if '歌词翻译' in text:
            continue

        # 跳过标题行（多种格式）：
        # 1. "title - artist" 精确匹配
        # 2. 文本以标题开头且含 " - "（如 "渡月橋 〜君 想ふ〜 (渡月桥~思君~) - 倉木麻衣 (くらき まい)"）
        # 3. 含 " - " 且含歌手名
        # 注意：不要简单匹配 text == title，因为歌词可能包含与标题相同的行（如副歌）
        if title and artist and text == f"{title} - {artist}":
            continue
        if title_norm:
            text_norm = normalize_str(text)
            if text_norm.startswith(title_norm) and " - " in text:
                continue
        if artist and " - " in text and artist in text:
            continue

        if is_chinese(text):
            pending_translations.append(text)
        else:
            # 日文行或英文行：先触发批量匹配，再添加
            flush()
            lines.append({"start": current["start"], "text": text, "translation": None})

    # 文件结束：处理剩余翻译
    flush()

    return lines


def format_timestamp(time_s: float) -> str:
    """格式化时间戳为 [MM:SS.cc]（2位小数）"""
    minutes = int(time_s // 60)
    seconds = int(time_s % 60)
    cs = int(round((time_s % 1) * 100))
    if cs >= 100:
        cs = 99
    return f"{minutes:02d}:{seconds:02d}.{cs:02d}"


def write_fixed_lrc(lrc_path: Path, metadata: dict, lines: list):
    """写入修复后的 LRC：每行日文后紧跟翻译（同一时间戳）"""
    output = []

    # 元数据
    for key in ("ti", "ar", "al", "by"):
        if key in metadata:
            output.append(f"[{key}:{metadata[key]}]")
    # 其他元数据
    for key, value in metadata.items():
        if key not in ("ti", "ar", "al", "by"):
            output.append(f"[{key}:{value}]")
    output.append("")

    # 歌词行
    for line in lines:
        ts = format_timestamp(line["start"])
        output.append(f"[{ts}]{line['text']}")
        if line.get("translation"):
            output.append(f"[{ts}]{line['translation']}")

    with open(lrc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output) + "\n")


def main():
    BACKUP_DIR.mkdir(exist_ok=True)

    # 优先从备份目录读取原始文件，确保基于原始数据修复
    lrc_files = sorted(BACKUP_DIR.glob("*.lrc"))
    if not lrc_files:
        lrc_files = sorted(AUDIO_DIR.glob("*.lrc"))
        print(f"No backup found, reading from audio dir")
    else:
        print(f"Reading from backup dir (original files)")
    print(f"Found {len(lrc_files)} LRC files\n")

    stats = {"total": 0, "fixed": 0, "no_translation": 0, "failed": 0}

    for lrc_path in lrc_files:
        stats["total"] += 1
        try:
            # 解析（从备份或音频目录）
            metadata, timed_lines = parse_lrc(lrc_path)
            if not timed_lines:
                print(f"  [SKIP] No timed lines: {lrc_path.name}")
                stats["no_translation"] += 1
                continue

            # 匹配翻译
            lines = match_translations(metadata, timed_lines)

            # 检查是否有翻译
            has_translation = any(ln.get("translation") for ln in lines)
            if not has_translation:
                print(f"  [SKIP] No translations: {lrc_path.name}")
                stats["no_translation"] += 1
                continue

            # 统计
            total_lines = len(lines)
            translated = sum(1 for ln in lines if ln.get("translation"))
            untranslated_jp = sum(
                1 for ln in lines
                if needs_translation(ln["text"]) and not ln.get("translation")
            )

            # 写入修复后的 LRC（始终写到音频目录）
            output_path = AUDIO_DIR / lrc_path.name
            write_fixed_lrc(output_path, metadata, lines)

            print(f"  [OK] {lrc_path.name}: {total_lines} lines, "
                  f"{translated} translated, {untranslated_jp} untranslated JP")
            stats["fixed"] += 1

        except Exception as e:
            print(f"  [FAIL] {lrc_path.name}: {e}")
            stats["failed"] += 1

    print(f"\n=== Done ===")
    print(f"Fixed: {stats['fixed']}")
    print(f"No translation (skipped): {stats['no_translation']}")
    print(f"Failed: {stats['failed']}")
    print(f"Total: {stats['total']}")
    print(f"\nBackup saved to: {BACKUP_DIR}")


if __name__ == "__main__":
    main()
