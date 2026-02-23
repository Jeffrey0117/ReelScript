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

from dotenv import load_dotenv
load_dotenv()

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logger = logging.getLogger(__name__)

REELSCRIPT_API = os.getenv("REELSCRIPT_API", "http://localhost:8002")
REELSCRIPT_WEB = os.getenv("REELSCRIPT_WEB", "http://localhost:5173")
BOT_TOKEN = os.getenv("BOT_TOKEN", "WcxHAMuFcPmzNwgEMTZDtSf4axNvjwaUp-w2JxojGi0")
BOT_HEADERS = {"X-Bot-Token": BOT_TOKEN}


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


def _check_auth(update: Update) -> bool:
    allowed = _get_allowed_users()
    return not allowed or update.effective_user.id in allowed


HELP_TEXT = (
    "🎬 ReelScript Bot\n\n"
    "傳送 YouTube 或 Instagram 影片連結給我，\n"
    "我會自動下載、轉錄並翻譯。\n\n"
    "指令：\n"
    "/list — 查看最近的影片\n"
    "/translate <編號> — 翻譯指定影片\n"
    "/vocab <編號> — 分析單字\n"
    "/study <編號> — 取得學習頁面連結\n"
    "/help — 顯示說明"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{REELSCRIPT_API}/api/videos", headers=BOT_HEADERS)
        resp.raise_for_status()
        videos = resp.json()

    if not videos:
        await update.message.reply_text("還沒有影片，傳個連結給我吧！")
        return

    lines = []
    for i, v in enumerate(videos[:15], 1):
        status_icon = {
            "ready": "✅", "downloading": "⬇️",
            "transcribing": "🎙️", "failed": "❌",
        }.get(v["status"], "⏳")
        title = v.get("title") or "未命名"
        vid = v["id"][:8]
        lines.append(f"{i}. {status_icon} {title[:35]}\n   ID: {vid}")

    text = (
        f"📚 最近的影片（共 {len(videos)} 部）：\n\n"
        + "\n\n".join(lines)
        + "\n\n💡 用 /study <ID> 開啟學習模式"
    )
    await update.message.reply_text(text)


async def _get_video_id(context: ContextTypes.DEFAULT_TYPE, update: Update) -> str | None:
    """Extract video ID from command args, supporting short IDs."""
    if not context.args:
        await update.message.reply_text("請提供影片 ID，例如：/study abc123\n用 /list 查看 ID")
        return None

    short_id = context.args[0].strip()

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{REELSCRIPT_API}/api/videos", headers=BOT_HEADERS)
        resp.raise_for_status()
        videos = resp.json()

    # Match by prefix
    matches = [v for v in videos if v["id"].startswith(short_id)]
    if len(matches) == 1:
        return matches[0]["id"]
    elif len(matches) > 1:
        await update.message.reply_text(f"找到多個匹配，請用更長的 ID：\n" +
            "\n".join(f"  {m['id'][:12]} — {m.get('title', '未命名')[:30]}" for m in matches[:5]))
        return None
    else:
        await update.message.reply_text(f"找不到 ID 為「{short_id}」的影片。用 /list 查看列表。")
        return None


async def cmd_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update):
        await update.message.reply_text("⛔ 未授權。")
        return

    video_id = await _get_video_id(context, update)
    if not video_id:
        return

    msg = await update.message.reply_text("🔄 翻譯中...")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{REELSCRIPT_API}/api/videos/{video_id}/translate", headers=BOT_HEADERS)
            resp.raise_for_status()
            data = resp.json()

        if data.get("message") == "Already translated":
            await msg.edit_text("✅ 已翻譯過了！")
        else:
            seg_count = len(data.get("segments", []))
            await msg.edit_text(f"✅ 翻譯完成！共 {seg_count} 段")
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        await msg.edit_text(f"❌ 翻譯失敗：{e}")


async def cmd_vocab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update):
        await update.message.reply_text("⛔ 未授權。")
        return

    video_id = await _get_video_id(context, update)
    if not video_id:
        return

    msg = await update.message.reply_text("🔄 分析單字中...")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{REELSCRIPT_API}/api/videos/{video_id}/analyze-vocabulary", headers=BOT_HEADERS)
            resp.raise_for_status()
            data = resp.json()

        if data.get("message") == "Already analyzed":
            await msg.edit_text("✅ 已分析過了！")
        else:
            # Show a preview of vocabulary
            segments = data.get("segments", [])
            words = []
            for seg in segments:
                for v in seg.get("vocabulary", []):
                    if v["word"] not in [w[0] for w in words]:
                        words.append((v["word"], v["translation"]))
            preview = "\n".join(f"  • {w} — {t}" for w, t in words[:10])
            remaining = len(words) - 10
            text = f"✅ 單字分析完成！\n\n{preview}"
            if remaining > 0:
                text += f"\n  ...還有 {remaining} 個"
            await msg.edit_text(text)
    except Exception as e:
        logger.error(f"Vocabulary analysis failed: {e}")
        await msg.edit_text(f"❌ 分析失敗：{e}")


async def cmd_study(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_id = await _get_video_id(context, update)
    if not video_id:
        return

    url = f"{REELSCRIPT_WEB}/study/{video_id}"
    await update.message.reply_text(
        f"📖 學習模式連結：\n{url}\n\n"
        f"🎬 觀看連結：\n{REELSCRIPT_WEB}/watch/{video_id}"
    )


async def _poll_and_notify(chat_id: int, video_id: str, title: str, bot):
    """Poll video status and notify user when processing completes."""
    max_polls = 120  # 10 minutes max (120 * 5s)
    short_id = video_id[:8]

    for _ in range(max_polls):
        await asyncio.sleep(5)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{REELSCRIPT_API}/api/videos/{video_id}", headers=BOT_HEADERS)
                if resp.status_code != 200:
                    continue
                data = resp.json()

            status = data.get("status")
            if status == "ready":
                watch_url = f"{REELSCRIPT_WEB}/watch/{video_id}"
                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"✅ 處理完成！\n\n"
                        f"📹 {title}\n\n"
                        f"🎬 觀看連結：\n{watch_url}\n\n"
                        f"/translate {short_id} — 翻譯\n"
                        f"/vocab {short_id} — 分析單字\n"
                        f"/study {short_id} — 學習模式"
                    ),
                )
                return
            elif status == "failed":
                error = data.get("error_message") or "未知錯誤"
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ 處理失敗：{title}\n\n錯誤：{error}",
                )
                return
        except Exception as e:
            logger.error(f"Poll error for {short_id}: {e}")
            continue

    await bot.send_message(
        chat_id=chat_id,
        text=f"⏰ 處理超時：{title}\n用 /list 查看狀態",
    )


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update):
        await update.message.reply_text("⛔ 未授權。你的 User ID: " + str(update.effective_user.id))
        return

    text = update.message.text.strip()

    if not _is_video_url(text):
        await update.message.reply_text("請傳送 YouTube 或 Instagram 的影片連結。")
        return

    msg = await update.message.reply_text("⬇️ 處理中...")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{REELSCRIPT_API}/api/videos/process",
                json={"url": text},
                headers=BOT_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()

        title = data.get("title") or "未命名"
        video_id = data.get("video_id", "")
        short_id = video_id[:8]

        await msg.edit_text(
            f"⏳ 下載＋轉錄中...\n\n"
            f"📹 {title}\n"
            f"🆔 {short_id}\n\n"
            f"完成後會自動通知你！"
        )

        # Start background polling for completion
        asyncio.create_task(_poll_and_notify(
            update.effective_chat.id, video_id, title, context.bot
        ))
    except Exception as e:
        logger.error(f"Process failed: {e}")
        await msg.edit_text(f"❌ 失敗：{e}")


def create_bot() -> Application:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("translate", cmd_translate))
    app.add_handler(CommandHandler("vocab", cmd_vocab))
    app.add_handler(CommandHandler("study", cmd_study))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    return app


def run_bot():
    """Run the Telegram bot (blocking). Call from a separate process or thread."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Telegram bot...")
    bot = create_bot()
    bot.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_bot()
