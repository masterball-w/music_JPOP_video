"""
AI Translation Module
=====================
Translates English vocabulary/grammar explanations to Chinese using AI APIs.
Supports OpenAI, DeepSeek, Zhipu GLM, and Ollama (local).
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from rich.console import Console

console = Console()


class AITranslator:
    """AI-powered translator for Japanese learning content."""

    def __init__(self, config: dict):
        self.config = config.get("ai", {})
        self.provider = self.config.get("provider", "deepseek")
        self.api_key = self.config.get("api_key", "")
        self.base_url = self.config.get("base_url", "")
        self.model = self.config.get("model", "deepseek-chat")
        self.timeout = self.config.get("timeout", 30)
        self.batch_size = self.config.get("batch_size", 20)

        # Cache
        self.cache_enabled = self.config.get("cache_enabled", True)
        cache_file = self.config.get("cache_file", "data/translation_cache.json")
        self.cache_path = Path(cache_file) if not Path(cache_file).is_absolute() else Path(cache_file)
        self._cache = {}
        self._cache_dirty = False
        if self.cache_enabled:
            self._load_cache()

        # Provider endpoints
        self.endpoints = {
            "openai": "https://api.openai.com/v1/chat/completions",
            "deepseek": "https://api.deepseek.com/v1/chat/completions",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            "ollama": "http://localhost:11434/api/chat",
        }

    def _load_cache(self):
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                console.print(f"[dim]Loaded {len(self._cache)} cached translations[/dim]")
            except Exception:
                self._cache = {}

    def _save_cache(self):
        if self._cache_dirty and self.cache_enabled:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
            self._cache_dirty = False

    def _make_cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _get_cached(self, text: str) -> Optional[str]:
        if not self.cache_enabled:
            return None
        key = self._make_cache_key(text)
        return self._cache.get(key)

    def _set_cached(self, text: str, result: str):
        if not self.cache_enabled:
            return
        key = self._make_cache_key(text)
        self._cache[key] = result
        self._cache_dirty = True

    def _call_api(self, prompt: str) -> Optional[str]:
        """Call the AI API and return the response text."""
        if not HAS_REQUESTS:
            console.print("[red]requests library not installed. pip install requests[/red]")
            return None

        # Build request
        if self.provider == "ollama":
            url = self.endpoints["ollama"]
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
            headers = {"Content-Type": "application/json"}
        else:
            url = self.base_url or self.endpoints.get(self.provider, self.endpoints["deepseek"])
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a Japanese language expert. Translate English explanations to concise Chinese. Output ONLY the translation, nothing else."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 200,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            if self.provider == "ollama":
                return data.get("message", {}).get("content", "").strip()
            else:
                return data["choices"][0]["message"]["content"].strip()
        except requests.exceptions.RequestException as e:
            console.print(f"[yellow]API request failed: {e}[/yellow]")
            return None
        except (KeyError, IndexError) as e:
            console.print(f"[yellow]API response parse error: {e}[/yellow]")
            return None

    def translate_meaning(self, word: str, english_meaning: str) -> str:
        """
        Translate an English word meaning to Chinese.
        Returns Chinese translation or original English if translation fails.
        """
        # Check cache first
        cache_key = f"word:{word}:{english_meaning}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        prompt = f'请将以下日语词汇的英文释义翻译为简洁的中文（2-6个字）：\n词汇：{word}\n英文释义：{english_meaning}\n\n只输出中文翻译，不要其他内容。'

        result = self._call_api(prompt)
        if result:
            # Clean up response
            result = result.strip().strip('"').strip("'").strip("。").strip(".")
            self._set_cached(cache_key, result)
            return result

        # Fallback: return original
        return english_meaning

    def translate_explanation(self, pattern_name: str, english_explanation: str) -> str:
        """Translate a grammar explanation to Chinese."""
        cache_key = f"grammar:{pattern_name}:{english_explanation}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        prompt = f'请将以下日语语法点的英文解释翻译为简洁的中文：\n语法：{pattern_name}\n英文解释：{english_explanation}\n\n只输出中文翻译，不要其他内容。'

        result = self._call_api(prompt)
        if result:
            result = result.strip().strip('"').strip("'").strip("。").strip(".")
            self._set_cached(cache_key, result)
            return result

        return english_explanation

    def translate_batch(self, items: list[dict]) -> list[dict]:
        """
        Translate a batch of vocabulary/grammar items.
        Each item should have 'word'/'pattern', 'meaning'/'explanation' fields.
        Returns items with 'meaning_cn'/'explanation_cn' added.
        """
        # Build batch prompt
        if not items:
            return items

        lines = []
        for i, item in enumerate(items):
            if "word" in item:
                lines.append(f"{i+1}. 词汇: {item['word']} - {item.get('meaning', '')}")
            elif "pattern" in item:
                lines.append(f"{i+1}. 语法: {item['pattern']} - {item.get('explanation', '')}")

        batch_text = "\n".join(lines)
        prompt = f"请将以下日语学习内容的英文释义翻译为简洁的中文，按编号输出：\n\n{batch_text}\n\n格式：编号. 中文翻译（每个翻译2-8个字，语法解释可以稍长）。只输出翻译结果。"

        # Check if all cached
        all_cached = True
        for item in items:
            if "word" in item:
                key = f"word:{item['word']}:{item.get('meaning', '')}"
            else:
                key = f"grammar:{item.get('pattern', '')}:{item.get('explanation', '')}"
            if not self._get_cached(key):
                all_cached = False
                break

        if all_cached:
            for item in items:
                if "word" in item:
                    key = f"word:{item['word']}:{item.get('meaning', '')}"
                    item["meaning_cn"] = self._get_cached(key)
                else:
                    key = f"grammar:{item.get('pattern', '')}:{item.get('explanation', '')}"
                    item["explanation_cn"] = self._get_cached(key)
            return items

        result = self._call_api(prompt)
        if not result:
            # Fallback: translate individually
            for item in items:
                if "word" in item:
                    item["meaning_cn"] = self.translate_meaning(item["word"], item.get("meaning", ""))
                else:
                    item["explanation_cn"] = self.translate_explanation(
                        item.get("pattern", ""), item.get("explanation", "")
                    )
            return items

        # Parse batch response
        translated_lines = [l.strip() for l in result.split("\n") if l.strip()]
        for i, item in enumerate(items):
            if i < len(translated_lines):
                # Extract translation (remove leading number)
                line = translated_lines[i]
                # Remove patterns like "1. ", "1、", "1："
                line = re.sub(r"^\d+[\.\、\：\:\s]+", "", line).strip()
                line = line.strip('"').strip("'").strip("。").strip(".")

            if "word" in item:
                item["meaning_cn"] = line if i < len(translated_lines) else item.get("meaning", "")
                key = f"word:{item['word']}:{item.get('meaning', '')}"
                self._set_cached(key, item["meaning_cn"])
            else:
                item["explanation_cn"] = line if i < len(translated_lines) else item.get("explanation", "")
                key = f"grammar:{item.get('pattern', '')}:{item.get('explanation', '')}"
                self._set_cached(key, item["explanation_cn"])

        return items

    def translate_song_analysis(self, analysis: dict) -> dict:
        """
        Translate all vocabulary and grammar meanings in a song analysis to Chinese.
        Adds 'meaning_cn' to vocabulary items and 'explanation_cn' to grammar items.
        """
        console.print(f"\n[bold cyan]Translating explanations to Chinese...[/bold cyan]")

        # Collect all unique items to translate
        vocab_items = []
        grammar_items = []
        seen_vocab = set()
        seen_grammar = set()

        # From top_notes
        for note in analysis.get("top_notes", []):
            data = note.get("data", {})
            if note.get("type") == "vocabulary":
                key = data.get("word", "")
                if key and key not in seen_vocab:
                    seen_vocab.add(key)
                    vocab_items.append({
                        "word": key,
                        "reading": data.get("reading", ""),
                        "meaning": data.get("meaning", ""),
                        "jlpt_level": data.get("jlpt_level", ""),
                    })
            elif note.get("type") == "grammar":
                key = data.get("pattern", "")
                if key and key not in seen_grammar:
                    seen_grammar.add(key)
                    grammar_items.append({
                        "pattern": key,
                        "level": data.get("level", ""),
                        "explanation": data.get("explanation", ""),
                    })

        # From analyzed_lines
        for line in analysis.get("analyzed_lines", []):
            for v in line.get("vocabulary", []):
                key = v.get("word", "")
                if key and key not in seen_vocab:
                    seen_vocab.add(key)
                    vocab_items.append({
                        "word": key,
                        "reading": v.get("reading", ""),
                        "meaning": v.get("meaning", ""),
                        "jlpt_level": v.get("jlpt_level", ""),
                    })
            for g in line.get("grammar", []):
                key = g.get("pattern", "")
                if key and key not in seen_grammar:
                    seen_grammar.add(key)
                    grammar_items.append({
                        "pattern": key,
                        "level": g.get("level", ""),
                        "explanation": g.get("explanation", ""),
                    })

        console.print(f"  Vocabulary items: {len(vocab_items)}")
        console.print(f"  Grammar items: {len(grammar_items)}")

        # Translate in batches
        total = len(vocab_items) + len(grammar_items)
        if total == 0:
            console.print("  [dim]Nothing to translate[/dim]")
            return analysis

        # Translate vocabulary
        for i in range(0, len(vocab_items), self.batch_size):
            batch = vocab_items[i:i + self.batch_size]
            self.translate_batch(batch)
            console.print(f"  [dim]Vocab batch {i // self.batch_size + 1} done[/dim]")

        # Translate grammar
        for i in range(0, len(grammar_items), self.batch_size):
            batch = grammar_items[i:i + self.batch_size]
            self.translate_batch(batch)
            console.print(f"  [dim]Grammar batch {i // self.batch_size + 1} done[/dim]")

        # Build lookup maps
        vocab_map = {item["word"]: item.get("meaning_cn", item["meaning"]) for item in vocab_items}
        grammar_map = {item["pattern"]: item.get("explanation_cn", item["explanation"]) for item in grammar_items}

        # Apply translations to analysis
        for note in analysis.get("top_notes", []):
            data = note.get("data", {})
            if note.get("type") == "vocabulary" and data.get("word") in vocab_map:
                data["meaning"] = vocab_map[data["word"]]
            elif note.get("type") == "grammar" and data.get("pattern") in grammar_map:
                data["explanation"] = grammar_map[data["pattern"]]

        for line in analysis.get("analyzed_lines", []):
            for v in line.get("vocabulary", []):
                if v.get("word") in vocab_map:
                    v["meaning"] = vocab_map[v["word"]]
            for g in line.get("grammar", []):
                if g.get("pattern") in grammar_map:
                    g["explanation"] = grammar_map[g["pattern"]]

        # Save cache
        self._save_cache()

        console.print(f"  [green]Translation complete![/green]")
        return analysis

    def flush_cache(self):
        """Force save cache to disk."""
        self._save_cache()


# Need re for batch parsing
import re
