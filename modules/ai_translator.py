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
            if self.base_url:
                url = self.base_url.rstrip("/") + "/chat/completions"
            else:
                url = self.endpoints.get(self.provider, self.endpoints["deepseek"])
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

    def analyze_lyrics_with_ai(self, analysis: dict) -> dict:
        """
        使用AI深度分析歌词，提取词汇和语法知识点（中文释义）。
        将AI分析结果合并到现有analysis中，补充本地分析遗漏的词汇。
        """
        console.print(f"\n[bold cyan]AI深度分析歌词知识点...[/bold cyan]")

        lines = analysis.get("analyzed_lines", [])
        if not lines:
            return analysis

        # 收集已有词汇，避免重复
        existing_vocab = set()
        for line in lines:
            for v in line.get("vocabulary", []):
                existing_vocab.add(v.get("word", ""))

        # 按批次处理歌词行（每批3行，减少单次请求负载）
        batch_size = 3
        for start in range(0, len(lines), batch_size):
            batch = lines[start:start + batch_size]
            batch_num = start // batch_size + 1
            total_batches = (len(lines) + batch_size - 1) // batch_size

            # 构建提示词，包含每行已有的词汇以避免重复
            lyrics_text = ""
            for i, l in enumerate(batch):
                existing_words = [v.get("word", "") for v in l.get("vocabulary", [])]
                existing_grammars = [g.get("pattern", "") for g in l.get("grammar", [])]
                existing_str = ""
                if existing_words or existing_grammars:
                    existing_str = f"（已提取: {', '.join(existing_words + existing_grammars)}）"
                lyrics_text += f"{i+1}. {l.get('text', '')} {existing_str}\n"

            prompt = f"""分析以下日语歌词，提取每行中尚未提取的重要词汇和语法点。

{lyrics_text}

要求：
1. 每行提取1-3个重要词汇（动词、形容词、副词优先）
2. 跳过已提取的词汇和语法点
3. 跳过助词（は、が、の等）和常见代词（私、君等）
4. 释义用简洁中文（2-6个字）
5. 确保所有动词都被提取

输出纯JSON（不要markdown代码块，不要解释）：
[{{"line":1,"items":[{{"type":"vocabulary","word":"溶ける","reading":"とける","meaning":"溶解","jlpt_level":"N3"}}]}}]"""

            # 检查缓存
            cache_key = f"analysis:{hashlib.md5(lyrics_text.encode()).hexdigest()}"
            cached = self._get_cached(cache_key)

            if cached:
                try:
                    result_json = json.loads(cached)
                except json.JSONDecodeError:
                    result_json = None
            else:
                result = self._call_api_analyze(prompt)
                if result:
                    try:
                        # 清理markdown代码块标记
                        cleaned = result.strip()
                        if cleaned.startswith('```'):
                            # 移除 ```json 或 ``` 标记
                            lines = cleaned.split('\n')
                            # 移除首行（```json 或 ```）
                            lines = lines[1:]
                            # 移除末尾的 ```
                            if lines and lines[-1].strip() == '```':
                                lines = lines[:-1]
                            cleaned = '\n'.join(lines)

                        # 提取JSON部分
                        json_start = cleaned.find('[')
                        json_end = cleaned.rfind(']') + 1
                        if json_start >= 0 and json_end > json_start:
                            json_str = cleaned[json_start:json_end]
                            result_json = json.loads(json_str)
                            self._set_cached(cache_key, json_str)
                        else:
                            result_json = None
                    except (json.JSONDecodeError, Exception) as e:
                        console.print(f"  [yellow]JSON解析失败: {e}[/yellow]")
                        result_json = None
                else:
                    result_json = None

            if not result_json:
                console.print(f"  [yellow]批次 {batch_num}/{total_batches} 解析失败，跳过[/yellow]")
                continue

            # 将AI分析结果合并到analysis中
            for item in result_json:
                line_num = item.get("line", 0) - 1  # 转为0-based索引
                if line_num < 0 or line_num >= len(batch):
                    continue

                actual_idx = start + line_num
                target_line = lines[actual_idx]

                for ai_item in item.get("items", []):
                    if ai_item.get("type") == "vocabulary":
                        word = ai_item.get("word", "")
                        if not word or word in existing_vocab:
                            continue
                        existing_vocab.add(word)
                        target_line.setdefault("vocabulary", []).append({
                            "word": word,
                            "reading": ai_item.get("reading", ""),
                            "meaning": ai_item.get("meaning", ""),
                            "jlpt_level": ai_item.get("jlpt_level", ""),
                            "pos": "",
                            "source": "ai",
                        })
                        # 标记该行有笔记
                        target_line["has_notes"] = True

                    elif ai_item.get("type") == "grammar":
                        # AI可能用"pattern"或"word"字段
                        pattern = ai_item.get("pattern", "") or ai_item.get("word", "")
                        if not pattern:
                            continue
                        # 标准化比较：去除波浪线差异（〜/～/~）
                        def _normalize_pattern(p):
                            return p.replace("〜", "").replace("～", "").replace("~", "").strip()
                        pattern_norm = _normalize_pattern(pattern)
                        existing_grammar = {_normalize_pattern(g.get("pattern", "")) for g in target_line.get("grammar", [])}
                        if pattern_norm in existing_grammar:
                            continue
                        target_line.setdefault("grammar", []).append({
                            "pattern": pattern,
                            "meaning": ai_item.get("meaning", ""),
                            "explanation": ai_item.get("explanation", "") or ai_item.get("meaning", ""),
                            "level": ai_item.get("jlpt_level", ""),
                            "example": "",
                            "source": "ai",
                        })
                        target_line["has_notes"] = True

            console.print(f"  [dim]批次 {batch_num}/{total_batches} 完成[/dim]")

        # 保存缓存
        self._save_cache()

        # 重新统计
        total_vocab = sum(len(l.get("vocabulary", [])) for l in lines)
        total_grammar = sum(len(l.get("grammar", [])) for l in lines)
        lines_with_notes = sum(1 for l in lines if l.get("has_notes"))
        console.print(f"  [green]AI分析完成！词汇: {total_vocab}, 语法: {total_grammar}, 有笔记行: {lines_with_notes}/{len(lines)}[/green]")

        return analysis

    def _call_api_analyze(self, prompt: str) -> Optional[str]:
        """调用AI API进行歌词分析（允许更长输出）"""
        if not HAS_REQUESTS:
            return None

        if self.base_url:
            url = self.base_url.rstrip("/") + "/chat/completions"
        else:
            url = self.endpoints.get(self.provider, self.endpoints["deepseek"])

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是日语教育专家。只输出纯JSON，不要markdown代码块。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 800,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            console.print(f"  [yellow]AI分析API错误: {e}[/yellow]")
            return None


# Need re for batch parsing
import re
