import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from . import state, db
from .keyboards import deepseek_picker_keyboard
from .messages import send_response, send_error, _keep_typing, _delete_after
from config import DEEPSEEK_MODELS
from services.deepseek_ai import chat as ds_chat, DeepSeekConnectionError, DeepSeekAPIError

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "<b>DeepSeek Bot</b> — Commands\n\n"
    "<b>Model</b>\n"
    "<blockquote>/deep — Switch between Flash and Pro</blockquote>\n"
    "<b>Web Search</b>\n"
    "<blockquote>"
    "/web &lt;query&gt; — one-off forced web search\n"
    "/search — toggle web search on / off for all messages"
    "</blockquote>\n"
    "<b>Thinking</b>\n"
    "<blockquote>/think — toggle DeepSeek reasoning mode on / off</blockquote>\n"
    "<b>Session</b>\n"
    "<blockquote>"
    "/status — show current model and settings\n"
    "/reset — clear conversation history"
    "</blockquote>\n\n"
    "Send any message, photo or document to start chatting."
)


async def _auto_delete(msg):
    await asyncio.sleep(0.1)
    try:
        await msg.delete()
    except Exception:
        pass


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    uid  = update.effective_user.id
    user = update.effective_user
    asyncio.create_task(db.save_user(uid, user.username, user.first_name))
    s = state.get(uid)
    saved = await db.load_state(uid)
    if saved:
        s.update(saved)
    name = user.first_name or "there"
    await update.message.reply_text(
        f"Hey {name}! I'm DeepSeek Bot.\n"
        "Use /help to see all available commands."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    sent = await update.message.reply_text(HELP_TEXT, parse_mode="HTML")
    asyncio.create_task(_delete_after(sent, 15))


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    state.reset(update.effective_user.id)
    sent = await update.message.reply_text("Session cleared.")
    asyncio.create_task(_delete_after(sent, 3))


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    s = state.get(update.effective_user.id)
    model_label = DEEPSEEK_MODELS.get(s["model"], s["model"])
    lines = [
        f"Model   : {model_label}",
        f"Thinking: {'ON' if s['thinking'] else 'OFF'}",
        f"Search  : {'ON' if s['search'] else 'OFF'}",
        f"Session : {'active' if s['session_id'] else 'new'}",
    ]
    await update.message.reply_text("\n".join(lines))


async def cmd_deep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    await update.message.reply_text(
        "Choose a model:",
        reply_markup=deepseek_picker_keyboard(),
    )


async def cmd_think(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    uid = update.effective_user.id
    s   = state.get(uid)
    s["thinking"] = not s["thinking"]
    asyncio.create_task(db.save_state(uid, s))
    status = "ON" if s["thinking"] else "OFF"
    sent = await update.message.reply_text(f"Thinking mode: {status}")
    asyncio.create_task(_delete_after(sent, 3))


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    uid = update.effective_user.id
    s   = state.get(uid)
    s["search"] = not s["search"]
    asyncio.create_task(db.save_state(uid, s))
    status = "ON" if s["search"] else "OFF"
    sent = await update.message.reply_text(f"Web search: {status}")
    asyncio.create_task(_delete_after(sent, 3))


async def cmd_web(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid        = update.effective_user.id
    s          = state.get(uid)
    query_text = " ".join(context.args).strip() if context.args else ""
    msg        = update.message
    if not query_text:
        asyncio.create_task(_auto_delete(update.message))
        sent = await msg.reply_text("Usage: /web &lt;your search query&gt;", parse_mode="HTML")
        asyncio.create_task(_delete_after(sent, 5))
        return
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(_keep_typing(msg.chat, ChatAction.TYPING, stop_typing))
    try:
        raw, sid = await ds_chat(
            query_text,
            model=s["model"],
            thinking=s["thinking"],
            search=True,
            session_id=s["session_id"],
            files=None,
        )
        s["session_id"] = sid
        stop_typing.set()
        typing_task.cancel()
        await send_response(msg, raw)
    except DeepSeekConnectionError:
        await send_error(msg, "Connection error — please try again.")
    except DeepSeekAPIError:
        await send_error(msg, "DeepSeek API error — please try again later.")
    except Exception:
        logger.exception("cmd_web error")
        await send_error(msg, "Kuch gadbad ho gayi — please try again.")
    finally:
        stop_typing.set()
        typing_task.cancel()
