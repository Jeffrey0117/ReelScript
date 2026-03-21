"""
Quota API routes — check usage, get current quota.
Checks PayGate subscription (via local cache) for paid plans.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models import get_db, UserQuota, Subscription
from middleware.auth import optional_auth

router = APIRouter(prefix="/api/quota", tags=["quota"])

FREE_MONTHLY_LIMIT = 5
PRO_MONTHLY_LIMIT = 80


def _get_user_id(user: dict) -> str:
    return user.get("sub", "")


@router.get("")
async def get_quota(db: Session = Depends(get_db), user: dict | None = Depends(optional_auth)):
    if not user:
        return {"plan": "free", "period": "", "videos_used": 0, "bonus_videos": 0, "limit": 0, "remaining": 0}

    user_id = _get_user_id(user)
    email = user.get("email", "")
    period = datetime.utcnow().strftime("%Y-%m")

    # Check paid subscription from PayGate webhook cache
    sub = None
    if email:
        sub = db.query(Subscription).filter(
            Subscription.email == email,
            Subscription.status == "active",
        ).first()

    plan = sub.plan if sub else "free"

    quota = db.query(UserQuota).filter(
        UserQuota.user_id == user_id, UserQuota.period == period
    ).first()

    videos_used = quota.videos_used if quota else 0
    bonus_videos = quota.bonus_videos if quota else 0

    if plan == "unlimited":
        limit = -1
        remaining = -1
    elif plan == "pro":
        limit = PRO_MONTHLY_LIMIT + bonus_videos
        remaining = max(0, limit - videos_used)
    else:
        limit = FREE_MONTHLY_LIMIT + bonus_videos
        remaining = max(0, limit - videos_used)

    return {
        "plan": plan,
        "period": period,
        "videos_used": videos_used,
        "bonus_videos": bonus_videos,
        "limit": limit,
        "remaining": remaining,
    }
