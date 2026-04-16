"""
Auto-title + appreciation service — one AI call for title, theme, key points, golden quotes.
Uses OpenCC post-processing to guarantee Traditional Chinese output.
"""

import os
import sys
import json
from opencc import OpenCC

# s2twp = Simplified → Traditional (Taiwan phrases, e.g. 軟件→軟體, 信息→資訊)
_s2tw = OpenCC('s2twp')

# MEEI_PATH is auto-injected by CloudPipe (deploy.js / ecosystem.config.js).
# For standalone runs, set MEEI_PATH=/path/to/meei/python/src manually.
MEEI_PATH = os.environ.get("MEEI_PATH")
if not MEEI_PATH:
    raise RuntimeError("MEEI_PATH environment variable not set")
if MEEI_PATH not in sys.path:
    sys.path.insert(0, MEEI_PATH)

from meei.chat import chat  # noqa: E402

SYSTEM_PROMPT = """You are a bilingual content analyst. Given an English video transcript,
produce a JSON object with a concise title AND content analysis.

CRITICAL: All Chinese output MUST be 繁體中文（台灣用語）. 絕對不可以用簡體中文。
例如：使用「影片」不是「视频」，使用「軟體」不是「软件」，使用「資訊」不是「信息」。

{
  "title": "繁體中文標題（台灣用語）",
  "theme": "一句話描述主題（繁體中文，台灣用語）",
  "keyPoints": ["重點1", "重點2", "重點3"],
  "goldenQuotes": [
    {"en": "Original English quote", "zh": "繁體中文翻譯"},
    {"en": "...", "zh": "..."},
    {"en": "...", "zh": "..."}
  ]
}

Rules:
- title: 繁體中文（台灣用語）, 8-18 字, 要像人寫的口語化摘要, 讓人一看就知道影片在講什麼
  好標題範例: "馬斯克談為什麼要移民火星", "如何用三個月學好英文", "為什麼你總是拖延"
  壞標題範例: "成功的秘訣", "學習方法論", "生活的真諦" (太籠統、沒記憶點)
  原則: 具體 > 抽象, 口語 > 書面, 有主角/動作 > 純概念
- theme: 1 sentence in 繁體中文（台灣用語）, summarizing the core message
- keyPoints: exactly 3 bullet points in 繁體中文（台灣用語）
- goldenQuotes: exactly 3 memorable sentences from the original English, with 繁體中文翻譯
- Output ONLY valid JSON, no markdown fences or extra text"""

LYRICS_SYSTEM_PROMPT = """You are a bilingual music/lyrics analyst. Given song lyrics (transcribed from audio),
produce a JSON object with a title AND lyrics analysis.

CRITICAL: All Chinese output MUST be 繁體中文（台灣用語）. 絕對不可以用簡體中文。

{
  "title": "歌名 — 歌手 (max 25 chars)",
  "theme": "一句話描述歌曲核心意境（繁體中文，台灣用語）",
  "keyPoints": ["主題意境1", "修辭手法/情感表達2", "歌曲結構或風格特色3"],
  "goldenQuotes": [
    {"en": "Most impactful lyric line", "zh": "繁體中文翻譯"},
    {"en": "...", "zh": "..."},
    {"en": "...", "zh": "..."}
  ]
}

Rules:
- title: Try to identify song name and artist from lyrics/context. Format: "歌名 — 歌手"
- theme: Describe the emotional core and imagery of the song in 繁體中文（台灣用語）
- keyPoints: 3 points covering: (1) core theme/emotion, (2) notable lyrical techniques (metaphor, repetition, imagery), (3) song mood/style
- goldenQuotes: 3 most memorable/beautiful lyric lines with 繁體中文翻譯
- Pick lyrics that are poetic, emotionally powerful, or capture the song's essence
- Output ONLY valid JSON, no markdown fences or extra text"""

CHINESE_SYSTEM_PROMPT = """你是一位內容分析專家。根據以下的繁體中文字幕內容，生成標題和內容分析。

所有輸出必須是繁體中文（台灣用語）。絕對不可以用簡體中文。

輸出格式（純 JSON，不要 markdown）：
{
  "title": "繁體中文標題（台灣用語，8-18字）",
  "theme": "一句話描述主題",
  "keyPoints": ["重點1", "重點2", "重點3"],
  "goldenQuotes": [
    {"en": "Original English quote (if available)", "zh": "對應的繁體中文"},
    {"en": "...", "zh": "..."},
    {"en": "...", "zh": "..."}
  ]
}

標題規則：
- 8-18 字，口語化，讓人一看就知道影片在講什麼
- 好標題：「馬斯克談為什麼要移民火星」、「如何用三個月學好英文」、「為什麼你總是拖延」
- 壞標題：「成功的秘訣」、「學習方法論」（太籠統、沒記憶點）
- 原則：具體 > 抽象，口語 > 書面，有主角/動作 > 純概念
- goldenQuotes: 從字幕中挑 3 句最有記憶點的話
- Output ONLY valid JSON, no markdown fences or extra text"""

PROVIDERS = ["openai", "deepseek", "groq"]


def _to_traditional(obj):
    """Recursively convert all Chinese strings in a dict/list to Traditional Chinese (Taiwan)."""
    if isinstance(obj, str):
        return _s2tw.convert(obj)
    if isinstance(obj, list):
        return [_to_traditional(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_traditional(v) for k, v in obj.items()}
    return obj


def generate_title_and_appreciation(full_text: str, content_type: str = "video") -> dict:
    """Generate title + appreciation in one AI call. Returns {title, theme, keyPoints, goldenQuotes}."""
    system = LYRICS_SYSTEM_PROMPT if content_type == "lyrics" else SYSTEM_PROMPT
    label = "Lyrics" if content_type == "lyrics" else "Titler"
    print(f"[{label}] Analyzing text ({len(full_text)} chars)...")

    last_error = None
    for pv in PROVIDERS:
        try:
            response = chat.ask(full_text, pv=pv, system=system, temperature=0.3)
            result = _parse_json(response)
            if result and result.get("title"):
                result = _to_traditional(result)
                print(f"[Titler] Generated: {result['title']}")
                return result
        except Exception as e:
            last_error = e
            print(f"[Titler] {pv} failed: {e}, trying next...")
            continue

    print(f"[Titler] All providers failed: {last_error}")
    return {}


def _parse_json(text: str) -> dict | None:
    """Try to extract a JSON object from the response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return None


def generate_title_from_chinese(chinese_text: str, content_type: str = "video") -> dict:
    """Generate title + appreciation from translated Chinese text. Returns {title, theme, keyPoints, goldenQuotes}."""
    # Always use CHINESE_SYSTEM_PROMPT since input is already Chinese
    system = CHINESE_SYSTEM_PROMPT
    label = "Lyrics" if content_type == "lyrics" else "Titler"
    print(f"[{label}] Analyzing Chinese text ({len(chinese_text)} chars)...")

    last_error = None
    for pv in PROVIDERS:
        try:
            response = chat.ask(chinese_text, pv=pv, system=system, temperature=0.3)
            result = _parse_json(response)
            if result and result.get("title"):
                result = _to_traditional(result)
                print(f"[Titler] Generated from Chinese: {result['title']}")
                return result
        except Exception as e:
            last_error = e
            print(f"[Titler] {pv} failed: {e}, trying next...")
            continue

    print(f"[Titler] All providers failed for Chinese text: {last_error}")
    return {}
