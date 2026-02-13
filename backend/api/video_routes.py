"""
Video API routes — download, transcribe, list, get, delete.
"""

import asyncio
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import get_db, Video, Transcript
from services.downloader import download_video, get_video_info, VIDEOS_DIR
from services.transcriber import transcriber
from services.translator import translate_segments
from services.vocabulary import analyze_segments
from services.appreciation import generate_appreciation
from services.titler import generate_title_and_appreciation
from api.websocket import manager

router = APIRouter(prefix="/api/videos", tags=["videos"])


class ProcessRequest(BaseModel):
    url: str


class RenameRequest(BaseModel):
    title: str


class BatchDeleteRequest(BaseModel):
    video_ids: list[str]


URL_PATTERNS = [
    re.compile(r"https?://(www\.)?(youtube\.com|youtu\.be)/"),
    re.compile(r"https?://(www\.)?instagram\.com/"),
    re.compile(r"https?://(www\.)?(bilibili\.com|b23\.tv)/"),
    re.compile(r"https?://(www\.)?tiktok\.com/"),
]


def _is_valid_url(url: str) -> bool:
    return any(p.match(url) for p in URL_PATTERNS)


@router.post("/process")
async def process_video(req: ProcessRequest, db: Session = Depends(get_db)):
    """Download a video and transcribe it. Returns immediately, processes in background."""

    if not _is_valid_url(req.url):
        raise HTTPException(status_code=400, detail="Unsupported URL. Use YouTube, Instagram, Bilibili, or TikTok links.")

    # Dedup: check if this URL is already processed
    existing = db.query(Video).filter(Video.url == req.url).first()
    if existing:
        return {
            "success": True,
            "video_id": existing.id,
            "title": existing.title,
            "status": existing.status,
            "duplicate": True,
        }

    # Fetch info first
    info = await get_video_info(req.url)

    # Create DB record
    video = Video(
        url=req.url,
        title=info.get("title"),
        source=info.get("source", "unknown"),
        duration=info.get("duration"),
        thumbnail=info.get("thumbnail"),
        channel=info.get("channel"),
        status="downloading",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    video_id = video.id

    # Run download + transcribe in background
    asyncio.create_task(_process_pipeline(video_id, req.url))

    return {
        "success": True,
        "video_id": video_id,
        "title": video.title,
        "status": "downloading",
    }


async def _process_pipeline(video_id: str, url: str):
    """Background pipeline: download → transcribe → save transcript."""
    from models.database import SessionLocal

    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return

        # Step 1: Download
        result = await download_video(url, video_id)

        if not result.get("success"):
            video.status = "failed"
            video.error_message = result.get("error", "Download failed")
            db.commit()
            return

        video.filename = result.get("filename")
        video.title = result.get("title") or video.title
        video.duration = result.get("duration") or video.duration
        video.thumbnail = result.get("thumbnail") or video.thumbnail
        video.channel = result.get("channel") or video.channel
        video.source = result.get("source") or video.source
        video.status = "transcribing"
        db.commit()

        await manager.broadcast({
            "type": "transcribe_started",
            "data": {"video_id": video_id},
        })

        # Step 2: Transcribe (CPU-bound, run in thread)
        video_path = str(VIDEOS_DIR / video.filename)

        loop = asyncio.get_running_loop()
        segments = await loop.run_in_executor(
            None, transcriber.transcribe, video_path
        )

        # Step 3: Save transcript
        transcript = Transcript(
            video_id=video_id,
            language="en",
            segments=transcriber.segments_to_dict(segments),
            full_text=transcriber.segments_to_full_text(segments),
        )
        db.add(transcript)

        video.status = "ready"
        video.completed_at = datetime.utcnow()
        db.commit()

        # Step 4: Auto-generate title + appreciation in one AI call
        try:
            full_text = transcriber.segments_to_full_text(segments)
            analysis = await loop.run_in_executor(
                None, generate_title_and_appreciation, full_text
            )
            if analysis.get("title"):
                video.title = analysis["title"]
            appreciation = {
                k: analysis[k] for k in ("theme", "keyPoints", "goldenQuotes")
                if k in analysis
            }
            if appreciation.get("theme"):
                transcript.appreciation = appreciation
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(transcript, "appreciation")
            db.commit()
        except Exception as ai_err:
            print(f"[Pipeline] Auto-analysis failed (non-fatal): {ai_err}")

        await manager.broadcast({
            "type": "transcribe_completed",
            "data": {
                "video_id": video_id,
                "title": video.title,
                "segment_count": len(segments),
            },
        })

    except Exception as e:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = "failed"
            video.error_message = str(e)
            db.commit()

        await manager.broadcast({
            "type": "process_error",
            "data": {"video_id": video_id, "error": str(e)},
        })
    finally:
        db.close()


@router.get("")
async def list_videos(db: Session = Depends(get_db)):
    """List all videos, newest first."""
    videos = db.query(Video).order_by(Video.created_at.desc()).all()
    return [
        {
            "id": v.id,
            "url": v.url,
            "title": v.title,
            "source": v.source,
            "duration": v.duration,
            "thumbnail": v.thumbnail,
            "channel": v.channel,
            "status": v.status,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in videos
    ]


@router.post("/batch-delete")
async def batch_delete_videos(req: BatchDeleteRequest, db: Session = Depends(get_db)):
    """Delete multiple videos and their files."""
    deleted_count = 0
    for vid in req.video_ids:
        video = db.query(Video).filter(Video.id == vid).first()
        if video:
            if video.filename:
                video_path = VIDEOS_DIR / video.filename
                if video_path.exists():
                    video_path.unlink()
            db.delete(video)
            deleted_count += 1
    db.commit()
    return {"success": True, "deleted_count": deleted_count}


@router.patch("/{video_id}")
async def rename_video(video_id: str, req: RenameRequest, db: Session = Depends(get_db)):
    """Update a video's title."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    video.title = req.title
    db.commit()
    return {"success": True, "id": video.id, "title": video.title}


@router.get("/{video_id}")
async def get_video(video_id: str, db: Session = Depends(get_db)):
    """Get a single video with its transcript."""
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
        "id": video.id,
        "url": video.url,
        "title": video.title,
        "source": video.source,
        "duration": video.duration,
        "thumbnail": video.thumbnail,
        "channel": video.channel,
        "filename": video.filename,
        "status": video.status,
        "created_at": video.created_at.isoformat() if video.created_at else None,
        "transcript": transcript_data,
    }


@router.delete("/{video_id}")
async def delete_video(video_id: str, db: Session = Depends(get_db)):
    """Delete a video and its transcript."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Delete video file
    if video.filename:
        video_path = VIDEOS_DIR / video.filename
        if video_path.exists():
            video_path.unlink()

    db.delete(video)
    db.commit()
    return {"success": True}


@router.post("/{video_id}/translate")
async def translate_video(video_id: str, db: Session = Depends(get_db)):
    """Translate transcript segments to Traditional Chinese."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    transcript = video.transcript
    if not transcript or not transcript.segments:
        raise HTTPException(status_code=400, detail="No transcript available")

    # Check if already translated
    has_translations = any(
        seg.get("translation") for seg in transcript.segments
    )
    if has_translations:
        return {"success": True, "message": "Already translated", "segments": transcript.segments}

    await manager.broadcast({
        "type": "translate_started",
        "data": {"video_id": video_id},
    })

    try:
        loop = asyncio.get_running_loop()
        translated = await loop.run_in_executor(
            None, translate_segments, transcript.segments
        )

        transcript.segments = translated
        db.commit()

        await manager.broadcast({
            "type": "translate_completed",
            "data": {"video_id": video_id},
        })

        return {"success": True, "segments": translated}
    except Exception as e:
        await manager.broadcast({
            "type": "translate_error",
            "data": {"video_id": video_id, "error": str(e)},
        })
        print(f"[API Error] {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{video_id}/analyze-vocabulary")
async def analyze_video_vocabulary(video_id: str, db: Session = Depends(get_db)):
    """Analyze transcript segments for difficult vocabulary words."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    transcript = video.transcript
    if not transcript or not transcript.segments:
        raise HTTPException(status_code=400, detail="No transcript available")

    # Check if already analyzed
    has_vocab = any(
        seg.get("vocabulary") for seg in transcript.segments
    )
    if has_vocab:
        return {"success": True, "message": "Already analyzed", "segments": transcript.segments}

    try:
        loop = asyncio.get_running_loop()
        analyzed = await loop.run_in_executor(
            None, analyze_segments, transcript.segments
        )

        transcript.segments = analyzed
        db.commit()

        return {"success": True, "segments": analyzed}
    except Exception as e:
        print(f"[API Error] {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{video_id}/appreciate")
async def appreciate_video(video_id: str, db: Session = Depends(get_db)):
    """Generate content appreciation: theme, key points, golden quotes."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    transcript = video.transcript
    if not transcript or not transcript.full_text:
        raise HTTPException(status_code=400, detail="No transcript available")

    # Check if already analyzed (stored in appreciation field)
    if transcript.appreciation and transcript.appreciation.get("theme"):
        return {"success": True, "appreciation": transcript.appreciation}

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, generate_appreciation, transcript.full_text
        )

        transcript.appreciation = result
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(transcript, "appreciation")
        db.commit()

        return {"success": True, "appreciation": result}
    except Exception as e:
        print(f"[API Error] {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
