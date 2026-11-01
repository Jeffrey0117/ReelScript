"""
Offline English→Traditional-Chinese dictionary.

Data: assets/dict.min.tsv.gz — 58k common words distilled from ECDICT
(github.com/skywind3000/ECDICT, MIT), translations pre-converted to
Traditional Chinese at build time. assets/lemma.tsv.gz maps inflected
forms to lemmas (running → run) so transcript clicks resolve.

Loaded lazily into memory (~15MB) on first lookup; thread-safe.
"""

import gzip
import threading
from pathlib import Path

ASSETS_DIR = Path(__file__).parent.parent / "assets"

_lock = threading.Lock()
_words: dict[str, tuple[str, str]] | None = None  # word -> (phonetic, translation)
_lemmas: dict[str, str] = {}

# Naive fallback suffix rules for forms the lemma table misses.
_SUFFIX_RULES = [
    ("ies", "y"), ("ied", "y"), ("ier", "y"), ("iest", "y"),
    ("ing", ""), ("ing", "e"), ("ed", ""), ("ed", "e"),
    ("es", ""), ("s", ""), ("er", ""), ("est", ""),
]


def _load() -> None:
    global _words
    with _lock:
        if _words is not None:
            return
        words: dict[str, tuple[str, str]] = {}
        with gzip.open(ASSETS_DIR / "dict.min.tsv.gz", "rt", encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 3:
                    words[parts[0]] = (parts[1], parts[2].replace("\\n", "\n"))
        with gzip.open(ASSETS_DIR / "lemma.tsv.gz", "rt", encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 2:
                    _lemmas[parts[0]] = parts[1]
        _words = words


def lookup(raw: str) -> dict | None:
    """Return {word, phonetic, translation} or None. Accepts inflected forms."""
    _load()
    assert _words is not None

    word = raw.strip().lower().strip(".,!?;:'\"()[]")
    if not word or len(word) > 50:
        return None

    candidates = [word]
    if word in _lemmas:
        candidates.append(_lemmas[word])
    for suffix, repl in _SUFFIX_RULES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 2:
            candidates.append(word[: -len(suffix)] + repl)

    for c in candidates:
        hit = _words.get(c)
        if hit:
            return {"word": c, "phonetic": hit[0], "translation": hit[1]}
    return None
