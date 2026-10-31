"""
Shared deck API routes — members publish snapshots of their wordbook,
others save a whole deck into their own wordbook. saves_count (deduped
via deck_saves) is the contributor reputation metric.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models import get_db, User, SavedWord, SharedDeck, SharedDeckWord, DeckSave
from middleware.auth import require_auth

router = APIRouter(prefix="/api/decks", tags=["decks"])

MAX_DECK_WORDS = 500


class PublishDeckRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    word_ids: list[str] = Field(min_length=1, max_length=MAX_DECK_WORDS)


def _get_user_id(user: dict) -> str:
    return user.get("sub", "")


def _author_name(db: Session, user: dict) -> str:
    """Display name snapshot: local user cache name, else email prefix."""
    user_id = _get_user_id(user)
    cached = db.query(User).filter(User.id == user_id).first()
    if cached and cached.name:
        return cached.name
    email = (user.get("email") or "").strip()
    return email.split("@")[0] if email else "member"


def _deck_summary(d: SharedDeck) -> dict:
    return {
        "id": d.id,
        "title": d.title,
        "description": d.description,
        "author_name": d.author_name,
        "word_count": len(d.words),
        "saves_count": d.saves_count or 0,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


@router.post("")
async def publish_deck(req: PublishDeckRequest, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    words = (
        db.query(SavedWord)
        .filter(SavedWord.user_id == user_id, SavedWord.id.in_(req.word_ids))
        .all()
    )
    if not words:
        raise HTTPException(status_code=400, detail="No valid words selected")

    # Preserve the caller's selection order.
    by_id = {w.id: w for w in words}
    ordered = [by_id[wid] for wid in req.word_ids if wid in by_id]

    deck = SharedDeck(
        user_id=user_id,
        author_name=_author_name(db, user),
        title=req.title.strip(),
        description=(req.description or "").strip() or None,
    )
    db.add(deck)
    db.flush()
    for i, w in enumerate(ordered):
        db.add(SharedDeckWord(deck_id=deck.id, word=w.word, meaning=w.meaning, example=w.example, position=i))
    db.commit()
    db.refresh(deck)
    return {"success": True, "deck": _deck_summary(deck)}


@router.get("/mine")
async def my_decks(db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    decks = (
        db.query(SharedDeck)
        .filter(SharedDeck.user_id == user_id)
        .order_by(SharedDeck.created_at.desc())
        .all()
    )
    return {"decks": [_deck_summary(d) for d in decks]}


@router.delete("/{deck_id}")
async def delete_deck(deck_id: str, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    deck = db.query(SharedDeck).filter(SharedDeck.id == deck_id, SharedDeck.user_id == user_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    db.delete(deck)
    db.commit()
    return {"success": True}


@router.post("/{deck_id}/save")
async def save_deck(deck_id: str, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    """Copy every deck word into my wordbook. Existing words keep their SRS progress."""
    user_id = _get_user_id(user)
    deck = db.query(SharedDeck).filter(SharedDeck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    mine = {
        w.word: w
        for w in db.query(SavedWord).filter(SavedWord.user_id == user_id).all()
    }
    added = 0
    for dw in deck.words:
        existing = mine.get(dw.word)
        if existing:
            if not existing.meaning and dw.meaning:
                existing.meaning = dw.meaning
            continue
        db.add(SavedWord(user_id=user_id, word=dw.word, meaning=dw.meaning, example=dw.example))
        added += 1

    first_save = False
    if deck.user_id != user_id:
        already = db.query(DeckSave).filter(DeckSave.deck_id == deck_id, DeckSave.user_id == user_id).first()
        if not already:
            db.add(DeckSave(deck_id=deck_id, user_id=user_id))
            deck.saves_count = (deck.saves_count or 0) + 1
            first_save = True

    db.commit()
    return {"success": True, "added": added, "total": len(deck.words), "first_save": first_save}
