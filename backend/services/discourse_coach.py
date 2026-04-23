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

SYSTEM_PROMPT = """You are an English expression coach specializing in SHORT-FORM VIDEO content (Reels, TikTok, YouTube Shorts).
The user recorded themselves speaking English for a short video. Below is the full transcript.

CRITICAL STYLE RULES for the rewritten version:
- This is SHORT VIDEO content. Keep it SPOKEN, PUNCHY, and CONVERSATIONAL.
- DO NOT make it sound like an essay, a blog post, or a formal speech.
- Use short sentences. Use sentence fragments. Use rhetorical questions.
- Preserve the speaker's ENERGY and VIBE — if they're passionate, keep it passionate. If they're casual, keep it casual.
- Think: "How would a popular creator say this on camera?" NOT "How would a professor write this."
- The rewrite should feel like something people would actually WATCH and SHARE, not read in a textbook.
- Keep roughly the same length. Don't pad it. Don't over-explain.

Your job:
1. What they were trying to say (topic)
2. How their current structure works (or doesn't) — for spoken video, not written prose
3. A rewritten version in the SAME SPOKEN STYLE but clearer and more engaging
4. Practical tips for short-form video delivery

Output ONLY valid JSON:

{
  "topic": "the main point the speaker is trying to express (1 sentence, in Traditional Chinese)",
  "structure_analysis": {
    "current": "describe the current expression structure (Traditional Chinese)",
    "problems": ["structural issue 1 (Traditional Chinese)", "structural issue 2"],
    "suggestion": "suggested expression structure for short video (Traditional Chinese)"
  },
  "rewritten": "Full rewritten version — same energy, same vibe, but clearer and more engaging. Spoken style, not written style. Short sentences. Punchy delivery.",
  "rewritten_segments": [
    {"index": 1, "text": "First sentence of the rewritten version"},
    {"index": 2, "text": "Second sentence of the rewritten version"}
  ],
  "tips": [
    {
      "category": "hook|structure|transition|closing|vocabulary|delivery",
      "tip": "specific advice for short video (Traditional Chinese)",
      "example": "English example demonstrating the tip"
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
- structure_analysis: all in Traditional Chinese, focused on VIDEO structure (hook → body → close), NOT essay structure
- rewritten: SPOKEN English. Short sentences. Fragments OK. Rhetorical questions OK. Keep the original energy.
- rewritten_segments: break into individual spoken sentences/phrases for read-along practice
- tips: 3-5 tips, category must be one of: hook, structure, transition, closing, vocabulary, delivery
- tips.tip in Traditional Chinese, tips.example in English
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
