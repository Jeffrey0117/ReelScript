"""
Translation service — translate transcript segments to Traditional Chinese via meei SDK.
Merges Whisper fragments into sentences before translating for better accuracy.
"""

import re
import sys
import json
from typing import List

# Add meei SDK to path
MEEI_PATH = "C:/Users/jeffb/Desktop/code/meei/python/src"
if MEEI_PATH not in sys.path:
    sys.path.insert(0, MEEI_PATH)

from meei.chat import chat  # noqa: E402

SYSTEM_PROMPT = """You are a professional English-to-Traditional-Chinese translator.
Translate the following English sentences into natural, fluent 繁體中文.

Rules:
- Output ONLY a JSON array of translated strings, one per input sentence
- Keep translations concise and natural
- Use 繁體中文 (Traditional Chinese), NOT 簡體
- Do NOT add explanations, notes, or formatting — just the JSON array
- Preserve the exact number of items
- Each translation should be a complete sentence ending with 。

Example input: ["Hello everyone.", "Today we talk about lighting."]
Example output: ["大家好。", "今天我們來聊聊打光。"]"""

# Max sentences per batch
BATCH_SIZE = 20

# Provider preference order
PROVIDERS = ["openai", "groq"]


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

    parsed = None

    try:
        result = json.loads(text)
        if isinstance(result, list):
            parsed = [str(t) for t in result]
    except json.JSONDecodeError:
        pass

    # Try to find JSON array in the response
    if parsed is None:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            try:
                result = json.loads(text[start:end + 1])
                if isinstance(result, list):
                    parsed = [str(t) for t in result]
            except json.JSONDecodeError:
                pass

    if parsed is None:
        print(f"[Translator] Warning: failed to parse translations from response")
        print(f"[Translator] Response preview: {text[:200]}")
        return [""] * expected_count

    # Pad or truncate to match expected count
    if len(parsed) != expected_count:
        print(f"[Translator] Warning: got {len(parsed)} translations, expected {expected_count}. Adjusting...")
    while len(parsed) < expected_count:
        parsed.append("")
    return parsed[:expected_count]


def _merge_into_sentences(segments: list) -> list:
    """
    Merge Whisper segments into complete sentences.
    Returns list of {text, seg_indices} where seg_indices tracks which segments form each sentence.
    """
    sentences = []
    buf = ""
    indices = []

    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        buf += (" " if buf else "") + text
        indices.append(i)

        # Split on sentence-ending punctuation
        if re.search(r'[.!?]$', text):
            sentences.append({"text": buf.strip(), "seg_indices": list(indices)})
            buf = ""
            indices = []

    # Flush remaining
    if buf.strip():
        sentences.append({"text": buf.strip(), "seg_indices": list(indices)})

    return sentences


def translate_segments(segments: list) -> list:
    """
    Translate transcript segments to Traditional Chinese.
    Merges into sentences first for accurate alignment, then maps back.

    Args:
        segments: List of segment dicts with 'text' field

    Returns:
        Updated segments list with 'translation' field filled in
    """
    # Step 1: Merge segments into sentences
    sentences = _merge_into_sentences(segments)
    sentence_texts = [s["text"] for s in sentences]

    print(f"[Translator] Merged {len(segments)} segments into {len(sentences)} sentences")

    # Step 2: Translate sentences in batches
    all_translations = []
    for i in range(0, len(sentence_texts), BATCH_SIZE):
        batch = sentence_texts[i:i + BATCH_SIZE]
        prompt = json.dumps(batch, ensure_ascii=False)

        print(f"[Translator] Translating batch {i // BATCH_SIZE + 1} ({len(batch)} sentences)...")
        response = _call_llm(prompt)
        translations = _parse_translations(response, len(batch))
        all_translations.extend(translations)

    # Step 3: Map sentence translations back to segments
    # Store full sentence translation on the LAST segment of each sentence
    seg_translations = [""] * len(segments)
    for si, sent in enumerate(sentences):
        translation = all_translations[si] if si < len(all_translations) else ""
        last_seg_idx = sent["seg_indices"][-1]
        seg_translations[last_seg_idx] = translation

    # Return new list with translations merged (immutable pattern)
    return [
        {**seg, "translation": seg_translations[i]}
        for i, seg in enumerate(segments)
    ]
