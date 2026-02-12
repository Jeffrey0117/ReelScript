"""
ReelScript Backend — FastAPI server.
Download IG/YouTube videos, transcribe with Whisper, serve transcripts.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from models import init_db
from api.video_routes import router as video_router
from api.collection_routes import router as collection_router
from api.websocket import manager

DATA_DIR = Path("./data")
VIDEOS_DIR = DATA_DIR / "videos"


@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(
    title="ReelScript API",
    description="Personal video learning resource library",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(video_router)
app.include_router(collection_router)

# Serve video files
if VIDEOS_DIR.exists():
    app.mount("/videos", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
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
