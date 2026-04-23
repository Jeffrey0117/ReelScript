"""
Discourse Coach service — analyze speaking structure, expression, and provide rewritten script.
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

SYSTEM_PROMPT = """You are an English expression coach for short-form video creators (Reels, TikTok, Shorts).
The user recorded themselves speaking English. Below is the full transcript.

REVISION RULES — THIS IS NOT A REWRITE, IT'S A POLISH:
- Stay VERY CLOSE to the original. Same words, same structure, same vibe.
- Only fix what's broken: grammar mistakes, awkward phrasing, unclear logic.
- STRENGTHEN the core message — make the main point hit harder.
- DO NOT add new ideas. DO NOT restructure into a different format.
- DO NOT make it formal or literary. Keep the spoken, casual tone.
- If the original is intense/passionate, keep that energy. Don't soften it.
- Same length. Don't pad. Don't over-explain.

Your job:
1. Identify the core message (topic)
2. Analyze structure issues (for spoken video, not essay)
3. Provide a POLISHED version — close to original, just stronger and cleaner
4. Each polished sentence must include Traditional Chinese translation
5. Practical tips for delivery

Output ONLY valid JSON:

{
  "topic": "the core message (1 sentence, Traditional Chinese)",
  "structure_analysis": {
    "current": "current structure description (Traditional Chinese)",
    "problems": ["issue 1 (Traditional Chinese)", "issue 2"],
    "suggestion": "suggested improvement (Traditional Chinese)"
  },
  "rewritten": "Full polished version in English — close to original, grammar fixed, core message strengthened.",
  "rewritten_segments": [
    {"index": 1, "en": "Polished English sentence 1", "zh": "繁體中文翻譯 1", "note": "將 XXX 改為 YYY，因為...（具體說明改動）"},
    {"index": 2, "en": "Polished English sentence 2", "zh": "繁體中文翻譯 2", "note": "調整語序，讓主旨更突出"}
  ],
  "tips": [
    {
      "category": "hook|structure|transition|closing|vocabulary|delivery",
      "tip": "specific advice (Traditional Chinese)",
      "example": "English example"
    }
  ],
  "scores": {
    "clarity": 6,
    "organization": 5,
    "persuasiveness": 4,
    "engagement": 5
  }
}

Rules:
- topic: 1 sentence in Traditional Chinese
- structure_analysis: all in Traditional Chinese
- rewritten: polished English, CLOSE to original, not a rewrite from scratch
- rewritten_segments: each has "en" (polished English), "zh" (Traditional Chinese translation), and "note" (Traditional Chinese, MUST describe the specific change: what was changed, what it was changed to, and why. Example: "將 'very important' 改為 'crucial'，語氣更強". NEVER write "無修改" — if the sentence is kept as-is, explain what makes it effective, e.g. "這句開場直接有力，保留原句")
- tips: 3-5 tips, category: hook/structure/transition/closing/vocabulary/delivery
- scores: 1-10 each (clarity, organization, persuasiveness, engagement)
- Output ONLY valid JSON, no markdown fences or extra text"""

PROVIDERS = ["openai", "groq"]


def _call_llm(prompt: str) -> str:
    last_error = None
    for pv in PROVIDERS:
        try:
            return chat.ask(prompt, pv=pv, system=SYSTEM_PROMPT, temperature=0.3)
        except Exception as e:
            last_error = e
            logger.warning("[DiscourseCoach] %s failed: %s, trying next...", pv, e)
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
        if isinstance(result, dict) and "topic" in result:
            return result
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, dict) and "topic" in result:
                return result
        except json.JSONDecodeError:
            pass

    return None


def analyze_discourse(full_text: str) -> dict:
    """Analyze the overall discourse structure and expression of the spoken text.

    Args:
        full_text: The complete transcript text (all segments joined).

    Returns:
        Discourse analysis result dict.
    """
    logger.info("[DiscourseCoach] Analyzing discourse (%d chars)...", len(full_text))
    response = _call_llm(full_text)
    result = _parse_json(response)

    if result:
        return result

    logger.warning("[DiscourseCoach] Failed to parse response: %s", response[:200])
    return {
        "topic": "",
        "structure_analysis": {
            "current": "",
            "problems": [],
            "suggestion": "",
        },
        "rewritten": "",
        "rewritten_segments": [],
        "tips": [],
        "scores": {
            "clarity": 0,
            "organization": 0,
            "persuasiveness": 0,
            "engagement": 0,
        },
    }
