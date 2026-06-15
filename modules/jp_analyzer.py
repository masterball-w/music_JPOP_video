"""
Japanese Language Analyzer Module
==================================
Analyzes Japanese lyrics for vocabulary, grammar, and JLPT-level knowledge points.
Uses Janome for morphological analysis and rule-based grammar detection.
"""

import json
import re
from pathlib import Path
from typing import Optional
from collections import defaultdict

from rich.console import Console
from rich.table import Table

console = Console()

try:
    from janome.tokenizer import Tokenizer as JanomeTokenizer
    HAS_JANOME = True
except ImportError:
    HAS_JANOME = False


# ========== JLPT Vocabulary Database ==========
# Common JLPT vocabulary with levels
JLPT_VOCAB = {
    # N5 - Basic
    "愛": ("N5", "あい", "love, affection"),
    "青": ("N5", "あお", "blue, green"),
    "赤": ("N5", "あか", "red"),
    "明かり": ("N5", "あかり", "light, brightness"),
    "秋": ("N5", "あき", "autumn"),
    "朝": ("N5", "あさ", "morning"),
    "明日": ("N5", "あした", "tomorrow"),
    "遊ぶ": ("N5", "あそぶ", "to play, to have fun"),
    "頭": ("N5", "あたま", "head"),
    "新しい": ("N5", "あたらしい", "new"),
    "歩く": ("N5", "あるく", "to walk"),
    "雨": ("N5", "あめ", "rain"),
    "言う": ("N5", "いう", "to say, to tell"),
    "家": ("N5", "いえ/うち", "house, home"),
    "行く": ("N5", "いく", "to go"),
    "今": ("N5", "いま", "now"),
    "犬": ("N5", "いぬ", "dog"),
    "色": ("N5", "いろ", "color"),
    "食べる": ("N5", "たべる", "to eat"),
    "大きい": ("N5", "おおきい", "big, large"),
    "女": ("N5", "おんな", "woman"),
    "男": ("N5", "おとこ", "man"),
    "今日": ("N5", "きょう", "today"),
    "来る": ("N5", "くる", "to come"),
    "心": ("N5", "こころ", "heart, mind"),
    "声": ("N5", "こえ", "voice"),
    "見る": ("N5", "みる", "to see, to look"),
    "水": ("N5", "みず", "water"),
    "道": ("N5", "みち", "road, way"),
    "夜": ("N5", "よる", "night, evening"),
    "聞く": ("N5", "きく", "to listen, to ask"),
    "手": ("N5", "て", "hand"),
    "目": ("N5", "め", "eye"),
    "人": ("N5", "ひと", "person"),
    "日": ("N5", "ひ", "day, sun"),
    "空": ("N5", "そら", "sky"),
    "花": ("N5", "はな", "flower"),
    "待つ": ("N5", "まつ", "to wait"),
    "名前": ("N5", "なまえ", "name"),
    "何": ("N5", "なに/なん", "what"),
    "友達": ("N5", "ともだち", "friend"),
    "読む": ("N5", "よむ", "to read"),
    "書く": ("N5", "かく", "to write"),
    "話す": ("N5", "はなす", "to speak, to talk"),
    "走る": ("N5", "はしる", "to run"),
    "高い": ("N5", "たかい", "high, tall, expensive"),
    "小さい": ("N5", "ちいさい", "small, little"),
    "時間": ("N5", "じかん", "time"),
    "光": ("N5", "ひかり", "light"),
    "風": ("N5", "かぜ", "wind"),
    "雪": ("N5", "ゆき", "snow"),
    "星": ("N5", "ほし", "star"),
    "夢": ("N5", "ゆめ", "dream"),
    "君": ("N5", "きみ", "you (informal)"),
    "僕": ("N5", "ぼく", "I (male, informal)"),
    "私": ("N5", "わたし", "I (formal)"),
    # N4 - Elementary
    "想い": ("N4", "おもい", "thoughts, feelings"),
    "届く": ("N4", "とどく", "to reach, to be delivered"),
    "伝える": ("N4", "つたえる", "to convey, to transmit"),
    "変わる": ("N4", "かわる", "to change"),
    "消える": ("N4", "きえる", "to disappear, to vanish"),
    "始まる": ("N4", "はじまる", "to begin, to start"),
    "終わる": ("N4", "おわる", "to end, to finish"),
    "忘れる": ("N4", "わすれる", "to forget"),
    "覚える": ("N4", "おぼえる", "to remember, to memorize"),
    "探す": ("N4", "さがす", "to search, to look for"),
    "見つける": ("N4", "みつける", "to find, to discover"),
    "信じる": ("N4", "しんじる", "to believe"),
    "感じる": ("N4", "かんじる", "to feel, to sense"),
    "考える": ("N4", "かんがえる", "to think, to consider"),
    "決める": ("N4", "きめる", "to decide"),
    "守る": ("N4", "まもる", "to protect, to keep"),
    "離れる": ("N4", "はなれる", "to separate, to leave"),
    "繋がる": ("N4", "つながる", "to be connected"),
    "抱える": ("N4", "かかえる", "to hold, to embrace"),
    "生まれる": ("N4", "うまれる", "to be born"),
    "生きる": ("N4", "いきる", "to live"),
    "死ぬ": ("N4", "しぬ", "to die"),
    "笑う": ("N4", "わらう", "to laugh, to smile"),
    "泣く": ("N4", "なく", "to cry"),
    "叫ぶ": ("N4", "さけぶ", "to shout, to scream"),
    "歌う": ("N4", "うたう", "to sing"),
    "踊る": ("N4", "おどる", "to dance"),
    "祈る": ("N4", "いのる", "to pray"),
    "願い": ("N4", "ねがい", "wish, desire"),
    "涙": ("N4", "なみだ", "tears"),
    "笑顔": ("N4", "えがお", "smile"),
    "未来": ("N4", "みらい", "future"),
    "過去": ("N4", "かこ", "past"),
    "世界": ("N4", "せかい", "world"),
    "景色": ("N4", "けしき", "scenery, landscape"),
    "季節": ("N4", "きせつ", "season"),
    "春": ("N4", "はる", "spring"),
    "夏": ("N4", "なつ", "summer"),
    "冬": ("N4", "ふゆ", "winter"),
    "太陽": ("N4", "たいよう", "sun"),
    "月": ("N4", "つき", "moon, month"),
    "海": ("N4", "うみ", "sea, ocean"),
    "山": ("N4", "やま", "mountain"),
    "川": ("N4", "かわ", "river"),
    "鳥": ("N4", "とり", "bird"),
    "猫": ("N4", "ねこ", "cat"),
    "窓": ("N4", "まど", "window"),
    "扉": ("N4", "とびら", "door"),
    "鍵": ("N4", "かぎ", "key"),
    "言葉": ("N4", "ことば", "words, language"),
    "約束": ("N4", "やくそく", "promise"),
    "秘密": ("N4", "ひみつ", "secret"),
    "勇気": ("N4", "ゆうき", "courage"),
    "力": ("N4", "ちから", "power, strength"),
    "本当": ("N4", "ほんとう", "truth, reality"),
    "嘘": ("N4", "うそ", "lie"),
    "答え": ("N4", "こたえ", "answer"),
    "間違い": ("N4", "まちがい", "mistake"),
    # N3 - Intermediate
    "永遠": ("N3", "えいえん", "eternity, forever"),
    "運命": ("N3", "うんめい", "fate, destiny"),
    "奇跡": ("N3", "きせき", "miracle"),
    "記憶": ("N3", "きおく", "memory"),
    "思い出": ("N3", "おもいで", "memories, recollections"),
    "後悔": ("N3", "こうかい", "regret"),
    "孤独": ("N3", "こどく", "loneliness, solitude"),
    "幸せ": ("N3", "しあわせ", "happiness, blessing"),
    "切ない": ("N3", "せつない", "heartrending, bittersweet"),
    "儚い": ("N3", "はかない", "fleeting, transient"),
    "美しい": ("N3", "うつくしい", "beautiful"),
    "眩しい": ("N3", "まぶしい", "dazzling, bright"),
    "優しい": ("N3", "やさしい", "gentle, kind"),
    "寂しい": ("N3", "さびしい", "lonely, lonesome"),
    "苦しい": ("N3", "くるしい", "painful, agonizing"),
    "悲しい": ("N3", "かなしい", "sad, sorrowful"),
    "嬉しい": ("N3", "うれしい", "happy, glad"),
    "怖い": ("N3", "こわい", "scary, frightening"),
    "懐かしい": ("N3", "なつかしい", "nostalgic, dear"),
    "溢れる": ("N3", "あふれる", "to overflow"),
    "輝く": ("N3", "かがやく", "to shine, to sparkle"),
    "揺れる": ("N3", "ゆれる", "to shake, to sway"),
    "沈む": ("N3", "しずむ", "to sink"),
    "漂う": ("N3", "ただよう", "to drift, to float"),
    "刻む": ("N3", "きざむ", "to carve, to engrave"),
    "紡ぐ": ("N3", "つむぐ", "to spin, to weave"),
    "重ねる": ("N3", "かさねる", "to pile up, to repeat"),
    "見つめる": ("N3", "みつめる", "to stare at, to gaze"),
    "抱きしめる": ("N3", "だきしめる", "to embrace tightly"),
    "包む": ("N3", "つつむ", "to wrap, to envelop"),
    "響く": ("N3", "ひびく", "to resound, to echo"),
    "広がる": ("N3", "ひろがる", "to spread, to expand"),
    "立ち上がる": ("N3", "たちあがる", "to stand up, to rise"),
    "駆け出す": ("N3", "かけだす", "to start running"),
    "舞い降りる": ("N3", "まいおりる", "to descend, to alight"),
    "蘇る": ("N3", "よみがえる", "to revive, to be resurrected"),
    "胸": ("N3", "むね", "chest, heart"),
    "背中": ("N3", "せなか", "back"),
    "翼": ("N3", "つばさ", "wings"),
    "影": ("N3", "かげ", "shadow"),
    "闇": ("N3", "やみ", "darkness"),
    "炎": ("N3", "ほのお", "flame"),
    "鼓動": ("N3", "こどう", "heartbeat, pulsation"),
    "呼吸": ("N3", "こきゅう", "breathing"),
    "存在": ("N3", "そんざい", "existence"),
    "運命": ("N3", "うんめい", "fate, destiny"),
    "奇跡": ("N3", "きせき", "miracle"),
    "瞬間": ("N3", "しゅんかん", "moment, instant"),
    # N2 - Upper-Intermediate
    "彷徨う": ("N2", "さまよう", "to wander, to roam"),
    "葛藤": ("N2", "かっとう", "conflict, struggle"),
    "憧憬": ("N2", "どうけい", "longing, yearning"),
    "憂い": ("N2", "うれい", "sorrow, grief"),
    "煌めく": ("N2", "きらめく", "to glitter, to sparkle"),
    "囁く": ("N2", "ささやく", "to whisper"),
    "迸る": ("N2", "ほとばしる", "to gush out, to burst forth"),
    "翻る": ("N2", "ひるがえる", "to flutter, to wave"),
    "佇む": ("N2", "たたずむ", "to stand still, to linger"),
    "迸る": ("N2", "ほとばしる", "to burst forth"),
    "歪む": ("N2", "ゆがむ", "to distort, to warp"),
    "絡む": ("N2", "からむ", "to entangle"),
    "脆い": ("N2", "もろい", "fragile, brittle"),
    "蒼い": ("N2", "あおい", "pale, blue"),
    "仄か": ("N2", "ほのか", "faint, dim"),
    # N1 - Advanced
    "泡沫": ("N1", "うたかた", "ephemeral, bubble"),
    "刹那": ("N1", "せつな", "instant, moment"),
    "憧憬": ("N1", "しょうけい", "yearning, aspiration"),
    "蜃気楼": ("N1", "しんきろう", "mirage"),
    "黎明": ("N1", "れいめい", "dawn, daybreak"),
    "黄昏": ("N1", "たそがれ", "twilight, dusk"),
    "暁": ("N1", "あかつき", "dawn, daybreak"),
    "深淵": ("N1", "しんえん", "abyss, depths"),
    "咆哮": ("N1", "ほうこう", "roar, howl"),
    "残響": ("N1", "ざんきょう", "reverberation, echo"),
}


# ========== Grammar Pattern Database ==========
GRAMMAR_PATTERNS = {
    # Basic patterns (N5-N4)
    "〜たい": {
        "pattern": re.compile(r'(.+)たい$'),
        "level": "N5",
        "meaning": "want to do ~",
        "explanation": "动词ます形去掉「ます」+ たい，表示说话人的愿望。例：食べたい（想吃）",
        "example": "会いたい → 想要见面",
    },
    "〜ている": {
        "pattern": re.compile(r'(.+)ている'),
        "level": "N5",
        "meaning": "is doing ~ / state of being",
        "explanation": "表示动作的持续或状态的存续。例：走っている（正在跑）",
        "example": "見ている → 正在看",
    },
    "〜ないで": {
        "pattern": re.compile(r'(.+)ないで'),
        "level": "N5",
        "meaning": "without doing ~",
        "explanation": "动词ない形 + で，表示不做某事的状态。例：食べないで（不吃就...）",
        "example": "泣かないで → 请不要哭",
    },
    "〜られる": {
        "pattern": re.compile(r'(.+)られる'),
        "level": "N4",
        "meaning": "can do ~ / passive / potential",
        "explanation": "可能态/被动态。一段动词去掉「る」+ られる。例：食べられる（能吃/被吃）",
        "example": "見られる → 能被看到/被看",
    },
    "〜てしまう": {
        "pattern": re.compile(r'(.+)てしまう'),
        "level": "N4",
        "meaning": "end up doing ~ / completely",
        "explanation": "表示动作的完了或意外结果。例：食べてしまう（不小心吃了/吃完了）",
        "example": "忘れてしまう → 不小心忘了",
    },
    "〜ように": {
        "pattern": re.compile(r'(.+)ように'),
        "level": "N4",
        "meaning": "so that ~ / like ~",
        "explanation": "表示目的或比喻。例：忘れないように（为了不忘记）",
        "example": "届くように → 希望传达得到",
    },
    "〜ながら": {
        "pattern": re.compile(r'(.+)ながら'),
        "level": "N4",
        "meaning": "while doing ~",
        "explanation": "动词ます形 + ながら，表示同时进行两个动作。",
        "example": "歌いながら → 一边唱一边...",
    },
    # Intermediate patterns (N3)
    "〜てくる": {
        "pattern": re.compile(r'(.+)てくる'),
        "level": "N3",
        "meaning": "has been doing ~ / come to ~",
        "explanation": "表示变化从过去持续到现在，或某种状态开始显现。",
        "example": "変わってきた → 逐渐改变了",
    },
    "〜ていく": {
        "pattern": re.compile(r'(.+)ていく'),
        "level": "N3",
        "meaning": "will continue to ~ / going to ~",
        "explanation": "表示从现在向未来的变化趋势。",
        "example": "消えていく → 渐渐消失",
    },
    "〜てほしい": {
        "pattern": re.compile(r'(.+)てほしい'),
        "level": "N3",
        "meaning": "want someone to do ~",
        "explanation": "希望别人做某事。例：見てほしい（希望你能看看）",
        "example": "聞いてほしい → 希望你能听",
    },
    "〜しかない": {
        "pattern": re.compile(r'(.+)しかない'),
        "level": "N3",
        "meaning": "nothing but ~ / have no choice but to",
        "explanation": "表示只有限定的选择。",
        "example": "信じるしかない → 只能选择相信",
    },
    "〜ばかり": {
        "pattern": re.compile(r'(.+)ばかり'),
        "level": "N3",
        "meaning": "only ~ / nothing but ~",
        "explanation": "表示尽是某种情况。",
        "example": "泣いてばかり → 一直在哭",
    },
    "〜ほど": {
        "pattern": re.compile(r'(.+)ほど'),
        "level": "N3",
        "meaning": "to the extent that ~",
        "explanation": "表示程度。歌词中常用于夸张表达。",
        "example": "死にたいほど → 痛苦到想死的程度",
    },
    "〜のに": {
        "pattern": re.compile(r'(.+)のに'),
        "level": "N3",
        "meaning": "even though ~ / despite ~",
        "explanation": "表示转折，带有不满或遗憾的语气。",
        "example": "好きなのに → 明明喜欢却...",
    },
    # Advanced patterns (N2-N1)
    "〜ずに": {
        "pattern": re.compile(r'(.+)ずに'),
        "level": "N2",
        "meaning": "without doing ~",
        "explanation": "「ない」的文语形式，歌词中常用。例：見ずに（不看就...）",
        "example": "止めずに → 不停下来地...",
    },
    "〜まま": {
        "pattern": re.compile(r'(.+)まま'),
        "level": "N3",
        "meaning": "as it is ~ / while still ~",
        "explanation": "保持某种状态不变。",
        "example": "夢のまま → 就这样在梦中",
    },
    "〜ごと": {
        "pattern": re.compile(r'(.+)ごと'),
        "level": "N2",
        "meaning": "together with ~ / every ~",
        "explanation": "表示连同一起或每隔。",
        "example": "全部まるごと → 全部一起",
    },
    "〜ぬ": {
        "pattern": re.compile(r'(.+)ぬ$'),
        "level": "N2",
        "meaning": "not ~ (literary negation)",
        "explanation": "「ない」的文语形式。歌词中常见。例：見ぬ（不看）",
        "example": "届かぬ → 传达不到（文语）",
    },
    "〜てやる": {
        "pattern": re.compile(r'(.+)てやる'),
        "level": "N3",
        "meaning": "will do ~ (determination)",
        "explanation": "带有强烈意志的表达。",
        "example": "見せてやる → 让你见识一下",
    },
    "〜き": {
        "pattern": re.compile(r'(.+)き$'),
        "level": "N2",
        "meaning": "~ (adjective noun form, literary)",
        "explanation": "形容词的文语形式。例：美しき（美丽的）",
        "example": "優しき → 温柔的（文语）",
    },
}


class JPAnalyzer:
    """Analyze Japanese lyrics for vocabulary and grammar knowledge points."""

    def __init__(self, config: dict):
        self.config = config
        self.analysis_cfg = config.get("analysis", {})
        self.highlight_pos = set(self.analysis_cfg.get("highlight_pos", []))
        self.max_notes = self.analysis_cfg.get("max_notes", 15)
        self.data_dir = Path(config["paths"]["data_dir"])
        self.output_dir = self.data_dir / "analysis"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize tokenizer
        self.tokenizer = None
        if HAS_JANOME:
            self.tokenizer = JanomeTokenizer()
            console.print("[green]Janome tokenizer initialized[/green]")
        else:
            console.print("[yellow]Janome not available, using fallback analysis[/yellow]")

    def tokenize_line(self, text: str) -> list[dict]:
        """Tokenize a Japanese text line using Janome."""
        if not self.tokenizer:
            return self._fallback_tokenize(text)

        tokens = []
        for token in self.tokenizer.tokenize(text):
            parts = token.part_of_speech.split(",")
            tokens.append({
                "surface": token.surface,
                "reading": token.reading if token.reading != '*' else token.surface,
                "base_form": token.base_form if token.base_form != '*' else token.surface,
                "pos": parts[0] if parts else "unknown",
                "pos_detail": parts[1] if len(parts) > 1 else "",
                "conjugation_type": parts[2] if len(parts) > 2 else "",
                "conjugation_form": parts[3] if len(parts) > 3 else "",
            })
        return tokens

    def _fallback_tokenize(self, text: str) -> list[dict]:
        """Simple fallback tokenizer for when Janome is unavailable."""
        # Split on common boundaries
        tokens = []
        # Simple character-based heuristic
        current = ""
        for char in text:
            if char in " 、。！？「」『』（）()ー～":
                if current:
                    tokens.append({
                        "surface": current,
                        "reading": current,
                        "base_form": current,
                        "pos": "unknown",
                    })
                    current = ""
                if char not in " ":
                    tokens.append({
                        "surface": char,
                        "reading": char,
                        "base_form": char,
                        "pos": "記号",
                    })
            else:
                current += char
        if current:
            tokens.append({
                "surface": current,
                "reading": current,
                "base_form": current,
                "pos": "unknown",
            })
        return tokens

    def find_vocabulary(self, tokens: list[dict]) -> list[dict]:
        """Find JLPT vocabulary in tokenized text."""
        found = []
        seen = set()

        for token in tokens:
            surface = token["surface"]
            base = token["base_form"]

            # Check both surface and base form
            for word, info in JLPT_VOCAB.items():
                if (surface == word or base == word) and word not in seen:
                    seen.add(word)
                    found.append({
                        "word": word,
                        "reading": info[1],
                        "meaning": info[2],
                        "jlpt_level": info[0],
                        "pos": token.get("pos", ""),
                    })

            # Also check compound words (2-3 char combinations)
            if token.get("pos") in ("名詞", "動詞", "形容詞"):
                if surface in JLPT_VOCAB and surface not in seen:
                    seen.add(surface)
                    info = JLPT_VOCAB[surface]
                    found.append({
                        "word": surface,
                        "reading": info[1],
                        "meaning": info[2],
                        "jlpt_level": info[0],
                        "pos": token.get("pos", ""),
                    })

        return found

    def find_grammar(self, text: str) -> list[dict]:
        """Find grammar patterns in a text line."""
        found = []
        for pattern_name, info in GRAMMAR_PATTERNS.items():
            if info["pattern"].search(text):
                found.append({
                    "pattern": pattern_name,
                    "level": info["level"],
                    "meaning": info["meaning"],
                    "explanation": info["explanation"],
                    "example": info["example"],
                    "in_context": text,
                })
        return found

    def analyze_line(self, line: dict) -> dict:
        """
        Analyze a single lyrics line for Japanese knowledge.
        
        Args:
            line: Dict with 'text', 'index', 'start', 'end' fields
            
        Returns:
            Enriched line dict with vocabulary and grammar notes
        """
        text = line["text"]
        tokens = self.tokenize_line(text)
        vocab = self.find_vocabulary(tokens)
        grammar = self.find_grammar(text)

        # Build reading aid (furigana-style)
        reading_parts = []
        for token in tokens:
            if token["surface"] != token["reading"] and token.get("pos") != "記号":
                reading_parts.append({
                    "text": token["surface"],
                    "reading": token["reading"],
                })
            else:
                reading_parts.append({
                    "text": token["surface"],
                    "reading": None,
                })

        return {
            **line,
            "tokens": tokens,
            "vocabulary": vocab,
            "grammar": grammar,
            "reading_parts": reading_parts,
            "has_notes": bool(vocab or grammar),
        }

    def analyze_song(self, serialized_lyrics: dict) -> dict:
        """
        Analyze a complete song's lyrics.
        
        Args:
            serialized_lyrics: Serialized lyrics dict from LyricsSerializer
            
        Returns:
            Analysis result dict with all knowledge points
        """
        lines = serialized_lyrics.get("lines", [])
        title = serialized_lyrics.get("title", "Unknown")
        artist = serialized_lyrics.get("artist", "Unknown")

        console.print(f"\n  Analyzing: [cyan]{title}[/cyan] by [green]{artist}[/green]")

        # Analyze each line
        analyzed_lines = []
        all_vocabulary = {}  # Deduplicate vocabulary
        all_grammar = []     # Collect all grammar points
        jlpt_distribution = defaultdict(int)

        for line in lines:
            analyzed = self.analyze_line(line)
            analyzed_lines.append(analyzed)

            # Collect vocabulary
            for v in analyzed["vocabulary"]:
                if v["word"] not in all_vocabulary:
                    all_vocabulary[v["word"]] = v
                    jlpt_distribution[v["jlpt_level"]] += 1

            # Collect grammar
            for g in analyzed["grammar"]:
                all_grammar.append(g)

        # Select top knowledge notes (limit to max_notes)
        top_notes = self._select_top_notes(analyzed_lines, all_vocabulary, all_grammar)

        # Build result
        result = {
            "title": title,
            "artist": artist,
            "song_id": serialized_lyrics.get("song_id", ""),
            "total_lines": len(analyzed_lines),
            "lines_with_notes": sum(1 for l in analyzed_lines if l["has_notes"]),
            "jlpt_distribution": dict(jlpt_distribution),
            "vocabulary_count": len(all_vocabulary),
            "grammar_count": len(all_grammar),
            "top_notes": top_notes,
            "analyzed_lines": analyzed_lines,
        }

        # Display summary
        console.print(f"    Vocabulary: {len(all_vocabulary)} words, Grammar: {len(all_grammar)} patterns")
        console.print(f"    JLPT distribution: {dict(jlpt_distribution)}")
        console.print(f"    Lines with notes: {result['lines_with_notes']}/{result['total_lines']}")

        return result

    def _select_top_notes(self, lines: list[dict], vocab: dict, grammar: list) -> list[dict]:
        """Select the most important knowledge notes for display."""
        notes = []

        # Priority: N5 > N4 > N3 > N2 > N1 for learners
        jlpt_priority = {"N5": 5, "N4": 4, "N3": 3, "N2": 2, "N1": 1}

        # Score vocabulary notes
        for word, info in vocab.items():
            score = jlpt_priority.get(info["jlpt_level"], 0)
            # Boost if word appears multiple times
            count = sum(1 for l in lines if any(v["word"] == word for v in l.get("vocabulary", [])))
            score += min(count - 1, 3)  # Up to +3 for repeated words
            notes.append({
                "type": "vocabulary",
                "score": score,
                "data": info,
                "line_indices": [
                    l["index"] for l in lines
                    if any(v["word"] == word for v in l.get("vocabulary", []))
                ],
            })

        # Score grammar notes
        grammar_seen = set()
        for g in grammar:
            key = g["pattern"]
            if key in grammar_seen:
                continue
            grammar_seen.add(key)
            score = jlpt_priority.get(g["level"], 0) + 1  # Grammar gets a slight boost
            notes.append({
                "type": "grammar",
                "score": score,
                "data": g,
                "line_indices": [
                    l["index"] for l in lines
                    if any(gr["pattern"] == key for gr in l.get("grammar", []))
                ],
            })

        # Sort by score and limit
        notes.sort(key=lambda x: x["score"], reverse=True)
        return notes[:self.max_notes]

    def analyze_batch(self, serialized_list: list[dict]) -> list[dict]:
        """Analyze a batch of serialized lyrics."""
        results = []
        console.print(f"\n[bold cyan]=== Analyzing Japanese Knowledge Points ===[/bold cyan]")

        for i, serialized in enumerate(serialized_list, 1):
            console.print(f"\n  [{i}/{len(serialized_list)}]", end="")
            result = self.analyze_song(serialized)

            # Save to file
            song_id = serialized.get("song_id", f"song_{i}")
            safe_id = re.sub(r'[^\w\-]', '_', song_id)
            output_path = self.output_dir / f"{safe_id}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)

            results.append(result)

        console.print(f"\n[green]Analysis complete: {len(results)} songs processed[/green]")
        return results
