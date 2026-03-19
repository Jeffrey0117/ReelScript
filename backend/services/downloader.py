"""
Video downloader service — supports Instagram and YouTube via yt-dlp.
Adapted from AutoReel's ig_ytdlp_downloader + youtube_downloader.
"""

import asyncio
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, Any

import shutil

import yt_dlp

from api.websocket import manager

# Ensure ffmpeg is discoverable
FFMPEG_PATH = shutil.which("ffmpeg") or r"C:\tools\ffmpeg\ffmpeg.exe"
FFPROBE_PATH = shutil.which("ffprobe") or r"C:\tools\ffmpeg\ffprobe.exe"

logger = logging.getLogger(__name__)

# Project data dir (relative to backend/)
VIDEOS_DIR = Path("./data/videos")
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
THUMBS_DIR = Path("./data/thumbnails")
THUMBS_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR = Path("./data/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _detect_source(url: str) -> str:
    """Detect video source from URL."""
    if re.search(r"instagram\.com|instagr\.am", url):
        return "ig"
    if re.search(r"youtube\.com|youtu\.be", url):
        return "youtube"
    return "unknown"


def detect_content_type(url: str, info: dict = None) -> str:
    """Detect if content is music/lyrics based on URL and metadata."""
    if re.search(r"music\.youtube\.com", url):
        return "lyrics"
    if info:
        title = (info.get("title") or "").lower()
        categories = info.get("categories") or []
        cats_lower = [c.lower() for c in categories]
        if "music" in cats_lower:
            return "lyrics"
        if any(kw in title for kw in ("official lyric", "lyric video", "lyrics video")):
            return "lyrics"
    return "video"


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
                "content_type": detect_content_type(url, info),
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _has_qsv() -> bool:
    """Check if Intel QSV hardware encoder is available."""
    try:
        r = subprocess.run(
            [FFMPEG_PATH, "-hide_banner", "-init_hw_device", "qsv=hw", "-f", "lavfi",
             "-i", "nullsrc=s=64x64:d=0.1", "-c:v", "h264_qsv", "-f", "null", "-"],
            capture_output=True, timeout=10,
        )
        return r.returncode == 0
    except Exception:
        return False


_QSV_AVAILABLE: bool | None = None


def _ensure_h264(filepath: Path) -> None:
    """Re-encode video to H.264 if needed for iOS/mobile compatibility.
    Uses Intel QSV hardware encoding when available for ~5-10x speedup."""
    global _QSV_AVAILABLE
    if _QSV_AVAILABLE is None:
        _QSV_AVAILABLE = _has_qsv()
        logger.info(f"[Downloader] QSV hardware encoding: {'available' if _QSV_AVAILABLE else 'unavailable'}")

    try:
        result = subprocess.run(
            [FFPROBE_PATH, "-v", "quiet", "-print_format", "json", "-show_streams", str(filepath)],
            capture_output=True, text=True, timeout=30,
        )
        info = json.loads(result.stdout)
        video_codec = next(
            (s["codec_name"] for s in info["streams"] if s["codec_type"] == "video"),
            None,
        )

        if video_codec == "h264":
            logger.info(f"[Downloader] {filepath.name} already H.264, applying faststart...")
            tmp = filepath.with_suffix(".tmp.mp4")
            subprocess.run(
                [
                    "ffmpeg", "-i", str(filepath),
                    "-c:v", "copy", "-c:a", "copy",
                    "-movflags", "+faststart", "-y", str(tmp),
                ],
                capture_output=True, timeout=120, check=True,
            )
            filepath.unlink()
            tmp.rename(filepath)
            return

        logger.info(f"[Downloader] Re-encoding {filepath.name} from {video_codec} to H.264 ({'QSV' if _QSV_AVAILABLE else 'CPU'})...")
        tmp = filepath.with_suffix(".tmp.mp4")

        if _QSV_AVAILABLE:
            encode_cmd = [
                "ffmpeg", "-hwaccel", "qsv", "-i", str(filepath),
                "-c:v", "h264_qsv", "-profile:v", "main",
                "-global_quality", "23", "-preset", "faster",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                "-y", str(tmp),
            ]
        else:
            encode_cmd = [
                "ffmpeg", "-i", str(filepath),
                "-c:v", "libx264", "-profile:v", "main", "-level", "3.1",
                "-crf", "23", "-preset", "veryfast",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                "-y", str(tmp),
            ]

        subprocess.run(encode_cmd, capture_output=True, timeout=600, check=True)
        filepath.unlink()
        tmp.rename(filepath)
        logger.info(f"[Downloader] Re-encoded {filepath.name} to H.264")
    except Exception as e:
        logger.error(f"[Downloader] H.264 re-encode failed for {filepath.name}: {e}")
        tmp = filepath.with_suffix(".tmp.mp4")
        if tmp.exists():
            tmp.unlink()


def generate_thumbnail(video_path: Path, video_id: str) -> str | None:
    """Extract a frame from the video as a JPEG thumbnail."""
    thumb_path = THUMBS_DIR / f"{video_id}.jpg"
    if thumb_path.exists():
        return thumb_path.name
    try:
        subprocess.run(
            [
                "ffmpeg", "-i", str(video_path),
                "-ss", "00:00:01", "-frames:v", "1",
                "-vf", "scale=480:-2",
                "-q:v", "3", "-y", str(thumb_path),
            ],
            capture_output=True, timeout=30, check=True,
        )
        logger.info(f"[Downloader] Thumbnail generated: {thumb_path.name}")
        return thumb_path.name
    except Exception as e:
        logger.error(f"[Downloader] Thumbnail generation failed: {e}")
        return None


def extract_audio(video_path: Path, video_id: str) -> str | None:
    """Extract MP3 audio from MP4 video file. Returns filename or None.
    Uses stream copy for AAC sources, re-encodes only when necessary."""
    audio_path = AUDIO_DIR / f"{video_id}.mp3"
    if audio_path.exists():
        return audio_path.name
    if not video_path.exists():
        logger.error(f"[Downloader] Video not found for audio extraction: {video_path}")
        return None
    try:
        # Check source audio codec — copy if already mp3
        probe = subprocess.run(
            [FFPROBE_PATH, "-v", "quiet", "-print_format", "json", "-show_streams",
             "-select_streams", "a:0", str(video_path)],
            capture_output=True, text=True, timeout=15,
        )
        audio_codec = None
        if probe.returncode == 0:
            streams = json.loads(probe.stdout).get("streams", [])
            if streams:
                audio_codec = streams[0].get("codec_name")

        if audio_codec == "mp3":
            cmd = [FFMPEG_PATH, "-i", str(video_path), "-vn", "-c:a", "copy", "-y", str(audio_path)]
        else:
            cmd = [
                "ffmpeg", "-i", str(video_path),
                "-vn", "-acodec", "libmp3lame", "-b:a", "128k",
                "-y", str(audio_path),
            ]

        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        logger.info(f"[Downloader] Audio extracted: {audio_path.name}")
        return audio_path.name
    except Exception as e:
        logger.error(f"[Downloader] Audio extraction failed: {e}")
        if audio_path.exists():
            audio_path.unlink()
        return None


async def download_video(url: str, video_id: str, content_type: str = "video") -> Dict[str, Any]:
    """
    Download a video or audio from IG or YouTube.

    Args:
        url: Video URL
        video_id: Database video ID for progress tracking
        content_type: "video" or "lyrics" — lyrics downloads audio only

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

    common_opts = {
        "outtmpl": str(VIDEOS_DIR / "%(id)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": str(Path(FFMPEG_PATH).parent),
    }

    if content_type == "lyrics":
        ydl_opts = {
            **common_opts,
            "format": "bestaudio[ext=m4a]/bestaudio/best",
        }
    else:
        ydl_opts = {
            **common_opts,
            "format": "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
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

        # Ensure H.264 codec for iOS/mobile compatibility (skip for audio-only lyrics)
        filepath = Path(filename)
        if content_type != "lyrics" and filepath.exists():
            await asyncio.to_thread(_ensure_h264, filepath)

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
