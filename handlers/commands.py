import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

import state
import db
from keyboards import deepseek_picker_keyboard
from config import DEEPSEEK_MODELS
from services.deepseek_ai import chat as ds_chat, DeepSeekConnectionError, DeepSeekAPIError
from handlers.messages import send_response, send_error, _keep_typing, _delete_after

logger = logging.getLogger(__name__)

HELP_TEXT = """\
MultiGPT AI  —  commands

Model
  /deep   — switch between DeepSeek Flash and Pro

Chat tools
  /web    <query>  — one-off forced web search
  /search          — toggle web search on / off for all messages

Session
  /status  — current model and settings
  /reset   — clear conversation history

Send any message, photo or document to start chatting.\
"""


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
        f"Hey {name}! I'm MultiGPT AI.\n"
        "Use /help to see all available commands."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    await update.message.reply_text(HELP_TEXT)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    state.reset(update.effective_user.id)
    sent = await update.message.reply_text("Session cleared.")
    asyncio.create_task(_delete_after(sent, 3))


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    s = state.get(update.effective_user.id)
    model_label = f"DeepSeek {DEEPSEEK_MODELS.get(s['model'], s['model'])}"
    lines = [
        f"Model   : {model_label}",
        f"Search  : {'ON' if s['search'] else 'OFF'}",
        f"Session : {'active' if s['session_id'] else 'new'}",
    ]
    await update.message.reply_text("\n".join(lines))


async def cmd_deep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    await update.message.reply_text(
        "Choose a DeepSeek model:",
        reply_markup=deepseek_picker_keyboard(),
    )


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
    asyncio.create_task(_auto_delete(update.message))
    uid        = update.effective_user.id
    s          = state.get(uid)
    query_text = " ".join(context.args).strip() if context.args else ""
    msg        = update.message

    if not query_text:
        sent = await msg.reply_text("Usage: /web <your search query>")
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
    except DeepSeekAPIError as e:
        await send_error(msg, f"API error: {e}")
    except Exception as e:
        logger.exception("cmd_web error")
        await send_error(msg, f"Unexpected error: {e}")
    finally:
        stop_typing.set()
        typing_task.cancel()
