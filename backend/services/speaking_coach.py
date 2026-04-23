"""
Speaking Coach service — analyze English speaking for grammar, word choice, and naturalness.
"""

import os
import sys
import json
import logging

logger = logging.getLogger(__name__)

MEEI_PATH = os.environ.get("MEEI_PATH")
if not MEEI_PATH:
    raise RuntimeError("MEEI_PATH environment variable not set")
if MEEI_PATH not in sys.path:
    sys.path.insert(0, MEEI_PATH)

from meei.chat import chat  # noqa: E402

SYSTEM_PROMPT = """You are an expert English speaking coach for Mandarin Chinese speakers.
Given an array of transcribed English sentences (from a user's speaking recording),
analyze each sentence and provide coaching feedback.

Output ONLY valid JSON in this exact format:

{
  "sentences": [
    {
      "index": 1,
      "original": "the original transcribed sentence",
      "corrected": "the grammatically correct and natural version",
      "issues": [
        {
          "type": "grammar|word_choice|naturalness|pronunciation_hint",
          "highlight": "the problematic word or phrase",
          "explanation": "簡短中文解釋 (繁體中文)"
        }
      ],
      "native_alt": "how a native speaker might say it more naturally",
      "score": 7
    }
  ],
  "overall": {
    "fluency": 7,
    "grammar": 6,
    "vocabulary": 5,
    "naturalness": 5,
    "summary": "整體評語 (繁體中文，2-3 句)",
    "strengths": ["優點1 (繁體中文)", "優點2"],
    "improvements": ["建議1 (繁體中文)", "建議2"]
  }
}

Rules:
- issue type must be one of: grammar, word_choice, naturalness, pronunciation_hint
- explanation must be in 繁體中文
- score: 1-10 per sentence (10 = perfect native-like)
- overall scores: 1-10 each
- summary, strengths, improvements: all in 繁體中文
- If a sentence is already perfect, set issues to [], corrected = original, score = 10
- native_alt should show a more natural/idiomatic way to express the same idea
- Output ONLY valid JSON, no markdown fences or extra text"""

PROVIDERS = ["openai", "groq"]

MAX_SENTENCES_PER_BATCH = 20


def _call_llm(prompt: str) -> str:
    last_error = None
    for pv in PROVIDERS:
        try:
            return chat.ask(prompt, pv=pv, system=SYSTEM_PROMPT, temperature=0.3)
        except Exception as e:
            last_error = e
            logger.warning("[SpeakingCoach] %s failed: %s, trying next...", pv, e)
            continue
    raise RuntimeError(f"All providers failed. Last error: {last_error}")


def _parse_json(text: str) -> dict | None:
    """Try to extract JSON from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        result = json.loads(text)
        if isinstance(result, dict) and "sentences" in result:
            return result
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, dict) and "sentences" in result:
                return result
        except json.JSONDecodeError:
            pass

    return None


def analyze_speaking(segments: list[dict]) -> dict:
    """Analyze transcribed segments and return coaching feedback.

    Args:
        segments: List of {index, start, end, text} dicts from Whisper.

    Returns:
        Coaching result dict with sentences and overall scores.
    """
    sentences = [
        {"index": seg["index"], "text": seg["text"]}
        for seg in segments
        if seg.get("text", "").strip()
    ]

    if not sentences:
        return _empty_result()

    all_coached: list[dict] = []
    overall = None

    for batch_start in range(0, len(sentences), MAX_SENTENCES_PER_BATCH):
        batch = sentences[batch_start:batch_start + MAX_SENTENCES_PER_BATCH]
        is_last_batch = (batch_start + MAX_SENTENCES_PER_BATCH) >= len(sentences)

        prompt = "Analyze these English sentences from a speaking recording:\n\n"
        for s in batch:
            prompt += f"{s['index']}. {s['text']}\n"

        if not is_last_batch:
            prompt += "\nNote: This is a partial batch. Provide sentence-level analysis only, skip the 'overall' section."

        logger.info("[SpeakingCoach] Analyzing batch (%d sentences)...", len(batch))
        response = _call_llm(prompt)
        result = _parse_json(response)

        if not result:
            logger.warning("[SpeakingCoach] Failed to parse batch response: %s", response[:200])
            for s in batch:
                all_coached.append({
                    "index": s["index"],
                    "original": s["text"],
                    "corrected": s["text"],
                    "issues": [],
                    "native_alt": s["text"],
                    "score": 5,
                })
            continue

        all_coached.extend(result.get("sentences", []))
        if is_last_batch and "overall" in result:
            overall = result["overall"]

    if not overall:
        overall = {
            "fluency": 5,
            "grammar": 5,
            "vocabulary": 5,
            "naturalness": 5,
            "summary": "",
            "strengths": [],
            "improvements": [],
        }

    return {
        "sentences": all_coached,
        "overall": overall,
    }


def _empty_result() -> dict:
    return {
        "sentences": [],
        "overall": {
            "fluency": 0,
            "grammar": 0,
            "vocabulary": 0,
            "naturalness": 0,
            "summary": "",
            "strengths": [],
            "improvements": [],
        },
    }
