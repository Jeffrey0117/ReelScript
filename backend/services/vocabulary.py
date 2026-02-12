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

SYSTEM_PROMPT = """You are an English vocabulary analyzer for intermediate Chinese-speaking learners.
Analyze the following English subtitle segments and extract USEFUL phrases and difficult vocabulary.

Rules:
- PRIORITIZE: phrasal verbs, idioms, collocations, multi-word expressions
  e.g. "break their trust", "done for good", "act like", "run deeper than"
- Also include: intermediate+ single words that are NOT basic
- SKIP all basic/common words: cared, treat, hurt, lose, find, make, keep, break, love, hate, feel, think, want, need, know, see, go, come, get, take, give, let, tell, say, ask, try, use, help, call, look, show, turn, play, run, move, hold, bring, set, put, leave, work, live, start, stop, open, close, read, write, etc.
- For each item provide the EXACT phrase as it appears and 繁體中文 translation
- Output ONLY a JSON array of arrays, one per segment
- Each inner array has objects with "word" and "translation" fields
- If a segment has nothing notable, use empty array
- Aim for 0-2 items per segment, quality over quantity

Example input: ["Once you break their trust, that's it", "They forgive not because they're weak"]
Example output: [[{"word":"break their trust","translation":"破壞他們的信任"}],[{"word":"forgive","translation":"原諒"}]]"""

BATCH_SIZE = 20
PROVIDERS = ["openai", "groq"]


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

    parsed = None

    try:
        result = json.loads(text)
        if isinstance(result, list):
            parsed = result
    except json.JSONDecodeError:
        pass

    if parsed is None:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            try:
                result = json.loads(text[start:end + 1])
                if isinstance(result, list):
                    parsed = result
            except json.JSONDecodeError:
                pass

    if parsed is None:
        print(f"[Vocabulary] Warning: failed to parse vocabulary from response")
        print(f"[Vocabulary] Response preview: {text[:200]}")
        return [[] for _ in range(expected_count)]

    if len(parsed) != expected_count:
        print(f"[Vocabulary] Warning: got {len(parsed)} results, expected {expected_count}. Adjusting...")
    while len(parsed) < expected_count:
        parsed.append([])
    return parsed[:expected_count]


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
