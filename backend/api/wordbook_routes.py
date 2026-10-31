"""
Wordbook API routes — personal saved words with Leitner SRS review.
All endpoints require auth. Saving/reviewing words costs no quota.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models import get_db, SavedWord
from middleware.auth import require_auth

router = APIRouter(prefix="/api/wordbook", tags=["wordbook"])

# Leitner box → days until next review after a correct answer.
BOX_INTERVAL_DAYS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}
MAX_BOX = 5
LAPSE_RETRY_MINUTES = 10


class SaveWordRequest(BaseModel):
    word: str = Field(min_length=1, max_length=100)
    meaning: Optional[str] = Field(default=None, max_length=500)
    example: Optional[str] = Field(default=None, max_length=1000)
    video_id: Optional[str] = None


class ReviewRequest(BaseModel):
    correct: bool


def _get_user_id(user: dict) -> str:
    return user.get("sub", "")


def _word_dict(w: SavedWord) -> dict:
    return {
        "id": w.id,
        "word": w.word,
        "meaning": w.meaning,
        "example": w.example,
        "video_id": w.video_id,
        "box": w.box,
        "due_at": w.due_at.isoformat() if w.due_at else None,
        "reviews": w.reviews,
        "lapses": w.lapses,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


@router.post("")
async def save_word(req: SaveWordRequest, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    """Upsert a word. Re-saving updates meaning/example but keeps SRS progress."""
    user_id = _get_user_id(user)
    word = req.word.strip()
    if not word:
        raise HTTPException(status_code=400, detail="Word is empty")

    existing = db.query(SavedWord).filter(SavedWord.user_id == user_id, SavedWord.word == word).first()
    if existing:
        if req.meaning:
            existing.meaning = req.meaning
        if req.example:
            existing.example = req.example
        if req.video_id:
            existing.video_id = req.video_id
        db.commit()
        return {"success": True, "saved": _word_dict(existing), "duplicate": True}

    saved = SavedWord(
        user_id=user_id,
        word=word,
        meaning=req.meaning,
        example=req.example,
        video_id=req.video_id,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return {"success": True, "saved": _word_dict(saved), "duplicate": False}


@router.get("")
async def list_words(db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    words = (
        db.query(SavedWord)
        .filter(SavedWord.user_id == user_id)
        .order_by(SavedWord.created_at.desc())
        .all()
    )
    now = datetime.utcnow()
    due = sum(1 for w in words if w.due_at and w.due_at <= now)
    return {"total": len(words), "due": due, "words": [_word_dict(w) for w in words]}


@router.get("/review")
async def review_queue(
    db: Session = Depends(get_db),
    user: dict = Depends(require_auth),
    limit: int = Query(20, ge=1, le=100),
):
    """Due cards, lowest box (weakest) first."""
    user_id = _get_user_id(user)
    now = datetime.utcnow()
    words = (
        db.query(SavedWord)
        .filter(SavedWord.user_id == user_id, SavedWord.due_at <= now)
        .order_by(SavedWord.box.asc(), SavedWord.due_at.asc())
        .limit(limit)
        .all()
    )
    return {"cards": [_word_dict(w) for w in words]}


@router.post("/{word_id}/review")
async def review_word(word_id: str, req: ReviewRequest, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    w = db.query(SavedWord).filter(SavedWord.id == word_id, SavedWord.user_id == user_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Word not found")

    now = datetime.utcnow()
    w.reviews = (w.reviews or 0) + 1
    if req.correct:
        w.box = min(MAX_BOX, (w.box or 1) + 1)
        w.due_at = now + timedelta(days=BOX_INTERVAL_DAYS[w.box])
    else:
        w.box = 1
        w.lapses = (w.lapses or 0) + 1
        w.due_at = now + timedelta(minutes=LAPSE_RETRY_MINUTES)
    db.commit()
    return {"success": True, "word": _word_dict(w)}


@router.delete("/{word_id}")
async def delete_word(word_id: str, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    w = db.query(SavedWord).filter(SavedWord.id == word_id, SavedWord.user_id == user_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Word not found")
    db.delete(w)
    db.commit()
    return {"success": True}


@router.get("/export")
async def export_tsv(db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    """Anki-importable TSV: word <tab> meaning <tab> example."""
    user_id = _get_user_id(user)
    words = (
        db.query(SavedWord)
        .filter(SavedWord.user_id == user_id)
        .order_by(SavedWord.created_at.asc())
        .all()
    )

    def clean(s: Optional[str]) -> str:
        return (s or "").replace("\t", " ").replace("\n", " ").strip()

    lines = [f"{clean(w.word)}\t{clean(w.meaning)}\t{clean(w.example)}" for w in words]
    return PlainTextResponse(
        "\n".join(lines),
        media_type="text/tab-separated-values; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="reelscript-wordbook.txt"'},
    )
