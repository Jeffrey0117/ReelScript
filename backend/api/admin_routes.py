"""
Admin API routes — stats, video management, categories, featured.
Auth: adman JWT with admin role, or legacy X-Admin-Key fallback.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import get_db, Video, Transcript, Collection
from middleware.auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UpdateVideoAdmin(BaseModel):
    category: str | None = None
    is_featured: bool | None = None
    title: str | None = None


@router.get("/stats", dependencies=[Depends(require_admin)])
async def admin_stats(db: Session = Depends(get_db)):
    """Dashboard stats."""
    total_videos = db.query(func.count(Video.id)).scalar()
    ready_videos = db.query(func.count(Video.id)).filter(Video.status == "ready").scalar()
    failed_videos = db.query(func.count(Video.id)).filter(Video.status == "failed").scalar()
    featured_count = db.query(func.count(Video.id)).filter(Video.is_featured == True).scalar()
    total_collections = db.query(func.count(Collection.id)).scalar()

    # Source breakdown
    source_counts = (
        db.query(Video.source, func.count(Video.id))
        .group_by(Video.source)
        .all()
    )
    sources = {source: count for source, count in source_counts}

    # Category breakdown
    category_counts = (
        db.query(Video.category, func.count(Video.id))
        .filter(Video.category != None)
        .group_by(Video.category)
        .all()
    )
    categories = {cat: count for cat, count in category_counts}

    return {
        "total_videos": total_videos,
        "ready_videos": ready_videos,
        "failed_videos": failed_videos,
        "featured_count": featured_count,
        "total_collections": total_collections,
        "sources": sources,
        "categories": categories,
    }


@router.get("/videos", dependencies=[Depends(require_admin)])
async def admin_list_videos(
    status: str | None = None,
    category: str | None = None,
    featured: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    """List all videos with filters."""
    query = db.query(Video).order_by(Video.created_at.desc())

    if status:
        query = query.filter(Video.status == status)
    if category:
        query = query.filter(Video.category == category)
    if featured is not None:
        query = query.filter(Video.is_featured == featured)
    if search:
        query = query.filter(
            Video.title.ilike(f"%{search}%") | Video.channel.ilike(f"%{search}%")
        )

    videos = query.all()
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
            "category": v.category,
            "is_featured": v.is_featured or False,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in videos
    ]


@router.patch("/videos/{video_id}", dependencies=[Depends(require_admin)])
async def admin_update_video(
    video_id: str,
    req: UpdateVideoAdmin,
    db: Session = Depends(get_db),
):
    """Update video metadata (category, featured, title)."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if req.category is not None:
        video.category = req.category
    if req.is_featured is not None:
        video.is_featured = req.is_featured
    if req.title is not None:
        video.title = req.title

    db.commit()
    return {
        "success": True,
        "id": video.id,
        "category": video.category,
        "is_featured": video.is_featured,
        "title": video.title,
    }


@router.delete("/videos/{video_id}", dependencies=[Depends(require_admin)])
async def admin_delete_video(video_id: str, db: Session = Depends(get_db)):
    """Hard delete a video (admin only)."""
    from services.downloader import VIDEOS_DIR

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if video.filename:
        video_path = VIDEOS_DIR / video.filename
        if video_path.exists():
            video_path.unlink()

    db.delete(video)
    db.commit()
    return {"success": True}
