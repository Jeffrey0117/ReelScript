"""
Speaking Coach API routes — upload audio, transcribe, analyze.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session

from models import get_db, SpeakingSession, UserQuota, Subscription
from middleware.auth import require_auth
from api.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/speaking", tags=["speaking"])

SPEAKING_DIR = Path("./data/speaking")
SPEAKING_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_PREFIXES = ("audio/", "video/")

FREE_MONTHLY_LIMIT = 30
PRO_MONTHLY_LIMIT = 200
COST_SPEAKING = 5


def _get_user_id(user: dict) -> str:
    return user.get("sub", "")


def _is_admin(user: dict) -> bool:
    return user.get("role") == "admin"


def _get_or_create_quota(db: Session, user_id: str) -> UserQuota:
    period = datetime.utcnow().strftime("%Y-%m")
    quota = db.query(UserQuota).filter(
        UserQuota.user_id == user_id, UserQuota.period == period
    ).first()
    if not quota:
        quota = UserQuota(user_id=user_id, period=period)
        db.add(quota)
        db.commit()
        db.refresh(quota)
    return quota


def _get_credit_limit(db: Session, user: dict) -> int:
    email = user.get("email", "")
    if email:
        sub = db.query(Subscription).filter(
            Subscription.email == email, Subscription.status == "active"
        ).first()
        if sub:
            if sub.tier == "unlimited":
                return -1
            if sub.tier == "pro":
                return PRO_MONTHLY_LIMIT
    return FREE_MONTHLY_LIMIT


def _check_quota(quota: UserQuota, limit: int, cost: int = COST_SPEAKING) -> bool:
    if limit == -1:
        return True
    return quota.credits_used + cost <= limit + quota.bonus_credits


@router.post("/upload")
async def upload_speaking(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(require_auth),
):
    user_id = _get_user_id(user)
    is_admin = _is_admin(user)

    # Validate MIME type
    content_type = file.content_type or ""
    if not any(content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(status_code=400, detail="請上傳音訊或影片檔案")

    # Pre-check Content-Length to reject oversized uploads early
    cl = request.headers.get("content-length")
    if cl and int(cl) > MAX_FILE_SIZE + 4096:  # small margin for multipart overhead
        raise HTTPException(status_code=400, detail="檔案大小不能超過 50MB")

    # Check quota before reading file
    if not is_admin:
        quota = _get_or_create_quota(db, user_id)
        limit = _get_credit_limit(db, user)
        if not _check_quota(quota, limit, COST_SPEAKING):
            raise HTTPException(status_code=429, detail="本月點數已用完")

    # Read file and verify size
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="檔案大小不能超過 50MB")

    # Save file
    ext = _get_extension(file.filename or "recording.webm", content_type)
    session_id = str(uuid.uuid4())
    filename = f"{session_id}.{ext}"
    filepath = SPEAKING_DIR / filename
    filepath.write_bytes(data)

    # Create session record
    session = SpeakingSession(
        id=session_id,
        user_id=user_id,
        title=_generate_title(file.filename),
        filename=filename,
        status="transcribing",
    )
    db.add(session)

    # Deduct credits
    if not is_admin:
        quota.credits_used += COST_SPEAKING
    db.commit()

    # Launch async pipeline
    asyncio.create_task(_speaking_pipeline(session_id, user_id))

    return {"success": True, "session_id": session_id, "status": "transcribing"}


@router.get("")
async def list_speaking(
    db: Session = Depends(get_db),
    user: dict = Depends(require_auth),
):
    user_id = _get_user_id(user)
    sessions = (
        db.query(SpeakingSession)
        .filter(SpeakingSession.user_id == user_id)
        .order_by(SpeakingSession.created_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "title": s.title,
            "duration": s.duration,
            "status": s.status,
            "error_message": s.error_message,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "overall_score": _extract_overall_score(s.coaching),
        }
        for s in sessions
    ]


@router.get("/{session_id}")
async def get_speaking(
    session_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_auth),
):
    user_id = _get_user_id(user)
    session = db.query(SpeakingSession).filter(
        SpeakingSession.id == session_id,
        SpeakingSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "title": session.title,
        "filename": session.filename,
        "duration": session.duration,
        "status": session.status,
        "error_message": session.error_message,
        "segments": session.segments,
        "coaching": session.coaching,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


@router.delete("/{session_id}")
async def delete_speaking(
    session_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_auth),
):
    user_id = _get_user_id(user)
    session = db.query(SpeakingSession).filter(
        SpeakingSession.id == session_id,
        SpeakingSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete file
    if session.filename:
        filepath = SPEAKING_DIR / session.filename
        if filepath.exists():
            filepath.unlink()

    db.delete(session)
    db.commit()
    return {"success": True}


# --- Pipeline ---

async def _speaking_pipeline(session_id: str, user_id: str):
    from models.database import SessionLocal
    from services.transcriber import transcriber
    from services.speaking_coach import analyze_speaking

    db = SessionLocal()
    try:
        session = db.query(SpeakingSession).filter(SpeakingSession.id == session_id).first()
        if not session:
            return

        filepath = str(SPEAKING_DIR / session.filename)

        # Step 1: Transcribe
        await manager.broadcast(
            {"type": "speaking_transcribe_started", "data": {"session_id": session_id}},
            user_id=user_id,
        )

        from api.video_routes import enqueue_transcription
        segments = await enqueue_transcription(filepath)
        segment_dicts = transcriber.segments_to_dict(segments)

        session.segments = segment_dicts
        session.duration = segments[-1].end if segments else None
        session.status = "analyzing"
        db.commit()

        # Step 2: LLM coaching analysis
        await manager.broadcast(
            {"type": "speaking_analyze_started", "data": {"session_id": session_id}},
            user_id=user_id,
        )

        loop = asyncio.get_running_loop()
        coaching = await loop.run_in_executor(None, analyze_speaking, segment_dicts)

        session.coaching = coaching
        session.status = "ready"
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "coaching")
        flag_modified(session, "segments")
        db.commit()

        await manager.broadcast(
            {"type": "speaking_completed", "data": {"session_id": session_id}},
            user_id=user_id,
        )

    except Exception as e:
        logger.error(f"[SpeakingPipeline] Failed for {session_id}: {e}")
        session = db.query(SpeakingSession).filter(SpeakingSession.id == session_id).first()
        if session:
            session.status = "failed"
            session.error_message = str(e)[:500]
            db.commit()
        await manager.broadcast(
            {"type": "speaking_error", "data": {"session_id": session_id, "error": str(e)}},
            user_id=user_id,
        )
    finally:
        db.close()


# --- Helpers ---

def _get_extension(filename: str, content_type: str) -> str:
    """Extract file extension from filename or content type."""
    mime_map = {
        "audio/webm": "webm",
        "audio/mp3": "mp3",
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/ogg": "ogg",
        "audio/m4a": "m4a",
        "audio/mp4": "m4a",
        "video/mp4": "mp4",
        "video/webm": "webm",
    }
    if "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        # Only allow safe alphanumeric extensions
        if ext.isalnum() and len(ext) <= 10:
            return ext
    return mime_map.get(content_type, "webm")


def _generate_title(filename: str | None) -> str:
    """Generate a simple title from filename."""
    if not filename:
        return "Speaking Session"
    name = filename.rsplit(".", 1)[0] if "." in filename else filename
    # Clean up common recording filenames
    if name.lower() in ("recording", "audio", "voice", "blob"):
        return "Speaking Session"
    return name[:100]


def _extract_overall_score(coaching: dict | None) -> float | None:
    """Extract an average overall score for list display."""
    if not coaching or "overall" not in coaching:
        return None
    overall = coaching["overall"]
    scores = [
        overall.get("fluency", 0),
        overall.get("grammar", 0),
        overall.get("vocabulary", 0),
        overall.get("naturalness", 0),
    ]
    valid = [s for s in scores if s > 0]
    if not valid:
        return None
    return round(sum(valid) / len(valid), 1)
