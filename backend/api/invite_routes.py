"""
Invite API routes — generate codes, redeem invites.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import get_db, Invite, UserQuota
from middleware.auth import require_auth

router = APIRouter(prefix="/api/invite", tags=["invite"])

INVITE_BONUS = 2  # bonus videos per successful invite (both parties)


class RedeemRequest(BaseModel):
    code: str


def _get_user_id(user: dict) -> str:
    return user.get("sub", "")


def _add_bonus(db: Session, user_id: str, bonus: int):
    period = datetime.utcnow().strftime("%Y-%m")
    quota = db.query(UserQuota).filter(
        UserQuota.user_id == user_id, UserQuota.period == period
    ).first()
    if not quota:
        quota = UserQuota(user_id=user_id, period=period, bonus_videos=bonus)
        db.add(quota)
    else:
        quota.bonus_videos += bonus


@router.get("/my-code")
async def get_my_code(db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    invite = db.query(Invite).filter(Invite.inviter_id == user_id, Invite.used_by.is_(None)).first()
    if not invite:
        invite = Invite(inviter_id=user_id)
        db.add(invite)
        db.commit()
        db.refresh(invite)
    return {"code": invite.code}


@router.post("/redeem")
async def redeem_invite(req: RedeemRequest, db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    user_id = _get_user_id(user)
    code = req.code.strip().upper()

    invite = db.query(Invite).filter(Invite.code == code).first()
    if not invite:
        raise HTTPException(status_code=404, detail="邀請碼不存在")
    if invite.used_by:
        raise HTTPException(status_code=400, detail="邀請碼已被使用")
    if invite.inviter_id == user_id:
        raise HTTPException(status_code=400, detail="不能使用自己的邀請碼")

    # Redeem: mark as used + bonus for both parties
    invite.used_by = user_id
    invite.used_at = datetime.utcnow()

    _add_bonus(db, invite.inviter_id, INVITE_BONUS)
    _add_bonus(db, user_id, INVITE_BONUS)

    # Generate a new unused invite code for the inviter
    new_invite = Invite(inviter_id=invite.inviter_id)
    db.add(new_invite)

    db.commit()
    return {"success": True, "bonus": INVITE_BONUS}
