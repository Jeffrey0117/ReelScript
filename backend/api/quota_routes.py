"""
Quota API routes — check usage, get current quota.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models import get_db, UserQuota
from middleware.auth import optional_auth

router = APIRouter(prefix="/api/quota", tags=["quota"])

FREE_MONTHLY_LIMIT = 5


def _get_user_id(user: dict) -> str:
    return user.get("sub", "")


@router.get("")
async def get_quota(db: Session = Depends(get_db), user: dict | None = Depends(optional_auth)):
    if not user:
        return {"plan": "free", "period": "", "videos_used": 0, "bonus_videos": 0, "limit": 0, "remaining": 0}
    user_id = _get_user_id(user)
    period = datetime.utcnow().strftime("%Y-%m")
    quota = db.query(UserQuota).filter(
        UserQuota.user_id == user_id, UserQuota.period == period
    ).first()

    if not quota:
        return {
            "plan": "free",
            "period": period,
            "videos_used": 0,
            "bonus_videos": 0,
            "limit": FREE_MONTHLY_LIMIT,
            "remaining": FREE_MONTHLY_LIMIT,
        }

    limit = FREE_MONTHLY_LIMIT + quota.bonus_videos if quota.plan == "free" else -1
    remaining = max(0, limit - quota.videos_used) if quota.plan == "free" else -1

    return {
        "plan": quota.plan,
        "period": period,
        "videos_used": quota.videos_used,
        "bonus_videos": quota.bonus_videos,
        "limit": limit,
        "remaining": remaining,
    }
