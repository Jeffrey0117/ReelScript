"""
Internal bridge for the sister site (takeENGLISH): its members paste a video link,
this engine downloads and transcribes it locally (Whisper) WITHOUT any paid LLM step.

  POST /api/internal/videos            { url, owner }  → { id, status }
  GET  /api/internal/videos?owner=…                    → { videos: [...] }
  GET  /api/internal/videos/{id}?owner=…               → lesson (status, timed sentences)

owner is the sister site's member id, prefixed (e.g. "te:usr_123"); it is stored in
user_videos so each member only sees their own list. Guarded by ANNOTATE_TOKEN (the
same internal key the annotation bridge uses); disabled when it is unset.
"""

import os
import re
import hmac
import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import get_db, Video, UserVideo
from services.downloader import get_video_info
from api.video_routes import _is_valid_url, _ensure_user_video, _process_pipeline
from api.public_routes import _merge_segments, _video_has_segments

router = APIRouter(prefix="/api/internal/videos", tags=["internal"])

OWNER_PATTERN = re.compile(r"^te:[A-Za-z0-9_-]{1,80}$")
ID_PATTERN = re.compile(r"^[0-9a-f-]{36}$")
MAX_URL_CHARS = 500
# 每個會員 30 天內最多新增幾支(轉文字吃主機效能)
MAX_NEW_PER_30_DAYS = int(os.environ.get("SISTER_MAX_VIDEOS_PER_30_DAYS", "30"))


def _require_token(authorization: str | None) -> None:
    token = os.environ.get("ANNOTATE_TOKEN", "")
    if not token:
        raise HTTPException(status_code=503, detail="Internal bridge not configured")
    supplied = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
    if not supplied or not hmac.compare_digest(supplied.encode("utf-8"), token.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid internal token")


def _owner(value: str) -> str:
    if not OWNER_PATTERN.match(value or ""):
        raise HTTPException(status_code=400, detail="Invalid owner")
    return value


def _summary(video: Video, added_at: datetime | None = None) -> dict:
    return {
        "id": video.id,
        "title": video.title or "",
        "channel": video.channel or "",
        "source": video.source or "",
        "duration": video.duration,
        "status": video.status,
        "error": video.error_message or "",
        "thumbnail": video.thumbnail,
        "addedAt": added_at.isoformat() if added_at else None,
    }


class AddRequest(BaseModel):
    url: str
    owner: str


@router.post("")
async def add_video(req: AddRequest, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    _require_token(authorization)
    owner = _owner(req.owner)
    url = (req.url or "").strip()
    if len(url) > MAX_URL_CHARS or not _is_valid_url(url):
        raise HTTPException(status_code=400, detail="unsupported_url")

    existing = db.query(Video).filter(Video.url == url).first()
    if existing and existing.status != "failed":
        # 已經處理過(或正在處理):直接加進這個會員的清單,不重做
        _ensure_user_video(db, owner, existing.id)
        return {"success": True, "video": _summary(existing), "duplicate": True}

    since = datetime.utcnow() - timedelta(days=30)
    recent = db.query(UserVideo).filter(UserVideo.user_id == owner, UserVideo.added_at >= since).count()
    if recent >= MAX_NEW_PER_30_DAYS:
        raise HTTPException(status_code=429, detail="monthly_limit")

    if existing:
        # 之前失敗過:重試,而且這次一定不用 AI
        existing.status = "downloading"
        existing.error_message = None
        existing.ai_enabled = False
        db.commit()
        video = existing
    else:
        info = await get_video_info(url)
        video = Video(
            url=url,
            title=info.get("title"),
            source=info.get("source", "unknown"),
            content_type=info.get("content_type", "video"),
            duration=info.get("duration"),
            thumbnail=info.get("thumbnail"),
            channel=info.get("channel"),
            status="downloading",
            is_public=False,
            ai_enabled=False,
        )
        db.add(video)
        db.commit()
        db.refresh(video)

    _ensure_user_video(db, owner, video.id)
    asyncio.create_task(_process_pipeline(video.id, url, owner))
    return {"success": True, "video": _summary(video), "duplicate": False}


@router.get("")
async def list_videos(owner: str = Query(...), db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    _require_token(authorization)
    owner = _owner(owner)
    links = (
        db.query(UserVideo)
        .filter(UserVideo.user_id == owner)
        .order_by(UserVideo.added_at.desc())
        .limit(200)
        .all()
    )
    return {"videos": [_summary(link.video, link.added_at) for link in links if link.video]}


@router.get("/{video_id}")
async def get_video(video_id: str, owner: str = Query(...), db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    _require_token(authorization)
    owner = _owner(owner)
    if not ID_PATTERN.match(video_id):
        raise HTTPException(status_code=404, detail="Video not found")
    link = db.query(UserVideo).filter(UserVideo.user_id == owner, UserVideo.video_id == video_id).first()
    video = link.video if link else None
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    segments = []
    if video.status == "ready" and _video_has_segments(video):
        raw = video.transcript.segments
        if any((s.get("translation") or "").strip() for s in raw):
            for m in _merge_segments(raw):
                segments.append({"start": m["start"], "end": m["end"], "en": m["en"], "zh": m["zh"], "vocabulary": m.get("vocabulary", [])})
        else:
            # 沒翻譯的(不用 AI 的影片):原樣給逐段字幕,由呼叫端併成句子
            for s in raw:
                text = (s.get("text") or "").strip()
                if text:
                    segments.append({"start": s.get("start", 0), "end": s.get("end", 0), "en": text, "zh": "", "vocabulary": []})

    appreciation = (video.transcript.appreciation or {}) if video.transcript else {}
    return {
        **_summary(video, link.added_at),
        "filename": video.filename,
        "theme": appreciation.get("theme", ""),
        "keyPoints": [str(x) for x in (appreciation.get("keyPoints") or []) if x],
        "goldenQuotes": appreciation.get("goldenQuotes") or [],
        "segments": segments,
    }
