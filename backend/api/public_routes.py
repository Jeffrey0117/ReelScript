"""
Public API routes — open endpoints for external consumption.
No auth required. Serves learning snippets, cards, articles, vocabulary.
"""

import random
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models import get_db, Video, Transcript
from services.downloader import VIDEOS_DIR, extract_audio

router = APIRouter(prefix="/api/public", tags=["public"])


def _format_timestamp(seconds: float) -> str:
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"


def _get_ready_videos(db: Session):
    return (
        db.query(Video)
        .filter(Video.status == "ready", Video.is_featured == True)
        .all()
    )


def _get_all_ready_videos(db: Session):
    return db.query(Video).filter(Video.status == "ready").all()


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
    video = db.query(Video).filter(Video.id == video_id, Video.status == "ready").first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not _video_has_segments(video):
        raise HTTPException(status_code=404, detail="No transcript available")

    segments = video.transcript.segments
    return {
        "videoId": video.id,
        "videoTitle": video.title,
        "source": video.source,
        "channel": video.channel,
        "duration": video.duration,
        "totalCards": len(segments),
        "cards": [_segment_to_card(seg, video, len(segments)) for seg in segments],
    }


# ── Audio: extract and serve MP3 ──────────────────────────

@router.get("/videos/{video_id}/audio")
async def video_audio(video_id: str, db: Session = Depends(get_db)):
    """Get audio URL + timeline for a video (extracts MP3 on first request)."""
    video = db.query(Video).filter(Video.id == video_id, Video.status == "ready").first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.filename:
        raise HTTPException(status_code=404, detail="No video file available")

    # Extract MP3 (cached after first extraction)
    video_path = VIDEOS_DIR / video.filename
    audio_filename = extract_audio(video_path, video_id)
    if not audio_filename:
        raise HTTPException(status_code=500, detail="Audio extraction failed")

    # Build timeline from segments
    segments = []
    if _video_has_segments(video):
        segments = [
            {
                "index": seg.get("index", i),
                "start": seg.get("start", 0),
                "end": seg.get("end", 0),
                "en": seg.get("text", ""),
                "zh": seg.get("translation", ""),
            }
            for i, seg in enumerate(video.transcript.segments)
        ]

    return {
        "videoId": video.id,
        "title": video.title,
        "channel": video.channel,
        "duration": video.duration,
        "audioUrl": f"/audio/{audio_filename}",
        "segments": segments,
    }


# ── Article: blog-ready structured content ───────────────

@router.get("/videos/{video_id}/article")
async def video_article(video_id: str, db: Session = Depends(get_db)):
    """Get blog-ready article data for a video."""
    video = db.query(Video).filter(Video.id == video_id, Video.status == "ready").first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.transcript:
        raise HTTPException(status_code=404, detail="No transcript available")

    t = video.transcript
    appreciation = t.appreciation or {}
    segments = t.segments or []

    # Collect all vocabulary from segments
    all_vocab = []
    seen_words = set()
    for seg in segments:
        for v in seg.get("vocabulary", []):
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
                "index": seg.get("index", i),
                "timestamp": _format_timestamp(seg.get("start", 0)),
                "en": seg.get("text", ""),
                "zh": seg.get("translation", ""),
            }
            for i, seg in enumerate(segments)
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
    q = db.query(Video).filter(Video.status == "ready")
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
