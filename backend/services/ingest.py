"""
Admin batch-ingest worker — turns a pasted URL list into finished public
teaching material overnight.

One queue, one worker, strictly serial: each item runs the full pipeline
(download → whisper → translate → appreciate) via video_routes'
_process_pipeline, then vocabulary analysis, then is_public/category/pack
assignment. Queue rows live in ingest_items so a restart resumes cleanly.
"""

import asyncio
import uuid
from datetime import datetime

from sqlalchemy.orm.attributes import flag_modified

from models import Video, Collection, CollectionItem, IngestItem
from models.database import SessionLocal
from services.vocabulary import analyze_segments

_worker_task: asyncio.Task | None = None


def new_batch_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d-%H%M") + "-" + uuid.uuid4().hex[:4]


def ensure_worker() -> None:
    """Start the single background worker if it isn't running."""
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_worker_loop())


def resume_on_startup() -> bool:
    """Reset items stranded in 'processing' by a restart. Returns True if
    there is pending work (caller should ensure_worker once the loop runs)."""
    db = SessionLocal()
    try:
        stuck = db.query(IngestItem).filter(IngestItem.status == "processing").all()
        for item in stuck:
            item.status = "pending"
        db.commit()
        return db.query(IngestItem).filter(IngestItem.status == "pending").count() > 0
    finally:
        db.close()


async def _worker_loop() -> None:
    while True:
        db = SessionLocal()
        try:
            item = (
                db.query(IngestItem)
                .filter(IngestItem.status == "pending")
                .order_by(IngestItem.created_at.asc())
                .first()
            )
            if not item:
                return  # queue drained — worker exits, restarted on next enqueue
            item.status = "processing"
            item.error = None
            db.commit()
            item_id = item.id
        finally:
            db.close()

        try:
            await _process_item(item_id)
        except Exception as e:  # worker must never die on one bad URL
            db = SessionLocal()
            try:
                item = db.query(IngestItem).filter(IngestItem.id == item_id).first()
                if item:
                    item.status = "failed"
                    item.error = str(e)[:500]
                    db.commit()
            finally:
                db.close()


async def _process_item(item_id: str) -> None:
    # Imported here to avoid a module-level cycle (video_routes imports services.*)
    from api.video_routes import _process_pipeline
    from services.downloader import get_video_info

    db = SessionLocal()
    try:
        item = db.query(IngestItem).filter(IngestItem.id == item_id).first()
        if not item:
            return
        url = item.url.strip()

        video = db.query(Video).filter(Video.url == url).first()
        needs_pipeline = False
        if video is None:
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
                is_public=True,
            )
            db.add(video)
            db.commit()
            db.refresh(video)
            needs_pipeline = True
        elif video.status == "failed":
            video.status = "downloading"
            video.error_message = None
            db.commit()
            needs_pipeline = True

        video_id = video.id
        item.video_id = video_id
        db.commit()
    finally:
        db.close()

    if needs_pipeline:
        await _process_pipeline(video_id, url)

    # Post-pass: vocabulary + publish + categorize + pack assignment
    db = SessionLocal()
    try:
        item = db.query(IngestItem).filter(IngestItem.id == item_id).first()
        video = db.query(Video).filter(Video.id == video_id).first()
        if not item or not video:
            return

        if video.status != "ready":
            item.status = "failed"
            item.error = video.error_message or f"pipeline ended with status={video.status}"
            db.commit()
            return

        transcript = video.transcript
        if transcript and transcript.segments and not any(s.get("vocabulary") for s in transcript.segments):
            try:
                loop = asyncio.get_running_loop()
                analyzed = await loop.run_in_executor(None, analyze_segments, transcript.segments)
                transcript.segments = analyzed
                flag_modified(transcript, "segments")
            except Exception as e:
                print(f"[Ingest] vocabulary analysis failed (non-fatal) for {video_id}: {e}")

        video.is_public = True
        if item.category:
            video.category = item.category

        if item.collection_id:
            pack = db.query(Collection).filter(Collection.id == item.collection_id).first()
            if pack:
                exists = (
                    db.query(CollectionItem)
                    .filter(CollectionItem.collection_id == pack.id, CollectionItem.video_id == video_id)
                    .first()
                )
                if not exists:
                    db.add(CollectionItem(collection_id=pack.id, video_id=video_id))

        item.status = "done"
        db.commit()
    finally:
        db.close()
