"""
ReelScript Backend — FastAPI server.
Download IG/YouTube videos, transcribe with Whisper, serve transcripts.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv(Path(__file__).parent / ".env")

from models import init_db
from api.video_routes import router as video_router
from api.collection_routes import router as collection_router
from api.admin_routes import router as admin_router
from api.quota_routes import router as quota_router
from api.invite_routes import router as invite_router
from api.public_routes import router as public_router
from api.webhook_routes import router as webhook_router
from api.websocket import manager

DATA_DIR = Path("./data")
VIDEOS_DIR = DATA_DIR / "videos"
THUMBS_DIR = DATA_DIR / "thumbnails"
AUDIO_DIR = DATA_DIR / "audio"


@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    # Recover pipelines stuck from previous crash
    from api.video_routes import recover_stuck_pipelines
    await recover_stuck_pipelines()
    yield


app = FastAPI(
    title="ReelScript API",
    description="Personal video learning resource library",
    version="1.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "https://reelscript.isnowfriend.com").split(",")
IS_DEV = os.environ.get("DEV_BYPASS_AUTH", "").strip() == "1"
if IS_DEV:
    ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response: StarletteResponse = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# API routes
app.include_router(video_router)
app.include_router(collection_router)
app.include_router(admin_router)
app.include_router(quota_router)
app.include_router(invite_router)
app.include_router(public_router)
app.include_router(webhook_router)

# Serve video files and thumbnails
if VIDEOS_DIR.exists():
    app.mount("/videos", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")
if THUMBS_DIR.exists():
    app.mount("/thumbnails", StaticFiles(directory=str(THUMBS_DIR)), name="thumbnails")
if AUDIO_DIR.exists():
    app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    from api.websocket import DEV_BYPASS_AUTH, _authenticate_ws

    token = websocket.query_params.get("token", "")
    if DEV_BYPASS_AUTH:
        user_id = "dev_admin"
    else:
        user = _authenticate_ws(token)
        if not user:
            await websocket.close(code=4001, reason="Unauthorized")
            return
        user_id = user.get("sub", "anonymous")

    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "reelscript"}


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("REELSCRIPT_PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
