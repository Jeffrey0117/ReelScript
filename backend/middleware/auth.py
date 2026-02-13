"""
Auth middleware — verify adman JWT tokens.
Supports dual auth: JWT Bearer token OR legacy X-Admin-Key header.
"""

import os
import jwt
from fastapi import HTTPException, Request, Depends


ADMAN_APP_SECRET = os.environ.get("ADMAN_APP_SECRET", "UEpzMyu5ItZ8Bx6vxqV6H56SzLhnXscO")
ADMAN_APP_ID = os.environ.get("ADMAN_APP_ID", "app_yX0u0SiJ")
LEGACY_ADMIN_KEY = os.environ.get("ADMIN_KEY", "reelscript-admin-2024")


def get_current_user(request: Request) -> dict:
    """Extract and verify user from adman JWT in Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header[7:]
    try:
        payload = jwt.decode(token, ADMAN_APP_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("app") != ADMAN_APP_ID:
        raise HTTPException(status_code=401, detail="Invalid app")

    return payload


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
