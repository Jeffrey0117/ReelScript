"""
Public API routes — open endpoints for external consumption.
No auth required. Serves learning snippets, cards, articles, vocabulary, search.
"""

import json
import random
import re
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models import get_db, Video, Transcript
from services.downloader import VIDEOS_DIR, extract_audio

# meei SDK for semantic search — auto-injected by CloudPipe.
# For standalone runs, set MEEI_PATH=/path/to/meei/python/src manually.
import os
MEEI_PATH = os.environ.get("MEEI_PATH")
if not MEEI_PATH:
    print("WARNING: MEEI_PATH not set, translation features disabled"); MEEI_PATH = None
if MEEI_PATH not in sys.path:
    sys.path.insert(0, MEEI_PATH)

router = APIRouter(prefix="/api/public", tags=["public"])


def _format_timestamp(seconds: float) -> str:
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"


def _get_ready_videos(db: Session):
    return (
        db.query(Video)
        .filter(Video.status == "ready", Video.is_public == True, Video.is_featured == True)
        .all()
    )


def _get_all_ready_videos(db: Session):
    return db.query(Video).filter(Video.status == "ready", Video.is_public == True).all()


def _video_has_segments(video: Video) -> bool:
    return (
        video.transcript is not None
        and video.transcript.segments is not None
        and len(video.transcript.segments) > 0
    )


def _merge_segments(segments: list[dict]) -> list[dict]:
    """Merge fragmented Whisper segments into complete sentences.

    Whisper often splits at commas/pauses, producing tiny fragments like
    "okay,", "ah,", "No,".  Translation is applied per merged sentence,
    so only the final fragment of a group has zh text.

    Strategy: walk segments, accumulate EN text until we hit one that has
    a non-empty translation — that becomes one merged sentence.
    """
    merged: list[dict] = []
    buf_en: list[str] = []
    buf_vocab: list[dict] = []
    buf_start: float = 0
    buf_end: float = 0

    for seg in segments:
        text = seg.get("text", "").strip()
        zh = seg.get("translation", "").strip()
        if not text:
            continue

        if not buf_en:
            buf_start = seg.get("start", 0)
        buf_en.append(text)
        buf_end = seg.get("end", buf_start)
        buf_vocab.extend(seg.get("vocabulary", []))

        if zh:
            merged.append({
                "en": " ".join(buf_en),
                "zh": zh,
                "start": buf_start,
                "end": buf_end,
                "vocabulary": buf_vocab,
            })
            buf_en = []
            buf_vocab = []

    # Leftover fragments without translation — skip them
    return merged


MIN_SNIPPET_EN_LEN = 20  # minimum English characters for a usable snippet


def _get_quality_snippets(db: Session) -> list[tuple[dict, "Video"]]:
    """Return merged, quality-filtered (en, zh, len) snippet pool."""
    videos = _get_all_ready_videos(db)
    pool: list[tuple[dict, Video]] = []
    for v in videos:
        if not _video_has_segments(v):
            continue
        for m in _merge_segments(v.transcript.segments):
            if len(m["en"]) >= MIN_SNIPPET_EN_LEN and m["zh"]:
                pool.append((m, v))
    return pool


def _merged_to_card(m: dict, video: Video, total: int) -> dict:
    card = {
        "en": m["en"],
        "zh": m["zh"],
        "timestamp": _format_timestamp(m["start"]),
        "videoTitle": video.title,
        "videoId": video.id,
        "source": video.source,
        "channel": video.channel,
    }
    if m.get("vocabulary"):
        card["vocabulary"] = m["vocabulary"]
    return card


def _segment_to_card(seg: dict, video: Video, total: int) -> dict:
    card = {
        "index": seg.get("index", 0),
        "total": total,
        "en": seg.get("text", ""),
        "zh": seg.get("translation", ""),
        "timestamp": _format_timestamp(seg.get("start", 0)),
        "videoTitle": video.title,
        "videoId": video.id,
        "source": video.source,
        "channel": video.channel,
    }
    vocab = seg.get("vocabulary")
    if vocab:
        card["vocabulary"] = vocab
    return card


# ── Snippet: random single sentence ─────────────────────

@router.get("/snippet/random")
async def random_snippet(db: Session = Depends(get_db)):
    """Get a random learning snippet (one complete sentence + translation)."""
    pool = _get_quality_snippets(db)
    if not pool:
        raise HTTPException(status_code=404, detail="No content available")

    m, video = random.choice(pool)
    return _merged_to_card(m, video, len(pool))


@router.get("/snippet/daily")
async def daily_snippet(db: Session = Depends(get_db)):
    """Get today's daily snippet (deterministic per day)."""
    pool = _get_quality_snippets(db)
    if not pool:
        raise HTTPException(status_code=404, detail="No content available")

    day_seed = datetime.utcnow().timetuple().tm_yday
    idx = day_seed % len(pool)
    m, video = pool[idx]
    return _merged_to_card(m, video, len(pool))


# ── Cards: full video in order ───────────────────────────

@router.get("/videos/{video_id}/cards")
async def video_cards(video_id: str, db: Session = Depends(get_db)):
    """Get all segments of a video as ordered cards."""
    video = db.query(Video).filter(Video.id == video_id, Video.status == "ready", Video.is_public == True).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not _video_has_segments(video):
        raise HTTPException(status_code=404, detail="No transcript available")

    merged = _merge_segments(video.transcript.segments)
    return {
        "videoId": video.id,
        "videoTitle": video.title,
        "source": video.source,
        "channel": video.channel,
        "duration": video.duration,
        "totalCards": len(merged),
        "cards": [_merged_to_card(m, video, len(merged)) for m in merged],
    }


# ── Audio: extract and serve MP3 ──────────────────────────

@router.get("/videos/{video_id}/audio")
async def video_audio(video_id: str, db: Session = Depends(get_db)):
    """Get audio URL + timeline for a video (extracts MP3 on first request)."""
    video = db.query(Video).filter(Video.id == video_id, Video.status == "ready", Video.is_public == True).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.filename:
        raise HTTPException(status_code=404, detail="No video file available")

    # Extract MP3 (cached after first extraction)
    video_path = VIDEOS_DIR / video.filename
    audio_filename = extract_audio(video_path, video_id)
    if not audio_filename:
        raise HTTPException(status_code=500, detail="Audio extraction failed")

    # Build timeline from merged segments (complete sentences only)
    segments = []
    if _video_has_segments(video):
        for i, m in enumerate(_merge_segments(video.transcript.segments)):
            segments.append({
                "index": i,
                "start": m["start"],
                "end": m["end"],
                "en": m["en"],
                "zh": m["zh"],
            })

    return {
        "videoId": video.id,
        "title": video.title,
        "channel": video.channel,
        "duration": video.duration,
        "audioUrl": f"/audio/{audio_filename}",
        "videoUrl": f"/videos/{video.filename}",
        "thumbnail": f"/thumbnails/{video.thumbnail}" if video.thumbnail else None,
        "segments": segments,
    }


# ── Article: blog-ready structured content ───────────────

@router.get("/videos/{video_id}/article")
async def video_article(video_id: str, db: Session = Depends(get_db)):
    """Get blog-ready article data for a video."""
    video = db.query(Video).filter(Video.id == video_id, Video.status == "ready", Video.is_public == True).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.transcript:
        raise HTTPException(status_code=404, detail="No transcript available")

    t = video.transcript
    appreciation = t.appreciation or {}
    raw_segments = t.segments or []
    merged = _merge_segments(raw_segments)

    # Collect vocabulary from merged segments
    all_vocab = []
    seen_words = set()
    for m in merged:
        for v in m.get("vocabulary", []):
            word = v.get("word", "").lower()
            if word and word not in seen_words:
                seen_words.add(word)
                all_vocab.append(v)

    return {
        "videoId": video.id,
        "title": video.title,
        "source": video.source,
        "channel": video.channel,
        "duration": video.duration,
        "theme": appreciation.get("theme", ""),
        "keyPoints": appreciation.get("keyPoints", []),
        "goldenQuotes": appreciation.get("goldenQuotes", []),
        "segments": [
            {
                "index": i,
                "timestamp": _format_timestamp(m["start"]),
                "en": m["en"],
                "zh": m["zh"],
            }
            for i, m in enumerate(merged)
        ],
        "vocabulary": all_vocab,
        "fullText": t.full_text,
    }


# ── Vocabulary: searchable word list ─────────────────────

@router.get("/vocabulary")
async def vocabulary_list(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get aggregated vocabulary across all videos."""
    videos = _get_all_ready_videos(db)
    all_vocab = []
    seen_words = set()

    for video in videos:
        if not _video_has_segments(video):
            continue
        for seg in video.transcript.segments:
            for v in seg.get("vocabulary", []):
                word = v.get("word", "").lower()
                if word and word not in seen_words:
                    seen_words.add(word)
                    all_vocab.append({
                        **v,
                        "videoId": video.id,
                        "videoTitle": video.title,
                    })

    total = len(all_vocab)
    page = all_vocab[offset:offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "words": page,
    }


# ── Quotes: golden quotes collection ────────────────────

@router.get("/quotes")
async def quotes_list(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    """Get golden quotes from video appreciations."""
    videos = _get_all_ready_videos(db)
    all_quotes = []

    for video in videos:
        if not video.transcript or not video.transcript.appreciation:
            continue
        quotes = video.transcript.appreciation.get("goldenQuotes", [])
        for q in quotes:
            all_quotes.append({
                "en": q.get("en", ""),
                "zh": q.get("zh", ""),
                "videoId": video.id,
                "videoTitle": video.title,
                "channel": video.channel,
            })

    random.shuffle(all_quotes)
    return {
        "total": len(all_quotes),
        "quotes": all_quotes[:limit],
    }


# ── Video list: public catalog ───────────────────────────

@router.get("/videos")
async def public_videos(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    featured: bool = Query(False),
):
    """List publicly available videos."""
    q = db.query(Video).filter(Video.status == "ready", Video.is_public == True)
    if featured:
        q = q.filter(Video.is_featured == True)
    q = q.order_by(Video.created_at.desc())

    total = q.count()
    videos = q.offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "videos": [
            {
                "id": v.id,
                "title": v.title,
                "source": v.source,
                "channel": v.channel,
                "duration": v.duration,
                "thumbnail": v.thumbnail,
                "category": v.category,
                "hasTranscript": v.transcript is not None,
                "hasAppreciation": v.transcript is not None and v.transcript.appreciation is not None,
                "createdAt": v.created_at.isoformat() if v.created_at else None,
            }
            for v in videos
        ],
    }


# ── Search: keyword + semantic ───────────────────────────

@router.get("/search")
async def search_content(
    q: str = Query(..., min_length=1, max_length=200),
    mode: str = Query("keyword", pattern="^(keyword|semantic)$"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Search across all video content.

    Modes:
    - keyword: exact text match across EN segments, titles, full_text
    - semantic: AI-powered concept matching (slower, more precise)
    """
    if mode == "keyword":
        return _keyword_search(db, q, limit)
    return await _semantic_search(db, q, limit)


def _keyword_search(db: Session, query: str, limit: int) -> dict:
    """Case-insensitive keyword search across segments and titles."""
    query_lower = query.lower()
    videos = _get_all_ready_videos(db)
    results: list[dict] = []

    for video in videos:
        # Search in title
        title_match = query_lower in (video.title or "").lower()

        if not _video_has_segments(video):
            if title_match:
                results.append({
                    "videoId": video.id,
                    "videoTitle": video.title,
                    "channel": video.channel,
                    "source": video.source,
                    "matchType": "title",
                    "matches": [],
                })
            continue

        # Search in merged segments
        merged = _merge_segments(video.transcript.segments)
        segment_matches = []
        for i, m in enumerate(merged):
            en = m["en"]
            if query_lower in en.lower():
                segment_matches.append({
                    "en": en,
                    "zh": m["zh"],
                    "timestamp": _format_timestamp(m["start"]),
                    "index": i,
                })

        if segment_matches or title_match:
            results.append({
                "videoId": video.id,
                "videoTitle": video.title,
                "channel": video.channel,
                "source": video.source,
                "matchType": "segment" if segment_matches else "title",
                "matches": segment_matches,
            })

    # Sort: segment matches first (more relevant), then by match count
    results.sort(key=lambda r: len(r["matches"]), reverse=True)

    return {
        "query": query,
        "mode": "keyword",
        "total": len(results),
        "results": results[:limit],
    }


_SEMANTIC_SYSTEM = """You are a precise content relevance scorer.
Given a user query (a concept or topic) and a list of video summaries,
score each video's relevance to the query on a scale of 0-100.

Rules:
- 0 = completely unrelated
- 100 = directly discusses this exact concept
- Be STRICT: only score >60 if the content genuinely relates to the concept
- Consider both explicit mentions AND implicit thematic connections
- Output ONLY a JSON array of objects: [{"id": "video_id", "score": N, "reason": "brief explanation"}]
- Order by score descending
- Exclude videos with score < 30"""

# Provider preference
_PROVIDERS = ["openai", "groq"]


async def _semantic_search(db: Session, query: str, limit: int) -> dict:
    """AI-powered concept matching across video content."""
    from meei.chat import chat

    videos = _get_all_ready_videos(db)

    # Build summaries for each video
    video_summaries = []
    video_map = {}
    for v in videos:
        if not v.transcript:
            continue

        summary_parts = [f"Title: {v.title or 'Untitled'}"]

        appreciation = v.transcript.appreciation or {}
        if appreciation.get("theme"):
            summary_parts.append(f"Theme: {appreciation['theme']}")
        if appreciation.get("keyPoints"):
            summary_parts.append(f"Key points: {'; '.join(appreciation['keyPoints'][:3])}")

        # Use first few merged sentences for context
        if _video_has_segments(v):
            merged = _merge_segments(v.transcript.segments)
            sample = [m["en"] for m in merged[:5]]
            summary_parts.append(f"Content sample: {' '.join(sample)}")

        video_summaries.append({
            "id": v.id,
            "summary": " | ".join(summary_parts),
        })
        video_map[v.id] = v

    if not video_summaries:
        return {"query": query, "mode": "semantic", "total": 0, "results": []}

    # Ask LLM to score relevance
    prompt = f"""User query: "{query}"

Videos to evaluate:
{json.dumps(video_summaries, ensure_ascii=False, indent=1)}"""

    response = None
    last_error = None
    for pv in _PROVIDERS:
        try:
            response = chat.ask(prompt, pv=pv, system=_SEMANTIC_SYSTEM, temperature=0.2)
            break
        except Exception as e:
            last_error = e
            continue

    if response is None:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {last_error}")

    # Parse scores
    scored = _parse_semantic_scores(response)

    # Build results
    results = []
    for item in scored[:limit]:
        vid = item.get("id", "")
        video = video_map.get(vid)
        if not video:
            continue

        result: dict = {
            "videoId": video.id,
            "videoTitle": video.title,
            "channel": video.channel,
            "source": video.source,
            "score": item.get("score", 0),
            "reason": item.get("reason", ""),
        }

        # Include best matching segments if available
        if _video_has_segments(video):
            merged = _merge_segments(video.transcript.segments)
            result["sampleSegments"] = [
                {"en": m["en"], "zh": m["zh"], "timestamp": _format_timestamp(m["start"])}
                for m in merged[:3]
            ]

        results.append(result)

    return {
        "query": query,
        "mode": "semantic",
        "total": len(results),
        "results": results,
    }


def _parse_semantic_scores(response: str) -> list[dict]:
    """Parse LLM response into scored results."""
    text = response.strip()

    # Strip markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # Find JSON array
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return []

    try:
        result = json.loads(text[start:end + 1])
        if isinstance(result, list):
            # Sort by score descending
            return sorted(result, key=lambda x: x.get("score", 0), reverse=True)
    except json.JSONDecodeError:
        pass

    return []
