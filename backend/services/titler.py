"""
Auto-title service — generate a concise video title from transcript text.
"""

import sys

MEEI_PATH = "C:/Users/jeffb/Desktop/code/meei/python/src"
if MEEI_PATH not in sys.path:
    sys.path.insert(0, MEEI_PATH)

from meei.chat import chat  # noqa: E402

SYSTEM_PROMPT = """You are a bilingual title generator. Given an English transcript from a short video,
generate a concise, descriptive title in 繁體中文 (Traditional Chinese).

Rules:
- Maximum 20 characters
- Capture the core topic/message
- Be specific, not generic
- Output ONLY the title text, nothing else
- No quotes, no punctuation wrapping"""

PROVIDERS = ["openai", "deepseek", "groq"]


def generate_title(full_text: str) -> str:
    """Generate a short Chinese title from transcript text."""
    # Use first 500 chars to keep it fast and cheap
    snippet = full_text[:500]
    print(f"[Titler] Generating title from {len(snippet)} chars...")

    last_error = None
    for pv in PROVIDERS:
        try:
            result = chat.ask(snippet, pv=pv, system=SYSTEM_PROMPT, temperature=0.3)
            title = result.strip().strip('"').strip("'").strip()
            if title:
                print(f"[Titler] Generated: {title}")
                return title
        except Exception as e:
            last_error = e
            print(f"[Titler] {pv} failed: {e}, trying next...")
            continue

    print(f"[Titler] All providers failed: {last_error}")
    return ""
