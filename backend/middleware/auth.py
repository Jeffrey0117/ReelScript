"""
Auth middleware — verify LetMeUse JWT tokens.
Supports dual auth: JWT Bearer token OR legacy X-Admin-Key header.
"""

import os
import jwt
from fastapi import HTTPException, Request, Depends


LMU_APP_SECRET = os.environ.get("LMU_APP_SECRET", "Rs7kW2mNpQ4xYvB9cD1fH3jL5tA8uE6g")
LMU_APP_ID = os.environ.get("LMU_APP_ID", "app_3lXIxPKb")
LEGACY_ADMIN_KEY = os.environ.get("ADMIN_KEY", "reelscript-admin-2024")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "WcxHAMuFcPmzNwgEMTZDtSf4axNvjwaUp-w2JxojGi0")
BOT_USER_ID = os.environ.get("BOT_USER_ID", "usr_reelscript_admin")
DEV_BYPASS_AUTH = os.environ.get("DEV_BYPASS_AUTH", "").strip() == "1"

DEV_USER = {"sub": "dev_admin", "role": "admin", "email": "dev@reelscript", "app": LMU_APP_ID}


def get_current_user(request: Request) -> dict:
    """Extract and verify user from LetMeUse JWT, or bot service token."""
    if DEV_BYPASS_AUTH:
        return DEV_USER

    auth_header = request.headers.get("Authorization", "")

    # Bot service token: X-Bot-Token header
    bot_token = request.headers.get("X-Bot-Token", "")
    if bot_token == BOT_TOKEN:
        return {"sub": BOT_USER_ID, "role": "admin", "email": "bot@reelscript", "app": LMU_APP_ID}

    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header[7:]
    try:
        payload = jwt.decode(token, LMU_APP_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("app") != LMU_APP_ID:
        raise HTTPException(status_code=401, detail="Invalid app")

    return payload


def optional_auth(request: Request) -> dict | None:
    """FastAPI dependency — return user if authenticated, None otherwise."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        return get_current_user(request)
    except HTTPException:
        return None


def require_auth(request: Request) -> dict:
    """FastAPI dependency — require authenticated user."""
    return get_current_user(request)


def require_admin(request: Request) -> dict:
    """FastAPI dependency — require admin role.
    Supports dual auth: JWT with admin role OR legacy X-Admin-Key.
    """
    # Try JWT first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        user = get_current_user(request)
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin required")
        return user

    # Fallback: legacy X-Admin-Key
    key = request.headers.get("X-Admin-Key", "")
    if key == LEGACY_ADMIN_KEY:
        return {"sub": "legacy-admin", "role": "admin", "email": "admin"}

    raise HTTPException(status_code=401, detail="Unauthorized")
