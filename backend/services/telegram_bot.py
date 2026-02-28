"""
Telegram Bot — send a video URL, ReelScript processes it automatically.

Setup:
1. Talk to @BotFather on Telegram, create a new bot, get the token
2. Add TELEGRAM_BOT_TOKEN to backend/.env
3. Optionally add TELEGRAM_ALLOWED_USERS (comma-separated user IDs) to restrict access
"""

import os
import re
import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

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


_URL_RE = re.compile(r"https?://\S+")


def _extract_video_urls(text: str) -> list[str]:
    """Extract all video URLs from a message."""
    return [u for u in _URL_RE.findall(text) if _is_video_url(u)]


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
    "/retry <編號|all> — 重試失敗的影片\n"
    "/help — 顯示說明"
)


def _retry_keyboard(video_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 重試", callback_data=f"retry:{video_id}"),
    ]])


def _retry_url_keyboard(url: str) -> InlineKeyboardMarkup:
    # Callback data max 64 bytes — truncate URL if needed
    cb_data = f"retryurl:{url}"
    if len(cb_data.encode('utf-8')) > 64:
        cb_data = f"retryurl:{url[:50]}"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 重試", callback_data=cb_data),
    ]])


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
                    reply_markup=_retry_keyboard(video_id),
                )
                return
        except Exception as e:
            logger.error(f"Poll error for {short_id}: {e}")
            continue

    await bot.send_message(
        chat_id=chat_id,
        text=f"⏰ 處理超時：{title}\n用 /list 查看狀態",
        reply_markup=_retry_keyboard(video_id),
    )


async def _handle_single_url(url: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process a single video URL."""
    msg = await update.message.reply_text("⬇️ 處理中...")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{REELSCRIPT_API}/api/videos/process",
                json={"url": url},
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

        asyncio.create_task(_poll_and_notify(
            update.effective_chat.id, video_id, title, context.bot
        ))
    except httpx.HTTPStatusError as e:
        logger.error(f"Process API error: {e.response.status_code} {e.response.text}")
        error_detail = e.response.text[:100] if e.response.text else str(e.response.status_code)
        video_id = None
        try:
            video_id = e.response.json().get("video_id")
        except Exception:
            pass
        markup = _retry_keyboard(video_id) if video_id else _retry_url_keyboard(url)
        await msg.edit_text(f"❌ 失敗：{error_detail}", reply_markup=markup)
    except Exception as e:
        logger.error(f"Process failed: {e}")
        await msg.edit_text(
            f"❌ 失敗：{e}",
            reply_markup=_retry_url_keyboard(url),
        )


async def _handle_batch_urls(urls: list[str], update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process multiple video URLs via batch endpoint."""
    msg = await update.message.reply_text(f"⬇️ 批次處理 {len(urls)} 個連結...")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{REELSCRIPT_API}/api/videos/batch-process",
                json={"urls": urls},
                headers=BOT_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        started = data.get("started", 0)
        total = data.get("total", 0)

        lines = []
        for r in results:
            if r.get("success"):
                title = r.get("title") or "未命名"
                short_id = (r.get("video_id") or "")[:8]
                lines.append(f"✅ {title[:30]} ({short_id})")
                # Start polling for each
                if r.get("status") in ("downloading",):
                    asyncio.create_task(_poll_and_notify(
                        update.effective_chat.id, r["video_id"], title, context.bot
                    ))
            else:
                err = r.get("error", "未知錯誤")
                lines.append(f"❌ {r.get('url', '?')[:30]}... — {err}")

        text = f"📦 批次處理：{started}/{total} 開始\n\n" + "\n".join(lines)
        if started > 0:
            text += "\n\n完成後會逐一通知你！"
        await msg.edit_text(text)

    except Exception as e:
        logger.error(f"Batch process failed: {e}")
        await msg.edit_text(f"❌ 批次處理失敗：{e}")


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update):
        await update.message.reply_text("⛔ 未授權。你的 User ID: " + str(update.effective_user.id))
        return

    text = update.message.text.strip()
    urls = _extract_video_urls(text)

    if not urls:
        await update.message.reply_text("請傳送 YouTube 或 Instagram 的影片連結。")
        return

    if len(urls) == 1:
        await _handle_single_url(urls[0], update, context)
    else:
        await _handle_batch_urls(urls, update, context)


async def _do_retry(video_id: str, chat_id: int, bot):
    """Call retry API and start polling for the result."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{REELSCRIPT_API}/api/videos/{video_id}/retry",
            headers=BOT_HEADERS,
        )
        if resp.status_code == 400:
            await bot.send_message(chat_id=chat_id, text="ℹ️ 這部影片不是失敗狀態，不需要重試。")
            return
        resp.raise_for_status()

    # Fetch title for notification
    async with httpx.AsyncClient(timeout=10) as client:
        info = await client.get(f"{REELSCRIPT_API}/api/videos/{video_id}", headers=BOT_HEADERS)
        title = info.json().get("title", "未命名") if info.status_code == 200 else "未命名"

    short_id = video_id[:8]
    await bot.send_message(
        chat_id=chat_id,
        text=f"🔄 重新處理中...\n\n📹 {title}\n🆔 {short_id}\n\n完成後會自動通知你！",
    )
    asyncio.create_task(_poll_and_notify(chat_id, video_id, title, bot))


async def callback_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline retry button press (by video_id)."""
    query = update.callback_query
    await query.answer()

    if not query.data or not query.data.startswith("retry:"):
        return

    video_id = query.data.split(":", 1)[1]

    # Remove the retry button from the original message
    await query.edit_message_reply_markup(reply_markup=None)

    try:
        await _do_retry(video_id, query.message.chat_id, context.bot)
    except Exception as e:
        logger.error(f"Callback retry failed: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"❌ 重試失敗：{e}",
            reply_markup=_retry_keyboard(video_id),
        )


async def callback_retry_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline retry button press (by URL — for initial API failures)."""
    query = update.callback_query
    await query.answer()

    if not query.data or not query.data.startswith("retryurl:"):
        return

    url = query.data.split(":", 1)[1]

    # Remove the retry button
    await query.edit_message_reply_markup(reply_markup=None)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{REELSCRIPT_API}/api/videos/process",
                json={"url": url},
                headers=BOT_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()

        title = data.get("title") or "未命名"
        video_id = data.get("video_id", "")
        short_id = video_id[:8]

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🔄 重新處理中...\n\n📹 {title}\n🆔 {short_id}\n\n完成後會自動通知你！",
        )
        asyncio.create_task(_poll_and_notify(
            query.message.chat_id, video_id, title, context.bot
        ))
    except Exception as e:
        logger.error(f"URL retry failed: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"❌ 重試失敗：{e}",
            reply_markup=_retry_url_keyboard(url),
        )


async def cmd_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update):
        await update.message.reply_text("⛔ 未授權。")
        return

    if not context.args:
        await update.message.reply_text("用法：\n/retry <ID> — 重試單個影片\n/retry all — 重試所有失敗的")
        return

    arg = context.args[0].strip().lower()

    if arg == "all":
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{REELSCRIPT_API}/api/videos/retry-all-failed",
                    headers=BOT_HEADERS,
                )
                resp.raise_for_status()
                data = resp.json()

            count = data.get("retried", 0)
            if count == 0:
                await update.message.reply_text("✅ 沒有失敗的影片需要重試。")
                return

            await update.message.reply_text(f"🔄 已重新處理 {count} 部失敗影片，完成後會通知你！")

            # Start polling for each retried video
            for vid in data.get("video_ids", []):
                asyncio.create_task(_poll_and_notify(
                    update.effective_chat.id, vid, "重試影片", context.bot
                ))
        except Exception as e:
            logger.error(f"Retry all failed: {e}")
            await update.message.reply_text(f"❌ 重試失敗：{e}")
        return

    # Single video retry by short ID
    video_id = await _get_video_id(context, update)
    if not video_id:
        return

    try:
        await _do_retry(video_id, update.effective_chat.id, context.bot)
    except Exception as e:
        logger.error(f"Retry failed: {e}")
        await update.message.reply_text(
            f"❌ 重試失敗：{e}",
            reply_markup=_retry_keyboard(video_id),
        )


def create_bot() -> Application:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment")

    builder = Application.builder().token(token)

    # Support Cloudflare Workers reverse proxy for Telegram API
    tg_proxy = os.getenv("TELEGRAM_PROXY")
    if tg_proxy:
        base = tg_proxy.rstrip("/")
        logger.info(f"Using Telegram API proxy: {base}")
        builder = builder.base_url(f"{base}/bot").base_file_url(f"{base}/file/bot")

    app = builder.build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("translate", cmd_translate))
    app.add_handler(CommandHandler("vocab", cmd_vocab))
    app.add_handler(CommandHandler("study", cmd_study))
    app.add_handler(CommandHandler("retry", cmd_retry))
    app.add_handler(CallbackQueryHandler(callback_retry_url, pattern=r"^retryurl:"))
    app.add_handler(CallbackQueryHandler(callback_retry, pattern=r"^retry:"))
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
