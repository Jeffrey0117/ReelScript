"""
Video downloader service — supports Instagram and YouTube via yt-dlp.
Adapted from AutoReel's ig_ytdlp_downloader + youtube_downloader.
"""

import asyncio
import re
from pathlib import Path
from typing import Dict, Any

import yt_dlp

from api.websocket import manager

# Project data dir (relative to backend/)
VIDEOS_DIR = Path("./data/videos")
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


def _detect_source(url: str) -> str:
    """Detect video source from URL."""
    if re.search(r"instagram\.com|instagr\.am", url):
        return "ig"
    if re.search(r"youtube\.com|youtu\.be", url):
        return "youtube"
    return "unknown"


async def get_video_info(url: str) -> Dict[str, Any]:
    """Fetch video metadata without downloading."""
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "success": True,
                "id": info.get("id"),
                "title": info.get("title"),
                "duration": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
                "channel": info.get("channel") or info.get("uploader"),
                "source": _detect_source(url),
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def download_video(url: str, video_id: str) -> Dict[str, Any]:
    """
    Download a video from IG or YouTube.

    Args:
        url: Video URL
        video_id: Database video ID for progress tracking

    Returns:
        Result dict with filename or error
    """
    source = _detect_source(url)

    def progress_hook(d: Dict[str, Any]):
        if d["status"] == "downloading":
            percent_str = d.get("_percent_str", "0%").strip()
            try:
                percent = float(percent_str.replace("%", ""))
            except (ValueError, AttributeError):
                percent = 0

            asyncio.create_task(manager.broadcast({
                "type": "download_progress",
                "data": {
                    "video_id": video_id,
                    "progress": percent,
                    "speed": d.get("_speed_str", ""),
                },
            }))

        elif d["status"] == "finished":
            asyncio.create_task(manager.broadcast({
                "type": "download_progress",
                "data": {
                    "video_id": video_id,
                    "progress": 100,
                    "status": "processing",
                },
            }))

    ydl_opts = {
        "outtmpl": str(VIDEOS_DIR / "%(id)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
    }

    try:
        await manager.broadcast({
            "type": "download_started",
            "data": {"video_id": video_id, "url": url},
        })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        result = {
            "success": True,
            "filename": Path(filename).name,
            "title": info.get("title"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "channel": info.get("channel") or info.get("uploader"),
            "source": source,
        }

        await manager.broadcast({
            "type": "download_completed",
            "data": {"video_id": video_id, **result},
        })

        return result

    except Exception as e:
        error_msg = str(e)
        await manager.broadcast({
            "type": "download_error",
            "data": {"video_id": video_id, "error": error_msg},
        })
        return {"success": False, "error": error_msg}
