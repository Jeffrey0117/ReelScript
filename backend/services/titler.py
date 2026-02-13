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

PROVIDERS = ["openai", "deepseek", "groq"]


def generate_title_and_appreciation(full_text: str) -> dict:
    """Generate title + appreciation in one AI call. Returns {title, theme, keyPoints, goldenQuotes}."""
    print(f"[Titler] Analyzing text ({len(full_text)} chars)...")

    last_error = None
    for pv in PROVIDERS:
        try:
            response = chat.ask(full_text, pv=pv, system=SYSTEM_PROMPT, temperature=0.3)
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
