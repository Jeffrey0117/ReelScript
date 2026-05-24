"""
Translation service — translate transcript segments to Traditional Chinese via meei SDK.
Merges Whisper fragments into sentences before translating for better accuracy.
"""

import os
import re
import sys
import json
from typing import List

# MEEI_PATH is auto-injected by CloudPipe (deploy.js / ecosystem.config.js).
# For standalone runs, set MEEI_PATH=/path/to/meei/python/src manually.
MEEI_PATH = os.environ.get("MEEI_PATH")
if not MEEI_PATH:
    print("WARNING: MEEI_PATH not set, translation features disabled"); MEEI_PATH = None
if MEEI_PATH not in sys.path:
    sys.path.insert(0, MEEI_PATH)

from meei.chat import chat  # noqa: E402

SYSTEM_PROMPT = """You are a professional English-to-Traditional-Chinese translator.
Translate the following numbered English sentences into natural, fluent 繁體中文.

CRITICAL RULES:
- Each numbered input sentence MUST produce exactly one translation
- NEVER merge, combine, or skip sentences — maintain strict 1:1 mapping
- Output ONLY a JSON array of translated strings
- The array length MUST equal the number of input sentences
- Use 繁體中文 (Traditional Chinese, Taiwan), NOT 簡體中文
- Each translation should be natural and complete, ending with 。
- Do NOT include the [N] numbers in translations

Example input: ["[1] Hello everyone.", "[2] Today we talk about lighting."]
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


def _merge_into_sentences(segments: list, max_words: int = 0) -> list:
    """
    Merge Whisper segments into complete sentences.
    Returns list of {text, seg_indices} where seg_indices tracks which segments form each sentence.
    max_words: if >0, force split when buffer exceeds this word count (useful for lyrics).
    """
    sentences = []
    buf = ""
    indices = []

    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        buf += (" " if buf else "") + text
        indices.append(i)

        has_punctuation = bool(re.search(r'[.!?]$', text))
        over_limit = max_words > 0 and len(buf.split()) >= max_words

        if has_punctuation or over_limit:
            sentences.append({"text": buf.strip(), "seg_indices": list(indices)})
            buf = ""
            indices = []

    # Flush remaining
    if buf.strip():
        sentences.append({"text": buf.strip(), "seg_indices": list(indices)})

    return sentences


def _translate_batch(batch_index: int, batch: list) -> list:
    """Translate a single batch of sentences. Returns list of translated strings."""
    # Add [N] prefixes to prevent LLM from merging adjacent sentences
    numbered = [f"[{i + 1}] {s}" for i, s in enumerate(batch)]
    prompt = json.dumps(numbered, ensure_ascii=False)
    print(f"[Translator] Translating batch {batch_index + 1} ({len(batch)} sentences)...")
    response = _call_llm(prompt)
    translations = _parse_translations(response, len(batch))
    # Strip [N] prefixes if LLM included them in output
    return [re.sub(r'^\[\d+\]\s*', '', t) for t in translations]


def translate_segments(segments: list, content_type: str = "video") -> list:
    """
    Translate transcript segments to Traditional Chinese.
    Merges into sentences first for accurate alignment, then maps back.
    Uses concurrent batch processing (up to 3 parallel API calls).

    Args:
        segments: List of segment dicts with 'text' field
        content_type: "video" or "lyrics" — lyrics use shorter merge windows

    Returns:
        Updated segments list with 'translation' field filled in
    """
    import concurrent.futures

    # Step 1: Merge segments into sentences
    # Lyrics often lack punctuation, so force split at ~15 words
    max_words = 15 if content_type == "lyrics" else 0
    sentences = _merge_into_sentences(segments, max_words=max_words)
    sentence_texts = [s["text"] for s in sentences]

    print(f"[Translator] Merged {len(segments)} segments into {len(sentences)} sentences")

    # Step 2: Translate sentences in parallel batches (max 3 concurrent)
    batches = []
    for i in range(0, len(sentence_texts), BATCH_SIZE):
        batches.append(sentence_texts[i:i + BATCH_SIZE])

    all_translations = [None] * len(batches)

    if len(batches) <= 1:
        # Single batch — no need for threading
        if batches:
            all_translations[0] = _translate_batch(0, batches[0])
    else:
        max_workers = min(3, len(batches))
        print(f"[Translator] Processing {len(batches)} batches with {max_workers} parallel workers")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(_translate_batch, idx, batch): idx
                for idx, batch in enumerate(batches)
            }
            for future in concurrent.futures.as_completed(futures):
                idx = futures[future]
                try:
                    all_translations[idx] = future.result()
                except Exception as e:
                    print(f"[Translator] Batch {idx} failed: {e}")
                    all_translations[idx] = [""] * len(batches[idx])

    # Flatten ordered results
    flat_translations = []
    for batch_result in all_translations:
        if batch_result:
            flat_translations.extend(batch_result)

    # Step 2.5: Retry empty translations individually
    empty_indices = [i for i, t in enumerate(flat_translations) if not t.strip()]
    if empty_indices and len(empty_indices) <= 5:
        print(f"[Translator] Retrying {len(empty_indices)} empty translations individually...")
        for idx in empty_indices:
            try:
                retry_result = _translate_batch(-1, [sentence_texts[idx]])
                if retry_result and retry_result[0].strip():
                    flat_translations[idx] = retry_result[0]
                    print(f"[Translator] Retry success for sentence {idx + 1}")
            except Exception as e:
                print(f"[Translator] Retry failed for sentence {idx + 1}: {e}")
    elif empty_indices:
        print(f"[Translator] {len(empty_indices)} empty translations (too many to retry individually)")

    # Step 3: Map sentence translations back to segments
    # Store full sentence translation on the FIRST segment of each sentence
    seg_translations = [""] * len(segments)
    for si, sent in enumerate(sentences):
        translation = flat_translations[si] if si < len(flat_translations) else ""
        first_seg_idx = sent["seg_indices"][0]
        seg_translations[first_seg_idx] = translation

    # Return new list with translations merged (immutable pattern)
    return [
        {**seg, "translation": seg_translations[i]}
        for i, seg in enumerate(segments)
    ]
