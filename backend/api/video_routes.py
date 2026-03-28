"""
Video API routes — download, transcribe, list, get, delete.
Per-user isolation via UserVideo junction table.

Scalability features:
- Pipeline semaphore: max 6 concurrent pipelines (global)
- Per-user limit: max 2 concurrent pipelines per user
- Transcription queue: serializes Whisper access (single model bottleneck)
- Crash recovery: re-queues stuck videos on startup
"""

import asyncio
import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import get_db, Video, Transcript, UserVideo, UserQuota, Subscription
from middleware.auth import require_auth, require_admin, optional_auth
from services.downloader import download_video, get_video_info, generate_thumbnail, detect_content_type, VIDEOS_DIR, THUMBS_DIR
from services.transcriber import transcriber
from services.translator import translate_segments
from services.vocabulary import analyze_segments
from services.appreciation import generate_appreciation
from services.titler import generate_title_and_appreciation, generate_title_from_chinese
from api.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/videos", tags=["videos"])

FREE_MONTHLY_LIMIT = 30
PRO_MONTHLY_LIMIT = 200
COST_PROCESS = 10
COST_TRANSLATE = 3
COST_VOCABULARY = 3
COST_APPRECIATE = 3
MAX_CONCURRENT_PIPELINES = 6
MAX_PER_USER_PIPELINES = 2
_pipeline_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PIPELINES)
_user_semaphores: dict[str, asyncio.Semaphore] = {}  # per-user concurrency limit

# Transcription queue — serializes Whisper access (single GPU/model)
_transcription_queue: asyncio.Queue | None = None
_transcription_worker_task: asyncio.Task | None = None


def _get_transcription_queue() -> asyncio.Queue:
    """Lazy-init the transcription queue (must be called within event loop)."""
    global _transcription_queue, _transcription_worker_task
    if _transcription_queue is None:
        _transcription_queue = asyncio.Queue()
        _transcription_worker_task = asyncio.create_task(_transcription_worker())
        logger.info("[Queue] Transcription queue started")
    return _transcription_queue


async def _transcription_worker():
    """Single worker that processes transcription jobs one at a time."""
    while True:
        video_path, future = await _transcription_queue.get()
        try:
            loop = asyncio.get_running_loop()
            segments = await loop.run_in_executor(None, transcriber.transcribe, video_path)
            future.set_result(segments)
        except Exception as e:
            future.set_exception(e)
        finally:
            _transcription_queue.task_done()


async def enqueue_transcription(video_path: str):
    """Submit a transcription job to the queue. Returns segments when done."""
    queue = _get_transcription_queue()
    future = asyncio.get_running_loop().create_future()
    await queue.put((video_path, future))
    qsize = queue.qsize()
    if qsize > 0:
        logger.info(f"[Queue] Transcription queued (position ~{qsize})")
    return await future


async def recover_stuck_pipelines():
    """Re-queue videos stuck in 'downloading' or 'transcribing' status after a crash."""
    from models.database import SessionLocal
    db = SessionLocal()
    try:
        stuck = db.query(Video).filter(Video.status.in_(["downloading", "transcribing"])).all()
        if not stuck:
            return
        logger.info(f"[Recovery] Found {len(stuck)} stuck pipelines, re-queuing...")
        for video in stuck:
            # Look up the owner for per-user rate limiting
            user_video = db.query(UserVideo).filter(UserVideo.video_id == video.id).first()
            owner_id = user_video.user_id if user_video else ""

            # If stuck at transcribing and file exists, don't re-download
            if video.status == "transcribing" and video.filename:
                video_path = VIDEOS_DIR / video.filename
                if video_path.exists():
                    logger.info(f"[Recovery] {video.id} has file, keeping transcribing status")
                    db.commit()
                    asyncio.create_task(_process_pipeline(video.id, video.url, owner_id))
                    continue

            video.status = "downloading"
            video.error_message = None
            db.commit()
            asyncio.create_task(_process_pipeline(video.id, video.url, owner_id))
        logger.info(f"[Recovery] Re-queued {len(stuck)} videos")
    except Exception as e:
        logger.error(f"[Recovery] Failed: {e}")
    finally:
        db.close()


class ProcessRequest(BaseModel):
    url: str


class BatchProcessRequest(BaseModel):
    urls: list[str]


class RenameRequest(BaseModel):
    title: str


class BatchDeleteRequest(BaseModel):
    video_ids: list[str]


_ERROR_ZH = [
    ("Sign in to confirm", "需要登入驗證，無法下載"),
    ("Private video", "私人影片，無法存取"),
    ("Video unavailable", "影片不存在或已被刪除"),
    ("This video is private", "私人影片，無法存取"),
    ("Requested content is not available", "內容不可用，可能是私人或已刪除"),
    ("login required", "需要登入才能下載"),
    ("Sign in if you", "需要登入驗證，無法下載"),
    ("HTTP Error 429", "請求太頻繁，請稍後再試"),
    ("HTTP Error 403", "存取被拒絕"),
    ("HTTP Error 404", "影片不存在"),
    ("Unsupported URL", "不支援的連結格式"),
    ("No video formats found", "找不到可下載的影片格式"),
    ("not available in your country", "影片在你的地區不可用"),
    ("copyright", "影片因版權問題被移除"),
    ("age", "影片有年齡限制，需要登入"),
    ("geo", "影片有地區限制"),
    ("unable to extract", "無法解析此連結"),
    ("Incomplete data", "資料不完整，下載失敗"),
    ("timed out", "連線逾時，請稍後再試"),
    ("Network", "網路錯誤，請稍後再試"),
]


def _localize_error(raw: str) -> str:
    lower = raw.lower()
    for pattern, zh in _ERROR_ZH:
        if pattern.lower() in lower:
            return zh
    return f"下載失敗：{raw[:120]}"


URL_PATTERNS = [
    re.compile(r"https?://(www\.)?(music\.)?youtube\.com/"),
    re.compile(r"https?://(www\.)?youtu\.be/"),
    re.compile(r"https?://(www\.)?instagram\.com/"),
    re.compile(r"https?://(www\.)?(bilibili\.com|b23\.tv)/"),
    re.compile(r"https?://(www\.)?tiktok\.com/"),
]


def _is_valid_url(url: str) -> bool:
    return any(p.match(url) for p in URL_PATTERNS)


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
    """Returns monthly credit limit. -1 = unlimited."""
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


def _check_quota(quota: UserQuota, limit: int, cost: int = COST_PROCESS) -> bool:
    if limit == -1:
        return True
    return quota.credits_used + cost <= limit + quota.bonus_credits


def _ensure_user_video(db: Session, user_id: str, video_id: str):
    existing = db.query(UserVideo).filter(
        UserVideo.user_id == user_id, UserVideo.video_id == video_id
    ).first()
    if not existing:
        db.add(UserVideo(user_id=user_id, video_id=video_id))
        db.commit()


@router.post("/process")
async def process_video(req: ProcessRequest, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)

    if not _is_valid_url(req.url):
        raise HTTPException(status_code=400, detail="Unsupported URL. Use YouTube, Instagram, Bilibili, or TikTok links.")

    is_admin = _is_admin(user)

    # Dedup: check if this URL already exists in global pool
    existing = db.query(Video).filter(Video.url == req.url).first()
    if existing:
        if existing.status == "failed":
            if not is_admin:
                quota = _get_or_create_quota(db, user_id)
                limit = _get_credit_limit(db, user)
                if not _check_quota(quota, limit, COST_PROCESS):
                    raise HTTPException(status_code=429, detail="本月點數已用完")
                quota.credits_used += COST_PROCESS
            existing.status = "downloading"
            existing.error_message = None
            db.commit()
            _ensure_user_video(db, user_id, existing.id)
            asyncio.create_task(_process_pipeline(existing.id, existing.url, user_id))
            return {"success": True, "video_id": existing.id, "title": existing.title, "status": "downloading", "duplicate": True}
        # Already processed — just link to user (no quota cost)
        _ensure_user_video(db, user_id, existing.id)
        return {"success": True, "video_id": existing.id, "title": existing.title, "status": existing.status, "duplicate": True}

    # New video — check quota (admin/bot bypasses quota)
    if not is_admin:
        quota = _get_or_create_quota(db, user_id)
        limit = _get_credit_limit(db, user)
        if not _check_quota(quota, limit, COST_PROCESS):
            raise HTTPException(status_code=429, detail="本月點數已用完")

    info = await get_video_info(req.url)

    content_type = info.get("content_type", "video")

    video = Video(
        url=req.url,
        title=info.get("title"),
        source=info.get("source", "unknown"),
        content_type=content_type,
        duration=info.get("duration"),
        thumbnail=info.get("thumbnail"),
        channel=info.get("channel"),
        status="downloading",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    _ensure_user_video(db, user_id, video.id)
    if not is_admin:
        quota.credits_used += COST_PROCESS
    db.commit()

    asyncio.create_task(_process_pipeline(video.id, req.url, user_id))

    return {"success": True, "video_id": video.id, "title": video.title, "status": "downloading", "content_type": content_type}


@router.post("/batch-process")
async def batch_process_videos(req: BatchProcessRequest, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    is_admin = _is_admin(user)

    # Validate all URLs first (fail-fast)
    invalid = [u for u in req.urls if not _is_valid_url(u)]
    if invalid:
        raise HTTPException(status_code=400, detail=f"不支援的連結：{', '.join(invalid[:3])}")

    if not is_admin:
        quota = _get_or_create_quota(db, user_id)
        limit = _get_credit_limit(db, user)
        remaining = (limit + quota.bonus_credits) - quota.credits_used if limit != -1 else float("inf")
    else:
        remaining = float("inf")

    results = []
    credits_spent = 0

    for url in req.urls:
        existing = db.query(Video).filter(Video.url == url).first()
        if existing:
            if existing.status == "failed":
                if not is_admin and credits_spent + COST_PROCESS > remaining:
                    results.append({"url": url, "success": False, "error": "點數不足"})
                    continue
                existing.status = "downloading"
                existing.error_message = None
                db.commit()
                _ensure_user_video(db, user_id, existing.id)
                if not is_admin:
                    quota.credits_used += COST_PROCESS
                    credits_spent += COST_PROCESS
                    db.commit()
                asyncio.create_task(_process_pipeline(existing.id, existing.url, user_id))
                results.append({"url": url, "success": True, "video_id": existing.id, "status": "downloading", "duplicate": True})
            else:
                _ensure_user_video(db, user_id, existing.id)
                results.append({"url": url, "success": True, "video_id": existing.id, "status": existing.status, "duplicate": True})
            continue

        # New video — check credits
        if not is_admin and credits_spent + COST_PROCESS > remaining:
            results.append({"url": url, "success": False, "error": "點數不足"})
            continue

        try:
            info = await get_video_info(url)
        except Exception as e:
            results.append({"url": url, "success": False, "error": str(e)[:100]})
            continue

        video = Video(
            url=url,
            title=info.get("title"),
            source=info.get("source", "unknown"),
            content_type=info.get("content_type", "video"),
            duration=info.get("duration"),
            thumbnail=info.get("thumbnail"),
            channel=info.get("channel"),
            status="downloading",
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        _ensure_user_video(db, user_id, video.id)
        if not is_admin:
            quota.credits_used += COST_PROCESS
            credits_spent += COST_PROCESS
        db.commit()

        asyncio.create_task(_process_pipeline(video.id, url, user_id))
        results.append({"url": url, "success": True, "video_id": video.id, "title": video.title, "status": "downloading"})

    return {"success": True, "results": results, "total": len(results), "started": sum(1 for r in results if r.get("success"))}


async def _process_pipeline(video_id: str, url: str, user_id: str = ""):
    # Per-user concurrency via Semaphore (no race conditions)
    if user_id:
        if user_id not in _user_semaphores:
            _user_semaphores[user_id] = asyncio.Semaphore(MAX_PER_USER_PIPELINES)
        user_sem = _user_semaphores[user_id]
        async with user_sem:
            async with _pipeline_semaphore:
                await _process_pipeline_inner(video_id, url)
    else:
        async with _pipeline_semaphore:
            await _process_pipeline_inner(video_id, url)


async def _process_pipeline_inner(video_id: str, url: str):
    from models.database import SessionLocal

    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return

        ct = video.content_type or "video"
        result = await download_video(url, video_id, content_type=ct)

        if not result.get("success"):
            video.status = "failed"
            video.error_message = _localize_error(result.get("error", "Download failed"))
            db.commit()
            return

        video.filename = result.get("filename")
        video.title = result.get("title") or video.title
        video.duration = result.get("duration") or video.duration
        video.channel = result.get("channel") or video.channel
        video.source = result.get("source") or video.source

        if video.filename:
            thumb = await asyncio.to_thread(
                generate_thumbnail, VIDEOS_DIR / video.filename, video_id
            )
            if thumb:
                video.thumbnail = thumb

        video.status = "transcribing"
        db.commit()

        await manager.broadcast({"type": "transcribe_started", "data": {"video_id": video_id}})

        video_path = str(VIDEOS_DIR / video.filename)
        loop = asyncio.get_running_loop()
        segments = await enqueue_transcription(video_path)

        # Convert to dict format
        segment_dicts = transcriber.segments_to_dict(segments)

        # Translate segments immediately after transcription
        try:
            ct = video.content_type or "video"
            print(f"[Pipeline] Translating {len(segment_dicts)} segments (content_type={ct})...")
            translated_segments = await loop.run_in_executor(None, translate_segments, segment_dicts, ct)
            segment_dicts = translated_segments
            print(f"[Pipeline] Translation completed")
        except Exception as trans_err:
            print(f"[Pipeline] Translation failed (non-fatal): {trans_err}")
            # Continue with untranslated segments

        transcript = Transcript(
            video_id=video_id,
            language="en",
            segments=segment_dicts,
            full_text=transcriber.segments_to_full_text(segments),
        )
        db.add(transcript)
        video.status = "ready"
        video.completed_at = datetime.utcnow()
        db.commit()

        try:
            ct = video.content_type or "video"
            # Use translated Chinese text for title generation (more accurate)
            chinese_parts = [seg.get("translation", "") for seg in segment_dicts if seg.get("translation")]
            if chinese_parts:
                chinese_text = " ".join(chinese_parts)
                print(f"[Pipeline] Generating title from Chinese text ({len(chinese_text)} chars)...")
                analysis = await loop.run_in_executor(None, generate_title_from_chinese, chinese_text, ct)
            else:
                # Fallback to English if no translations available
                full_text = transcriber.segments_to_full_text(segments)
                print(f"[Pipeline] No translations, generating title from English text...")
                analysis = await loop.run_in_executor(None, generate_title_and_appreciation, full_text, ct)
            if analysis.get("title"):
                video.title = analysis["title"]
            appreciation = {k: analysis[k] for k in ("theme", "keyPoints", "goldenQuotes") if k in analysis}
            if appreciation.get("theme"):
                transcript.appreciation = appreciation
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(transcript, "appreciation")
            db.commit()
        except Exception as ai_err:
            print(f"[Pipeline] Auto-analysis failed (non-fatal): {ai_err}")

        await manager.broadcast({
            "type": "transcribe_completed",
            "data": {"video_id": video_id, "title": video.title, "segment_count": len(segments)},
        })

    except Exception as e:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = "failed"
            video.error_message = _localize_error(str(e))
            db.commit()
        await manager.broadcast({"type": "process_error", "data": {"video_id": video_id, "error": str(e)}})
    finally:
        db.close()


@router.post("/backfill-thumbnails", dependencies=[Depends(require_admin)])
async def backfill_thumbnails(db: Session = Depends(get_db)):
    videos = db.query(Video).filter(Video.filename.isnot(None), Video.status == "ready").all()
    generated = 0
    for video in videos:
        if video.thumbnail and (THUMBS_DIR / video.thumbnail).exists():
            continue
        video_path = VIDEOS_DIR / video.filename
        if not video_path.exists():
            continue
        thumb = generate_thumbnail(video_path, video.id)
        if thumb:
            video.thumbnail = thumb
            generated += 1
    db.commit()
    return {"success": True, "generated": generated, "total": len(videos)}


@router.get("")
async def list_videos(db: Session = Depends(get_db), user: dict | None = Depends(optional_auth)):
    if not user:
        return []
    user_id = _get_user_id(user)

    # Migration: if user has no videos yet, adopt all orphan videos (no UserVideo link)
    user_count = db.query(UserVideo).filter(UserVideo.user_id == user_id).count()
    if user_count == 0:
        from sqlalchemy import exists
        orphan_videos = (
            db.query(Video)
            .filter(~exists().where(UserVideo.video_id == Video.id))
            .all()
        )
        if orphan_videos:
            for v in orphan_videos:
                db.add(UserVideo(user_id=user_id, video_id=v.id))
            db.commit()

    user_vids = (
        db.query(Video)
        .join(UserVideo, UserVideo.video_id == Video.id)
        .filter(UserVideo.user_id == user_id)
        .order_by(Video.created_at.desc())
        .all()
    )
    return [
        {
            "id": v.id, "url": v.url, "title": v.title, "source": v.source,
            "content_type": v.content_type or "video",
            "duration": v.duration, "thumbnail": v.thumbnail, "channel": v.channel,
            "status": v.status, "error_message": v.error_message,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in user_vids
    ]


@router.post("/retry-all-failed")
async def retry_all_failed(db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    is_admin = _is_admin(user)

    # Admin/bot sees all failed videos; regular users only see their own
    if is_admin:
        failed = db.query(Video).filter(Video.status == "failed").all()
    else:
        failed = (
            db.query(Video)
            .join(UserVideo, UserVideo.video_id == Video.id)
            .filter(UserVideo.user_id == user_id, Video.status == "failed")
            .all()
        )
    if not failed:
        return {"retried": 0, "video_ids": []}
    video_ids = []
    for video in failed:
        video.status = "downloading"
        video.error_message = None
        video_ids.append(video.id)
    db.commit()
    for video in failed:
        asyncio.create_task(_process_pipeline(video.id, video.url, user_id))
    return {"retried": len(video_ids), "video_ids": video_ids}


@router.post("/batch-delete")
async def batch_delete_videos(req: BatchDeleteRequest, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    deleted_count = 0
    for vid in req.video_ids:
        uv = db.query(UserVideo).filter(UserVideo.user_id == user_id, UserVideo.video_id == vid).first()
        if uv:
            db.delete(uv)
            deleted_count += 1
            other_refs = db.query(UserVideo).filter(UserVideo.video_id == vid, UserVideo.user_id != user_id).count()
            if other_refs == 0:
                video = db.query(Video).filter(Video.id == vid).first()
                if video:
                    if video.filename:
                        video_path = VIDEOS_DIR / video.filename
                        if video_path.exists():
                            video_path.unlink()
                    db.delete(video)
    db.commit()
    return {"success": True, "deleted_count": deleted_count}


@router.patch("/{video_id}")
async def rename_video(video_id: str, req: RenameRequest, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    uv = db.query(UserVideo).filter(UserVideo.user_id == user_id, UserVideo.video_id == video_id).first()
    if not uv:
        raise HTTPException(status_code=404, detail="Video not found")
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    video.title = req.title
    db.commit()
    return {"success": True, "id": video.id, "title": video.title}


@router.get("/{video_id}")
async def get_video(video_id: str, db: Session = Depends(get_db)):
    """Get a single video with transcript (public — content is shared)."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    transcript_data = None
    if video.transcript:
        transcript_data = {
            "language": video.transcript.language,
            "segments": video.transcript.segments,
            "full_text": video.transcript.full_text,
            "appreciation": video.transcript.appreciation,
        }

    return {
        "id": video.id, "url": video.url, "title": video.title, "source": video.source,
        "content_type": video.content_type or "video",
        "duration": video.duration, "thumbnail": video.thumbnail, "channel": video.channel,
        "filename": video.filename, "status": video.status, "error_message": video.error_message,
        "created_at": video.created_at.isoformat() if video.created_at else None,
        "transcript": transcript_data,
    }


@router.delete("/{video_id}")
async def delete_video(video_id: str, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    uv = db.query(UserVideo).filter(UserVideo.user_id == user_id, UserVideo.video_id == video_id).first()
    if not uv:
        raise HTTPException(status_code=404, detail="Video not found")
    db.delete(uv)
    other_refs = db.query(UserVideo).filter(UserVideo.video_id == video_id, UserVideo.user_id != user_id).count()
    if other_refs == 0:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            if video.filename:
                video_path = VIDEOS_DIR / video.filename
                if video_path.exists():
                    video_path.unlink()
            db.delete(video)
    db.commit()
    return {"success": True}


@router.post("/{video_id}/retry")
async def retry_video(video_id: str, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    is_admin = _is_admin(user)

    # Admin/bot can retry any video; regular users need ownership
    if not is_admin:
        uv = db.query(UserVideo).filter(UserVideo.user_id == user_id, UserVideo.video_id == video_id).first()
        if not uv:
            raise HTTPException(status_code=404, detail="Video not found")

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status not in ("failed", "transcribing"):
        raise HTTPException(status_code=400, detail="Only failed videos can be retried")
    video.status = "downloading"
    video.error_message = None
    db.commit()
    asyncio.create_task(_process_pipeline(video.id, video.url, user_id))
    return {"success": True, "video_id": video.id, "status": "downloading"}


# --- Content endpoints (public, shared) ---

@router.post("/{video_id}/translate")
async def translate_video(video_id: str, db: Session = Depends(get_db), user: dict | None = Depends(optional_auth)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    transcript = video.transcript
    if not transcript or not transcript.segments:
        raise HTTPException(status_code=400, detail="No transcript available")
    if any(seg.get("translation") for seg in transcript.segments):
        return {"success": True, "message": "Already translated", "segments": transcript.segments}
    # Deduct credits for LLM translation
    if user and not _is_admin(user):
        user_id = _get_user_id(user)
        quota = _get_or_create_quota(db, user_id)
        limit = _get_credit_limit(db, user)
        if not _check_quota(quota, limit, COST_TRANSLATE):
            raise HTTPException(status_code=429, detail="本月點數已用完")
        quota.credits_used += COST_TRANSLATE
        db.commit()
    await manager.broadcast({"type": "translate_started", "data": {"video_id": video_id}})
    try:
        loop = asyncio.get_running_loop()
        translated = await loop.run_in_executor(None, translate_segments, transcript.segments)
        transcript.segments = translated
        db.commit()
        await manager.broadcast({"type": "translate_completed", "data": {"video_id": video_id}})
        return {"success": True, "segments": translated}
    except Exception as e:
        await manager.broadcast({"type": "translate_error", "data": {"video_id": video_id, "error": str(e)}})
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{video_id}/analyze-vocabulary")
async def analyze_video_vocabulary(video_id: str, db: Session = Depends(get_db), user: dict | None = Depends(optional_auth)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    transcript = video.transcript
    if not transcript or not transcript.segments:
        raise HTTPException(status_code=400, detail="No transcript available")
    if any(seg.get("vocabulary") for seg in transcript.segments):
        return {"success": True, "message": "Already analyzed", "segments": transcript.segments}
    # Deduct credits for LLM vocabulary analysis
    if user and not _is_admin(user):
        user_id = _get_user_id(user)
        quota = _get_or_create_quota(db, user_id)
        limit = _get_credit_limit(db, user)
        if not _check_quota(quota, limit, COST_VOCABULARY):
            raise HTTPException(status_code=429, detail="本月點數已用完")
        quota.credits_used += COST_VOCABULARY
        db.commit()
    try:
        loop = asyncio.get_running_loop()
        analyzed = await loop.run_in_executor(None, analyze_segments, transcript.segments)
        transcript.segments = analyzed
        db.commit()
        return {"success": True, "segments": analyzed}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{video_id}/appreciate")
async def appreciate_video(video_id: str, db: Session = Depends(get_db), user: dict | None = Depends(optional_auth)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    transcript = video.transcript
    if not transcript or not transcript.full_text:
        raise HTTPException(status_code=400, detail="No transcript available")
    if transcript.appreciation and transcript.appreciation.get("theme"):
        return {"success": True, "appreciation": transcript.appreciation}
    # Deduct credits for LLM appreciation
    if user and not _is_admin(user):
        user_id = _get_user_id(user)
        quota = _get_or_create_quota(db, user_id)
        limit = _get_credit_limit(db, user)
        if not _check_quota(quota, limit, COST_APPRECIATE):
            raise HTTPException(status_code=429, detail="本月點數已用完")
        quota.credits_used += COST_APPRECIATE
        db.commit()
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, generate_appreciation, transcript.full_text)
        transcript.appreciation = result
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(transcript, "appreciation")
        db.commit()
        return {"success": True, "appreciation": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
