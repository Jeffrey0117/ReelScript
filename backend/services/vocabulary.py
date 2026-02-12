"""
Vocabulary analysis service — extract difficult English words with Chinese translations.
Uses meei SDK (Groq by default) for AI analysis.
"""

import sys
import json
from typing import List

MEEI_PATH = "C:/Users/jeffb/Desktop/code/meei/python/src"
if MEEI_PATH not in sys.path:
    sys.path.insert(0, MEEI_PATH)

from meei.chat import chat  # noqa: E402

SYSTEM_PROMPT = """You are an English vocabulary analyzer for language learners.
Analyze the following English subtitle segments and identify difficult/useful vocabulary words.

Rules:
- For each segment, pick 1-3 words or phrases that are intermediate+ level
- Focus on: useful verbs, nouns, adjectives, phrasal verbs, idioms
- SKIP basic words like: is, am, are, the, a, an, I, you, he, she, it, this, that, and, or, but, in, on, at, to, for, of, with
- For each word, provide the original form and 繁體中文 translation
- Output ONLY a JSON array of arrays, one inner array per segment
- Each inner array contains objects with "word" and "translation" fields
- If a segment has no difficult words, use an empty array

Example input: ["The algorithm demonstrates efficiency", "Hello everyone"]
Example output: [[{"word":"algorithm","translation":"演算法"},{"word":"demonstrate","translation":"展示"},{"word":"efficiency","translation":"效率"}],[]]"""

BATCH_SIZE = 20
PROVIDERS = ["groq", "deepseek"]


def _call_llm(prompt: str) -> str:
    last_error = None
    for pv in PROVIDERS:
        try:
            return chat.ask(prompt, pv=pv, system=SYSTEM_PROMPT, temperature=0.2)
        except Exception as e:
            last_error = e
            print(f"[Vocabulary] {pv} failed: {e}, trying next...")
            continue
    raise RuntimeError(f"All providers failed. Last error: {last_error}")


def _parse_vocabulary(response: str, expected_count: int) -> list:
    text = response.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        result = json.loads(text)
        if isinstance(result, list) and len(result) == expected_count:
            return result
    except json.JSONDecodeError:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, list) and len(result) == expected_count:
                return result
        except json.JSONDecodeError:
            pass

    print(f"[Vocabulary] Warning: failed to parse vocabulary for {expected_count} segments")
    return [[] for _ in range(expected_count)]


def analyze_segments(segments: list) -> list:
    """
    Analyze transcript segments for vocabulary.

    Args:
        segments: List of segment dicts with 'text' field

    Returns:
        Updated segments with 'vocabulary' field: [{word, translation}, ...]
    """
    texts = [seg.get("text", "") for seg in segments]

    all_vocab = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        prompt = json.dumps(batch, ensure_ascii=False)

        print(f"[Vocabulary] Analyzing batch {i // BATCH_SIZE + 1} ({len(batch)} segments)...")
        response = _call_llm(prompt)
        vocab_batch = _parse_vocabulary(response, len(batch))
        all_vocab.extend(vocab_batch)

    return [
        {**seg, "vocabulary": all_vocab[i] if i < len(all_vocab) else []}
        for i, seg in enumerate(segments)
    ]
