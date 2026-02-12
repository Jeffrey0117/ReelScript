"""
Translation service — translate transcript segments to Traditional Chinese via meei SDK.
Uses DeepSeek by default, falls back to Groq if unavailable.
"""

import sys
import json
from typing import List

# Add meei SDK to path
MEEI_PATH = "C:/Users/jeffb/Desktop/code/meei/python/src"
if MEEI_PATH not in sys.path:
    sys.path.insert(0, MEEI_PATH)

from meei.chat import chat  # noqa: E402

SYSTEM_PROMPT = """You are a professional English-to-Traditional-Chinese translator.
Translate the following English subtitle segments into natural, fluent 繁體中文.

Rules:
- Output ONLY a JSON array of translated strings, one per input segment
- Keep translations concise and natural for subtitle reading
- Use 繁體中文 (Traditional Chinese), NOT 簡體
- Do NOT add explanations, notes, or formatting — just the JSON array
- Preserve the exact number of segments

Example input: ["Hello everyone", "Today we talk about lighting"]
Example output: ["大家好", "今天我們來聊聊打光"]"""

# Max segments per batch to stay within token limits
BATCH_SIZE = 30

# Provider preference order
PROVIDERS = ["deepseek", "groq"]


def _call_llm(prompt: str) -> str:
    """Try each provider in order until one succeeds."""
    last_error = None
    for pv in PROVIDERS:
        try:
            return chat.ask(prompt, pv=pv, system=SYSTEM_PROMPT, temperature=0.3)
        except Exception as e:
            last_error = e
            print(f"[Translator] {pv} failed: {e}, trying next...")
            continue
    raise RuntimeError(f"All translation providers failed. Last error: {last_error}")


def _parse_translations(response: str, expected_count: int) -> List[str]:
    """Extract JSON array from LLM response, with fallback parsing."""
    text = response.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        result = json.loads(text)
        if isinstance(result, list) and len(result) == expected_count:
            return [str(t) for t in result]
    except json.JSONDecodeError:
        pass

    # Try to find JSON array in the response
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, list) and len(result) == expected_count:
                return [str(t) for t in result]
        except json.JSONDecodeError:
            pass

    # Return empty translations if parsing fails
    print(f"[Translator] Warning: failed to parse {expected_count} translations from response")
    return [""] * expected_count


def translate_segments(segments: list) -> list:
    """
    Translate transcript segments to Traditional Chinese.

    Args:
        segments: List of segment dicts with 'text' field

    Returns:
        Updated segments list with 'translation' field filled in
    """
    texts = [seg.get("text", "") for seg in segments]

    all_translations = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        prompt = json.dumps(batch, ensure_ascii=False)

        print(f"[Translator] Translating batch {i // BATCH_SIZE + 1} ({len(batch)} segments)...")
        response = _call_llm(prompt)
        translations = _parse_translations(response, len(batch))
        all_translations.extend(translations)

    # Return new list with translations merged (immutable pattern)
    return [
        {**seg, "translation": all_translations[i] if i < len(all_translations) else ""}
        for i, seg in enumerate(segments)
    ]
