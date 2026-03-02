"""
Auto-title + appreciation service — one AI call for title, theme, key points, golden quotes.
"""

import sys
import json

MEEI_PATH = "C:/Users/jeffb/Desktop/code/meei/python/src"
if MEEI_PATH not in sys.path:
    sys.path.insert(0, MEEI_PATH)

from meei.chat import chat  # noqa: E402

SYSTEM_PROMPT = """You are a bilingual content analyst. Given an English video transcript,
produce a JSON object with a concise title AND content analysis:

{
  "title": "簡短繁體中文標題 (max 20 chars)",
  "theme": "一句話描述主題 (繁體中文)",
  "keyPoints": ["重點1", "重點2", "重點3"],
  "goldenQuotes": [
    {"en": "Original English quote", "zh": "繁體中文翻譯"},
    {"en": "...", "zh": "..."},
    {"en": "...", "zh": "..."}
  ]
}

Rules:
- title: max 20 characters, 繁體中文, specific not generic
- theme: 1 sentence in 繁體中文, summarizing the core message
- keyPoints: exactly 3 bullet points in 繁體中文
- goldenQuotes: exactly 3 memorable sentences from the original English, with 繁體中文 translation
- Output ONLY valid JSON, no markdown fences or extra text"""

LYRICS_SYSTEM_PROMPT = """You are a bilingual music/lyrics analyst. Given song lyrics (transcribed from audio),
produce a JSON object with a title AND lyrics analysis:

{
  "title": "歌名 — 歌手 (max 25 chars)",
  "theme": "一句話描述歌曲核心意境 (繁體中文)",
  "keyPoints": ["主題意境1", "修辭手法/情感表達2", "歌曲結構或風格特色3"],
  "goldenQuotes": [
    {"en": "Most impactful lyric line", "zh": "繁體中文翻譯"},
    {"en": "...", "zh": "..."},
    {"en": "...", "zh": "..."}
  ]
}

Rules:
- title: Try to identify song name and artist from lyrics/context. Format: "歌名 — 歌手"
- theme: Describe the emotional core and imagery of the song in 繁體中文
- keyPoints: 3 points covering: (1) core theme/emotion, (2) notable lyrical techniques (metaphor, repetition, imagery), (3) song mood/style
- goldenQuotes: 3 most memorable/beautiful lyric lines with 繁體中文 translation
- Pick lyrics that are poetic, emotionally powerful, or capture the song's essence
- Output ONLY valid JSON, no markdown fences or extra text"""

PROVIDERS = ["openai", "deepseek", "groq"]


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
