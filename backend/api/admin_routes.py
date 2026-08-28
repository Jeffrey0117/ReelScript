"""
Admin API routes — stats, video management, categories, featured, user management.
Auth: adman JWT with admin role, or legacy X-Admin-Key fallback.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, case, literal_column

from models import get_db, Video, Transcript, Collection, User, UserVideo, UserQuota, Subscription, Invite
from middleware.auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])

FREE_MONTHLY_LIMIT = 30
PRO_MONTHLY_LIMIT = 200


class UpdateVideoAdmin(BaseModel):
    category: str | None = None
    is_featured: bool | None = None
    is_public: bool | None = None
    title: str | None = None


@router.get("/stats", dependencies=[Depends(require_admin)])
async def admin_stats(db: Session = Depends(get_db)):
    """Dashboard stats — videos + user overview."""
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

    # User stats
    total_users = db.query(func.count(User.id)).scalar()
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users_30d = (
        db.query(func.count(User.id))
        .filter(User.last_seen_at >= thirty_days_ago)
        .scalar()
    )

    # Plan breakdown: join User → Subscription by email
    plan_breakdown = {"free": 0, "pro": 0, "unlimited": 0}
    plan_rows = (
        db.query(
            func.coalesce(Subscription.plan, "free").label("plan"),
            func.count(User.id),
        )
        .outerjoin(Subscription, (User.email == Subscription.email) & (Subscription.status == "active"))
        .group_by("plan")
        .all()
    )
    for plan_name, count in plan_rows:
        if plan_name in plan_breakdown:
            plan_breakdown[plan_name] = count

    return {
        "total_videos": total_videos,
        "ready_videos": ready_videos,
        "failed_videos": failed_videos,
        "featured_count": featured_count,
        "total_collections": total_collections,
        "sources": sources,
        "categories": categories,
        "total_users": total_users,
        "active_users_30d": active_users_30d,
        "plan_breakdown": plan_breakdown,
    }


@router.get("/videos", dependencies=[Depends(require_admin)])
async def admin_list_videos(
    status: str | None = None,
    category: str | None = None,
    featured: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    """List all videos with filters + uploader info."""
    query = db.query(Video).order_by(Video.created_at.desc())

    if status:
        query = query.filter(Video.status == status)
    if category:
        query = query.filter(Video.category == category)
    if featured is not None:
        query = query.filter(Video.is_featured == featured)
    if search:
        search = search.strip()[:100]
        query = query.filter(
            Video.title.ilike(f"%{search}%") | Video.channel.ilike(f"%{search}%")
        )

    videos = query.all()

    # Batch-load uploader info: video_id → User
    video_ids = [v.id for v in videos]
    uploader_map: dict[str, dict] = {}
    if video_ids:
        uv_rows = (
            db.query(UserVideo.video_id, User.id, User.email, User.name)
            .join(User, UserVideo.user_id == User.id)
            .filter(UserVideo.video_id.in_(video_ids))
            .all()
        )
        for vid, uid, uemail, uname in uv_rows:
            uploader_map[vid] = {"id": uid, "email": uemail, "name": uname}

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
            "is_public": v.is_public or False,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "uploader": uploader_map.get(v.id),
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
    if req.is_public is not None:
        video.is_public = req.is_public
    if req.title is not None:
        video.title = req.title

    db.commit()
    return {
        "success": True,
        "id": video.id,
        "category": video.category,
        "is_featured": video.is_featured,
        "is_public": video.is_public,
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


# ── User Management ──────────────────────────────────────────────


@router.get("/users", dependencies=[Depends(require_admin)])
async def admin_list_users(
    search: str | None = None,
    plan: str | None = None,
    sort: str | None = None,
    db: Session = Depends(get_db),
):
    """List all cached users with video count, credits, plan."""
    period = datetime.utcnow().strftime("%Y-%m")

    # Subquery: video count per user
    video_count_sq = (
        db.query(UserVideo.user_id, func.count(UserVideo.video_id).label("video_count"))
        .group_by(UserVideo.user_id)
        .subquery()
    )

    # Subquery: credits used this month
    credits_sq = (
        db.query(
            UserQuota.user_id,
            UserQuota.credits_used,
            UserQuota.bonus_credits,
        )
        .filter(UserQuota.period == period)
        .subquery()
    )

    query = (
        db.query(
            User,
            func.coalesce(video_count_sq.c.video_count, 0).label("video_count"),
            func.coalesce(credits_sq.c.credits_used, 0).label("credits_used"),
            func.coalesce(credits_sq.c.bonus_credits, 0).label("bonus_credits"),
            Subscription.plan.label("sub_plan"),
            Subscription.credits_per_month,
        )
        .outerjoin(video_count_sq, User.id == video_count_sq.c.user_id)
        .outerjoin(credits_sq, User.id == credits_sq.c.user_id)
        .outerjoin(Subscription, (User.email == Subscription.email) & (Subscription.status == "active"))
    )

    if search:
        search = search.strip()[:100]
        query = query.filter(
            User.email.ilike(f"%{search}%") | User.name.ilike(f"%{search}%")
        )

    if plan:
        if plan == "free":
            query = query.filter(
                (Subscription.plan == None) | (Subscription.plan == "free")
            )
        else:
            query = query.filter(Subscription.plan == plan)

    # Sorting
    if sort == "videos":
        query = query.order_by(func.coalesce(video_count_sq.c.video_count, 0).desc())
    elif sort == "credits":
        query = query.order_by(func.coalesce(credits_sq.c.credits_used, 0).desc())
    else:
        query = query.order_by(User.last_seen_at.desc())

    rows = query.all()

    result = []
    for user, vc, cu, bc, sp, cpm in rows:
        user_plan = sp or "free"
        if user_plan == "unlimited":
            credits_limit = -1
        elif user_plan == "pro":
            credits_limit = PRO_MONTHLY_LIMIT + bc
        else:
            credits_limit = FREE_MONTHLY_LIMIT + bc

        result.append({
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "avatar": user.avatar,
            "plan": user_plan,
            "video_count": vc,
            "credits_used": cu,
            "credits_limit": credits_limit,
            "first_seen_at": user.first_seen_at.isoformat() if user.first_seen_at else None,
            "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
        })

    return result


@router.get("/users/{user_id}", dependencies=[Depends(require_admin)])
async def admin_get_user(user_id: str, db: Session = Depends(get_db)):
    """User detail: videos, quota history, invite info."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Plan
    sub = None
    if user.email:
        sub = db.query(Subscription).filter(
            Subscription.email == user.email,
            Subscription.status == "active",
        ).first()
    user_plan = sub.plan if sub else "free"

    # Videos
    uv_rows = (
        db.query(UserVideo, Video)
        .join(Video, UserVideo.video_id == Video.id)
        .filter(UserVideo.user_id == user_id)
        .order_by(UserVideo.added_at.desc())
        .all()
    )
    videos = [
        {
            "id": v.id,
            "title": v.title,
            "source": v.source,
            "status": v.status,
            "thumbnail": v.thumbnail,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for _, v in uv_rows
    ]

    # Quota history (all periods)
    quotas = (
        db.query(UserQuota)
        .filter(UserQuota.user_id == user_id)
        .order_by(UserQuota.period.desc())
        .all()
    )
    quota_history = [
        {
            "period": q.period,
            "credits_used": q.credits_used,
            "bonus_credits": q.bonus_credits,
        }
        for q in quotas
    ]

    # Invite info
    invite_row = db.query(Invite).filter(Invite.inviter_id == user_id).first()
    redeemed_count = 0
    if invite_row:
        redeemed_count = (
            db.query(func.count(Invite.id))
            .filter(Invite.inviter_id == user_id, Invite.used_by != None)
            .scalar()
        )
    invite = (
        {"code": invite_row.code, "redeemed_count": redeemed_count}
        if invite_row
        else None
    )

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "avatar": user.avatar,
            "first_seen_at": user.first_seen_at.isoformat() if user.first_seen_at else None,
            "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
        },
        "plan": user_plan,
        "videos": videos,
        "quota_history": quota_history,
        "invite": invite,
    }
