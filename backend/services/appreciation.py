"""
Content appreciation service — generate theme, key takeaways, and golden quotes.
"""

import sys
import json

MEEI_PATH = "C:/Users/jeffb/Desktop/code/meei/python/src"
if MEEI_PATH not in sys.path:
    sys.path.insert(0, MEEI_PATH)

from meei.chat import chat  # noqa: E402

SYSTEM_PROMPT = """You are a bilingual content analyst. Given an English text (from a video transcript),
produce a concise study summary in the following JSON format:

{
  "theme": "一句話描述主題 (繁體中文)",
  "keyPoints": ["重點1", "重點2", "重點3"],
  "goldenQuotes": [
    {"en": "Original English quote", "zh": "繁體中文翻譯"},
    {"en": "...", "zh": "..."},
    {"en": "...", "zh": "..."}
  ]
}

Rules:
- theme: 1 sentence in 繁體中文, summarizing the core message
- keyPoints: exactly 3 bullet points in 繁體中文, capturing the main ideas
- goldenQuotes: exactly 3 memorable/impactful sentences from the original English text, with 繁體中文 translation
- Pick quotes that are powerful, quotable, or capture the essence of the message
- Output ONLY valid JSON, no markdown fences or extra text"""

PROVIDERS = ["openai", "groq"]


def _call_llm(prompt: str) -> str:
    last_error = None
    for pv in PROVIDERS:
        try:
            return chat.ask(prompt, pv=pv, system=SYSTEM_PROMPT, temperature=0.3)
        except Exception as e:
            last_error = e
            print(f"[Appreciation] {pv} failed: {e}, trying next...")
            continue
    raise RuntimeError(f"All providers failed. Last error: {last_error}")


def generate_appreciation(full_text: str) -> dict:
    """Generate appreciation/analysis for the given English text."""
    print(f"[Appreciation] Analyzing text ({len(full_text)} chars)...")
    response = _call_llm(full_text)

    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        result = json.loads(text)
        if isinstance(result, dict) and "theme" in result:
            return result
    except json.JSONDecodeError:
        pass

    # Try to find JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, dict) and "theme" in result:
                return result
        except json.JSONDecodeError:
            pass

    print(f"[Appreciation] Warning: failed to parse response: {text[:200]}")
    return {
        "theme": "",
        "keyPoints": [],
        "goldenQuotes": [],
    }
