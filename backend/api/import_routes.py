"""
AutoReel import bridge — receives finished IG content from AutoReel.

AutoReel already ran whisper + translation before posting to IG, so this
endpoint lands a completed Video + Transcript directly, skipping the whole
download/transcribe/translate pipeline. Imported videos immediately show up
in the public blog (/blog), article pages and search.

Auth: Bearer token == env AUTOREEL_IMPORT_TOKEN (shared secret with AutoReel).
Idempotent: re-import with the same source_url updates the existing record.
"""

import base64
import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import Video, Transcript, get_db

router = APIRouter(prefix="/api/import", tags=["import"])
logger = logging.getLogger(__name__)

THUMBS_DIR = Path("./data/thumbnails")
MAX_THUMB_BYTES = 2 * 1024 * 1024


class ImportSegment(BaseModel):
    index: int = 0
    start: float = 0
    end: float = 0
    text: str = ""
    translation: str = ""


class AutoreelPayload(BaseModel):
    external_id: str
    title: str
    source_url: str | None = None
    channel: str | None = None       # 原作者
    caption: str | None = None       # IG 文案
    segments: list[ImportSegment] = []
    posted_at: str | None = None     # ISO datetime of the IG post
    thumbnail_b64: str | None = None  # optional JPEG, base64
    category: str | None = None


def _require_token(authorization: str | None) -> None:
    token = os.environ.get("AUTOREEL_IMPORT_TOKEN", "")
    if not token:
        raise HTTPException(status_code=503, detail="Import bridge not configured")
    supplied = ""
    if authorization and authorization.startswith("Bearer "):
        supplied = authorization[7:]
    if not supplied or supplied != token:
        raise HTTPException(status_code=401, detail="Invalid import token")


def _save_thumbnail(video_id: str, b64: str) -> str | None:
    try:
        raw = base64.b64decode(b64)
        if not raw or len(raw) > MAX_THUMB_BYTES:
            return None
        THUMBS_DIR.mkdir(parents=True, exist_ok=True)
        name = f"{video_id}.jpg"
        (THUMBS_DIR / name).write_bytes(raw)
        return name
    except Exception as e:  # thumbnail is best-effort, never fail the import
        logger.warning(f"[import] thumbnail save failed: {e}")
        return None


@router.post("/autoreel")
async def import_autoreel(
    payload: AutoreelPayload,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    _require_token(authorization)

    if not payload.title.strip() and not payload.segments:
        raise HTTPException(status_code=400, detail="Empty payload")

    dedup_url = (payload.source_url or "").strip() or f"autoreel://{payload.external_id}"

    video = db.query(Video).filter(Video.url == dedup_url).first()
    created = video is None
    if created:
        video = Video(url=dedup_url)
        db.add(video)
        db.flush()  # allocate video.id for the thumbnail filename

    video.title = payload.title.strip() or video.title
    video.source = "ig"
    video.channel = payload.channel or video.channel
    video.category = payload.category or video.category
    video.status = "ready"
    video.is_public = True  # AutoReel content is the public blog/marketing feed
    video.error_message = None
    if video.completed_at is None:
        video.completed_at = datetime.utcnow()

    if payload.thumbnail_b64:
        name = _save_thumbnail(video.id, payload.thumbnail_b64)
        if name:
            video.thumbnail = name

    segments = [
        {
            "index": s.index,
            "start": s.start,
            "end": s.end,
            "text": s.text,
            "translation": s.translation,
        }
        for s in payload.segments
    ]
    full_text = " ".join(s.text.strip() for s in payload.segments if s.text.strip())

    appreciation = {
        "theme": (payload.caption or "").strip(),
        "keyPoints": [],
        "goldenQuotes": [],
        "igCaption": (payload.caption or "").strip(),
        "importedFrom": "autoreel",
        "autoreelId": payload.external_id,
        "postedAt": payload.posted_at,
    }

    transcript = db.query(Transcript).filter(Transcript.video_id == video.id).first()
    if transcript is None:
        transcript = Transcript(video_id=video.id)
        db.add(transcript)
    transcript.language = "en"
    transcript.segments = segments
    transcript.full_text = full_text or transcript.full_text
    # 保留既有 appreciation 裡人工補過的欄位,只覆寫 import 相關的
    existing = transcript.appreciation or {}
    transcript.appreciation = {**existing, **{k: v for k, v in appreciation.items() if v not in (None, "")}} or appreciation

    db.commit()

    logger.info(f"[import] autoreel {'created' if created else 'updated'} video={video.id} title={video.title!r}")
    return {
        "id": video.id,
        "created": created,
        "blogUrl": f"/blog/{video.id}",
    }
