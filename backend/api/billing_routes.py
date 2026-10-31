"""
Billing routes — Pro / Unlimited subscription checkout via PayGate (NewebPay 定期定額).

reelscript only exchanges the logged-in user's email for a PayGate checkout_url.
Order creation, NewebPay notify, renewals and cancellation all live in PayGate;
activation arrives through /api/webhooks/paygate (subscription.activated) which
upserts the local Subscription cache that every quota gate already reads.
"""

import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from middleware.auth import require_auth

router = APIRouter(prefix="/api/billing", tags=["billing"])

PAYGATE_URL = os.environ.get("PAYGATE_URL", "").rstrip("/")
PUBLIC_URL = os.environ.get("REELSCRIPT_WEB", "").rstrip("/")
PRODUCT = "reelscript"

PLAN_IDS = {
    "pro": os.environ.get("REELSCRIPT_PRO_PLAN_ID", "reelscript:pro:monthly"),
    "unlimited": os.environ.get("REELSCRIPT_UNLIMITED_PLAN_ID", "reelscript:unlimited:monthly"),
}

# Synthetic identities that must never reach a payment flow.
NON_HUMAN_EMAILS = {"bot@reelscript", "dev@reelscript"}


class CheckoutRequest(BaseModel):
    plan: str


def _paygate_token() -> str:
    token = os.environ.get("PAYGATE_TOKEN", "")
    if not token or not PAYGATE_URL or not PUBLIC_URL:
        raise HTTPException(status_code=503, detail="Billing not configured")
    return token


def _user_email(user: dict) -> str:
    email = (user.get("email") or "").strip().lower()
    if not email or email in NON_HUMAN_EMAILS:
        raise HTTPException(status_code=400, detail="Account has no email — please log in with LetMeUse")
    return email


async def _paygate_post(path: str, payload: dict) -> tuple[int, dict]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_paygate_token()}",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(f"{PAYGATE_URL}{path}", json=payload, headers=headers)
    except httpx.HTTPError as exc:
        print(f"[billing] PayGate unreachable: {exc}")
        raise HTTPException(status_code=502, detail="Checkout service unavailable, please try again later")
    try:
        data = res.json()
    except ValueError:
        data = {}
    return res.status_code, data


@router.post("/checkout")
async def create_checkout(body: CheckoutRequest, user: dict = Depends(require_auth)):
    """Create a NewebPay subscription order in PayGate and return its hosted checkout_url."""
    plan_id = PLAN_IDS.get(body.plan)
    if not plan_id:
        raise HTTPException(status_code=400, detail="Unknown plan")
    email = _user_email(user)

    status, data = await _paygate_post(
        "/api/newebpay/subscribe",
        {
            "email": email,
            "product": PRODUCT,
            "plan_id": plan_id,
            "return_url": f"{PUBLIC_URL}/pricing?upgraded=1",
        },
    )
    checkout_url = data.get("checkout_url")
    if status >= 400 or not checkout_url:
        print(f"[billing] checkout failed: {status} {data.get('error', '')}")
        raise HTTPException(status_code=502, detail="Checkout service unavailable, please try again later")
    return {"checkout_url": checkout_url}


@router.post("/cancel")
async def cancel_subscription(user: dict = Depends(require_auth)):
    """Terminate the NewebPay 委託; the paid period stays active until end_date (PayGate expires it)."""
    email = _user_email(user)
    status, data = await _paygate_post("/api/newebpay/cancel", {"email": email, "product": PRODUCT})
    if status == 404:
        raise HTTPException(status_code=404, detail="No active subscription")
    if status >= 400:
        print(f"[billing] cancel failed: {status} {data.get('error', '')}")
        raise HTTPException(status_code=502, detail="Cancel service unavailable, please try again later")
    return {"ok": True, "active_until": data.get("active_until")}
