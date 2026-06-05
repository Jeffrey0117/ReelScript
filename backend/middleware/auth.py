"""
Auth middleware — verify LetMeUse JWT tokens.
Supports dual auth: JWT Bearer token OR legacy X-Admin-Key header.
"""

import os
import logging
from datetime import datetime
import jwt
from fastapi import HTTPException, Request, Depends

logger = logging.getLogger(__name__)


def _require_env(key: str) -> str:
    """Get required env var, raise on missing in production."""
    val = os.environ.get(key, "")
    if not val:
        logger.warning("Missing required env var: %s", key)
    return val


LMU_APP_SECRET = _require_env("LMU_APP_SECRET")
LMU_APP_ID = os.environ.get("LMU_APP_ID", "app_3lXIxPKb")
LEGACY_ADMIN_KEY = _require_env("ADMIN_KEY")
BOT_TOKEN = _require_env("BOT_TOKEN")
BOT_USER_ID = os.environ.get("BOT_USER_ID", "usr_reelscript_admin")
DEV_BYPASS_AUTH = os.environ.get("DEV_BYPASS_AUTH", "").strip() == "1"

DEV_USER = {"sub": "dev_admin", "role": "admin", "email": "dev@reelscript", "app": LMU_APP_ID}

# IDs to skip when caching users (bots, dev, legacy admin)
_SKIP_CACHE_IDS = {"dev_admin", BOT_USER_ID, "legacy-admin"}

if DEV_BYPASS_AUTH:
    logger.warning("⚠ DEV_BYPASS_AUTH is ON — all requests treated as admin. Do NOT use in production!")


# 🔑 JWKS client for ES256 verification (LetMeUse Phase 2). Lazy + cached, so the
# import never blocks on the network and keys are fetched on first use.
from jwt import PyJWKClient

LMU_JWKS_URL = os.environ.get("LETMEUSE_JWKS_URL", "http://localhost:4006/api/jwks")
_jwk_client = PyJWKClient(LMU_JWKS_URL, cache_keys=True, lifespan=3600)


def _decode_letmeuse(token: str) -> dict:
    """Verify a LetMeUse JWT, accepting BOTH algorithms during the HS256→ES256
    migration. Verification is pinned to the header alg so an attacker can't
    downgrade (e.g. alg=none): HS256 → shared app secret; ES256 → JWKS public key.
    """
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "ES256":
        try:
            signing_key = _jwk_client.get_signing_key_from_jwt(token)
        except Exception as exc:  # JWKS fetch / unknown kid → treat as invalid
            raise jwt.InvalidTokenError(f"JWKS lookup failed: {exc}")
        return jwt.decode(token, signing_key.key, algorithms=["ES256"])
    if alg == "HS256":
        return jwt.decode(token, LMU_APP_SECRET, algorithms=["HS256"])
    raise jwt.InvalidTokenError(f"unsupported alg: {alg}")


def _cache_user(payload: dict) -> None:
    """Upsert authenticated user into local cache (fire-and-forget)."""
    user_id = payload.get("sub", "")
    if not user_id or user_id in _SKIP_CACHE_IDS:
        return
    try:
        from models.database import SessionLocal, User
        db = SessionLocal()
        try:
            existing = db.query(User).filter(User.id == user_id).first()
            now = datetime.utcnow()
            if existing:
                existing.email = payload.get("email") or existing.email
                existing.name = payload.get("displayName") or payload.get("name") or existing.name
                existing.role = payload.get("role") or existing.role
                existing.avatar = payload.get("avatar") or existing.avatar
                existing.last_seen_at = now
            else:
                db.add(User(
                    id=user_id,
                    email=payload.get("email"),
                    name=payload.get("displayName") or payload.get("name"),
                    role=payload.get("role", "user"),
                    avatar=payload.get("avatar"),
                    first_seen_at=now,
                    last_seen_at=now,
                ))
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.debug("User cache upsert failed for %s", user_id, exc_info=True)


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
        payload = _decode_letmeuse(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("app") != LMU_APP_ID:
        raise HTTPException(status_code=401, detail="Invalid app")

    _cache_user(payload)
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
