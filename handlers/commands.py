import asyncio
import os
import tempfile
import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

import state
import db
from keyboards import deepseek_picker_keyboard, duck_picker_keyboard, effort_keyboard
from config import DEEPSEEK_MODELS, DUCK_CHAT_MODELS, DUCK_EFFORT_MODELS
from services.duck_service import generate_image, edit_image, stream_chat as duck_stream, DuckChatError
from services.deepseek_ai import chat as ds_chat, DeepSeekConnectionError, DeepSeekAPIError
from handlers.messages import stream_to_message, _ds_word_stream, send_error, _keep_typing, _delete_after

logger = logging.getLogger(__name__)


async def _auto_delete(msg):
    await asyncio.sleep(0.1)
    try:
        await msg.delete()
    except Exception:
        pass


async def _stream_text(msg, text: str):
    async def _chars():
        batch = ""
        for char in text:
            batch += char
            if len(batch) >= 6:
                yield batch
                batch = ""
                await asyncio.sleep(0.03)
        if batch:
            yield batch

    await stream_to_message(msg, _chars())


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    uid  = update.effective_user.id
    user = update.effective_user
    asyncio.create_task(db.save_user(uid, user.username, user.first_name))
    s = state.get(uid)
    saved = await db.load_state(uid)
    if saved:
        s.update(saved)

    welcome = (
        "Welcome to MultiGPT AI!\n\n"
        "Use /deep for DeepSeek models, /duck for DuckDuckGo models.\n"
        "Use /img_gen to generate images, /img_edit to edit one.\n"
        "Use /web <query> for a forced web search.\n"
        "Use /search to toggle web search on/off for all messages.\n"
        "Use /mode to switch Fast / Reasoning (for supported models)."
    )
    asyncio.create_task(_stream_text(update.message, welcome))


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    state.reset(update.effective_user.id)
    sent = await update.message.reply_text("Session cleared.")
    asyncio.create_task(_delete_after(sent, 3))


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    s = state.get(update.effective_user.id)
    if s["provider"] == "deepseek":
        model_label = f"DeepSeek - {DEEPSEEK_MODELS.get(s['model'], s['model'])}"
    else:
        model_label = f"Duck - {DUCK_CHAT_MODELS.get(s['model'], s['model'])}"
        if s["model"] in DUCK_EFFORT_MODELS:
            model_label += f" ({s['effort']} mode)"
    lines = [
        f"Provider: {s['provider'].capitalize()}",
        f"Model: {model_label}",
        f"Search: {'ON' if s['search'] else 'OFF'}",
        f"Session: {'active' if s['session_id'] else 'new'}",
    ]
    await update.message.reply_text("\n".join(lines))


async def cmd_deep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    await update.message.reply_text(
        "Choose a DeepSeek model:",
        reply_markup=deepseek_picker_keyboard(),
    )


async def cmd_duck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    await update.message.reply_text(
        "Choose a Duck AI model:",
        reply_markup=duck_picker_keyboard(),
    )


async def cmd_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    s = state.get(update.effective_user.id)
    if s["provider"] != "duck" or s["model"] not in DUCK_EFFORT_MODELS:
        sent = await update.message.reply_text(
            "Reasoning mode is only available for: GPT-5 Mini, Claude Haiku, GPT-OSS 120B.\n"
            "Switch to one of those with /duck first."
        )
        asyncio.create_task(_delete_after(sent, 5))
        return
    await update.message.reply_text(
        "Choose thinking mode:",
        reply_markup=effort_keyboard(),
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
        if s["provider"] == "duck":
            s["session_id"] = None
            await stream_to_message(
                msg,
                duck_stream(query_text, model=s["model"], search=True, effort=s["effort"]),
            )
        else:
            raw, sid = await ds_chat(
                query_text,
                model=s["model"],
                thinking=s["thinking"],
                search=True,
                session_id=s["session_id"],
                files=None,
            )
            s["session_id"] = sid
            await stream_to_message(msg, _ds_word_stream(raw))

    except (DeepSeekConnectionError, DuckChatError) as e:
        await send_error(msg, f"Error: {e}")
    except DeepSeekAPIError as e:
        await send_error(msg, f"API error: {e}")
    except Exception as e:
        logger.exception("cmd_web error")
        await send_error(msg, f"Unexpected error: {e}")
    finally:
        stop_typing.set()
        typing_task.cancel()


async def _upload_animation_loop(chat, stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            await chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        except Exception:
            pass
        await asyncio.sleep(4)


async def cmd_img_gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    prompt = " ".join(context.args).strip() if context.args else ""
    msg    = update.message

    if not prompt:
        sent = await msg.reply_text("Usage: /img_gen <description of image>")
        asyncio.create_task(_delete_after(sent, 5))
        return

    stop_anim = asyncio.Event()
    anim_task = asyncio.create_task(_upload_animation_loop(msg.chat, stop_anim))
    try:
        path = await generate_image(prompt)
        stop_anim.set()
        anim_task.cancel()
        with open(path, "rb") as f:
            await msg.reply_photo(f)
        os.remove(path)
    except DuckChatError as e:
        await send_error(msg, f"Image generation error: {e}")
    except Exception as e:
        logger.exception("cmd_img_gen error")
        await send_error(msg, f"Unexpected error: {e}")
    finally:
        stop_anim.set()
        anim_task.cancel()


async def cmd_img_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(_auto_delete(update.message))
    msg     = update.message
    caption = " ".join(context.args).strip() if context.args else ""

    photo = None
    if msg.photo:
        photo = msg.photo[-1]
    elif msg.reply_to_message and msg.reply_to_message.photo:
        photo = msg.reply_to_message.photo[-1]

    if not photo:
        sent = await msg.reply_text(
            "Send a photo with /img_edit <caption>, "
            "or reply to a photo with /img_edit <caption>."
        )
        asyncio.create_task(_delete_after(sent, 5))
        return

    if not caption:
        sent = await msg.reply_text("Please provide an edit caption after /img_edit.")
        asyncio.create_task(_delete_after(sent, 5))
        return

    stop_anim = asyncio.Event()
    anim_task = asyncio.create_task(_upload_animation_loop(msg.chat, stop_anim))
    src_path  = None
    out_path  = None
    try:
        tg_file = await photo.get_file()
        fd, src_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        await tg_file.download_to_drive(src_path)

        out_path = await edit_image(caption, src_path)

        stop_anim.set()
        anim_task.cancel()
        with open(out_path, "rb") as f:
            await msg.reply_photo(f)

    except DuckChatError as e:
        await send_error(msg, f"Image edit error: {e}")
    except Exception as e:
        logger.exception("cmd_img_edit error")
        await send_error(msg, f"Unexpected error: {e}")
    finally:
        stop_anim.set()
        anim_task.cancel()
        for p in [src_path, out_path]:
            if p:
                try:
                    os.remove(p)
                except OSError:
                    pass
