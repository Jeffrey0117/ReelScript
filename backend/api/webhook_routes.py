"""
PayGate webhook handler — receives subscription lifecycle events.
Verifies HMAC-SHA256 signature, then upserts local Subscription cache.
"""

import hashlib
import hmac
import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from models import Subscription, get_db

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

PAYGATE_WEBHOOK_SECRET = os.environ.get(
    "PAYGATE_WEBHOOK_SECRET",
    "a109fab9c19dcfc97669cb0c787d9ece77b9c79f52aa8550f5d4b0ad3f7103a7",
)

FREE_CREDITS = 30


def _verify_signature(body: bytes, signature: str) -> bool:
    if not signature.startswith("sha256="):
        return False
    expected = signature[7:]
    calculated = hmac.new(
        PAYGATE_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(calculated, expected)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


@router.post("/paygate")
async def paygate_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature", "")

    if not _verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)
    event = payload.get("event", "")
    data = payload.get("data", {})

    sub_data = data.get("subscription", {})
    plan_data = data.get("plan", {})

    email = sub_data.get("email", "")
    if not email:
        return {"success": False, "error": "No email in payload"}

    if event == "subscription.activated":
        tier = sub_data.get("tier", plan_data.get("tier", "pro"))
        quotas = plan_data.get("quotas", {})
        if isinstance(quotas, str):
            quotas = json.loads(quotas)
        credits = quotas.get("credits_per_month", 80 if tier == "pro" else -1)
        expires_at = _parse_datetime(sub_data.get("end_date"))

        existing = db.query(Subscription).filter(Subscription.email == email).first()
        if existing:
            existing.plan = tier
            existing.tier = tier
            existing.status = "active"
            existing.paygate_sub_id = sub_data.get("id", "")
            existing.credits_per_month = credits
            existing.expires_at = expires_at
            existing.updated_at = datetime.utcnow()
        else:
            db.add(Subscription(
                email=email,
                plan=tier,
                tier=tier,
                status="active",
                paygate_sub_id=sub_data.get("id", ""),
                credits_per_month=credits,
                expires_at=expires_at,
            ))
        db.commit()
        print(f"[Webhook] subscription.activated: {email} → {tier} ({credits} credits)")
        return {"success": True}

    if event in ("subscription.expired", "subscription.cancelled"):
        existing = db.query(Subscription).filter(Subscription.email == email).first()
        if existing:
            existing.status = "expired" if event == "subscription.expired" else "cancelled"
            existing.plan = "free"
            existing.tier = "free"
            existing.credits_per_month = FREE_CREDITS
            existing.updated_at = datetime.utcnow()
            db.commit()
        print(f"[Webhook] {event}: {email} → free")
        return {"success": True}

    return {"success": True, "ignored": True}
