"""
Telegram Bot — send a video URL, ReelScript processes it automatically.

Setup:
1. Talk to @BotFather on Telegram, create a new bot, get the token
2. Add TELEGRAM_BOT_TOKEN to backend/.env
3. Optionally add TELEGRAM_ALLOWED_USERS (comma-separated user IDs) to restrict access
"""

import os
import asyncio
import logging
from pathlib import Path

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logger = logging.getLogger(__name__)

REELSCRIPT_API = os.getenv("REELSCRIPT_API", "http://localhost:8002")


def _get_allowed_users() -> set[int]:
    raw = os.getenv("TELEGRAM_ALLOWED_USERS", "")
    if not raw.strip():
        return set()
    return {int(uid.strip()) for uid in raw.split(",") if uid.strip()}


def _is_video_url(text: str) -> bool:
    patterns = [
        "youtube.com/", "youtu.be/",
        "instagram.com/reel", "instagram.com/p/",
    ]
    return any(p in text.lower() for p in patterns)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ReelScript Bot\n\n"
        "Send me a YouTube or Instagram video URL.\n"
        "I'll download, transcribe, and translate it for you.\n\n"
        "Commands:\n"
        "/list — Show recent videos\n"
        "/help — Show this message"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{REELSCRIPT_API}/api/videos")
        resp.raise_for_status()
        videos = resp.json()

    if not videos:
        await update.message.reply_text("No videos yet.")
        return

    lines = []
    for v in videos[:10]:
        status_icon = {"ready": "✅", "downloading": "⬇️", "transcribing": "🎙️", "failed": "❌"}.get(v["status"], "⏳")
        title = v.get("title") or "Untitled"
        lines.append(f"{status_icon} {title[:40]}")

    await update.message.reply_text(
        f"Recent videos ({len(videos)} total):\n\n" + "\n".join(lines)
    )


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    allowed = _get_allowed_users()
    if allowed and update.effective_user.id not in allowed:
        await update.message.reply_text("Unauthorized. Your user ID: " + str(update.effective_user.id))
        return

    text = update.message.text.strip()

    if not _is_video_url(text):
        await update.message.reply_text("Please send a YouTube or Instagram URL.")
        return

    msg = await update.message.reply_text("⬇️ Processing...")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{REELSCRIPT_API}/api/videos/process",
                json={"url": text},
            )
            resp.raise_for_status()
            data = resp.json()

        title = data.get("title") or "Untitled"
        video_id = data.get("video_id", "")

        await msg.edit_text(
            f"✅ Started processing!\n\n"
            f"Title: {title}\n"
            f"Status: downloading → transcribing → ready\n\n"
            f"View: {REELSCRIPT_API.replace('localhost', '127.0.0.1')}/watch/{video_id}\n\n"
            f"Use /list to check status."
        )
    except Exception as e:
        logger.error(f"Process failed: {e}")
        await msg.edit_text(f"❌ Failed: {e}")


def create_bot() -> Application:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    return app


def run_bot():
    """Run the Telegram bot (blocking). Call from a separate process or thread."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Telegram bot...")
    bot = create_bot()
    bot.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_bot()
