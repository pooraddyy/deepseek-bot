import asyncio
import os
import tempfile
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

import state
import db
from services.deepseek_ai import chat as ds_chat, DeepSeekConnectionError, DeepSeekAPIError
from lib import escape_md

logger = logging.getLogger(__name__)

TG_LIMIT          = 4096
SAFE_LIMIT        = TG_LIMIT - 100
IMAGE_ONLY_PROMPT = "Describe this image in detail."
ALBUM_ONLY_PROMPT = "Describe these images in detail."


def _split_text(text: str) -> list[str]:
    if len(text) <= SAFE_LIMIT:
        return [text]
    parts: list[str] = []
    while len(text) > SAFE_LIMIT:
        window = text[:SAFE_LIMIT]
        idx = window.rfind("\n\n")
        if idx < SAFE_LIMIT // 4:
            idx = window.rfind("\n")
        if idx < 1:
            idx = window.rfind(" ")
        if idx < 1:
            idx = SAFE_LIMIT
        parts.append(text[:idx].rstrip())
        text = text[idx:].lstrip("\n")
    if text.strip():
        parts.append(text.strip())
    return [p for p in parts if p]


async def send_response(msg, text: str) -> None:
    if not text:
        text = "(empty response)"
    for part in _split_text(text):
        escaped = escape_md(part)
        try:
            await msg.reply_text(escaped, parse_mode="MarkdownV2")
        except Exception:
            try:
                await msg.reply_text(part)
            except Exception:
                logger.exception("Failed to send message part")


async def _collect_duck(gen) -> str:
    chunks: list[str] = []
    async for chunk in gen:
        chunks.append(chunk)
    return "".join(chunks)


async def _download(file_obj, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    await file_obj.download_to_drive(path)
    return path


async def _delete_after(msg, delay: float = 5.0):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


async def send_error(msg, text: str, delay: float = 5.0):
    sent = await msg.reply_text(text)
    asyncio.create_task(_delete_after(sent, delay))


async def _keep_typing(chat, action: str = ChatAction.TYPING, stop_event: asyncio.Event = None):
    while not (stop_event and stop_event.is_set()):
        try:
            await chat.send_action(action)
        except Exception:
            pass
        await asyncio.sleep(4)


async def _process(uid: int, msg, prompt: str, file_paths: list) -> None:
    s = state.get(uid)
    anim_action = ChatAction.UPLOAD_DOCUMENT if file_paths else ChatAction.TYPING
    stop_anim   = asyncio.Event()
    anim_task   = asyncio.create_task(_keep_typing(msg.chat, anim_action, stop_anim))

    try:
        raw, sid = await ds_chat(
            prompt,
            model=s["model"],
            thinking=s["thinking"],
            search=s["search"],
            session_id=s["session_id"],
            files=file_paths or None,
        )
        s["session_id"] = sid
        stop_anim.set()
        anim_task.cancel()
        await send_response(msg, raw)

    except DeepSeekConnectionError:
        await send_error(msg, "Connection error — please try again.")
    except DeepSeekAPIError as e:
        await send_error(msg, f"API error: {e}")
    except Exception as e:
        logger.exception("Unexpected error in _process")
        await send_error(msg, f"Unexpected error: {e}")
    finally:
        stop_anim.set()
        anim_task.cancel()
        for p in file_paths:
            try:
                os.remove(p)
            except OSError:
                pass


async def _flush_album(context: ContextTypes.DEFAULT_TYPE) -> None:
    uid, group_id = context.job.data
    items = state.album_buffer.pop(group_id, [])
    if not items:
        return
    items.sort(key=lambda x: x["mid"])
    first_msg = items[0]["msg"]
    prompt    = next(
        (it["caption"] for it in items if it["caption"]),
        ALBUM_ONLY_PROMPT,
    )
    file_paths: list[str] = []
    for it in items:
        try:
            file_paths.append(await _download(it["tg_file"], it["suffix"]))
        except Exception:
            logger.exception("Failed to download album item")
    await _process(uid, first_msg, prompt, file_paths)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg:
        return

    uid  = update.effective_user.id
    user = update.effective_user
    asyncio.create_task(db.save_user(uid, user.username, user.first_name))

    raw_caption = (msg.caption or "").strip()

    if msg.media_group_id:
        if msg.photo:
            tg_file = await msg.photo[-1].get_file()
            suffix  = ".jpg"
        elif msg.document:
            tg_file = await msg.document.get_file()
            suffix  = os.path.splitext(msg.document.file_name or "")[1] or ".bin"
        else:
            return
        state.album_buffer[msg.media_group_id].append({
            "mid":     msg.message_id,
            "msg":     msg,
            "tg_file": tg_file,
            "suffix":  suffix,
            "caption": raw_caption,
        })
        for job in context.job_queue.get_jobs_by_name(f"album:{msg.media_group_id}"):
            job.schedule_removal()
        context.job_queue.run_once(
            _flush_album,
            when=1.5,
            data=(uid, msg.media_group_id),
            name=f"album:{msg.media_group_id}",
        )
        return

    file_paths: list[str] = []

    if msg.photo:
        tg_file = await msg.photo[-1].get_file()
        file_paths.append(await _download(tg_file, ".jpg"))
    elif msg.document:
        tg_file = await msg.document.get_file()
        suffix  = os.path.splitext(msg.document.file_name or "")[1] or ".bin"
        file_paths.append(await _download(tg_file, suffix))

    if file_paths and not (msg.text or raw_caption):
        prompt = IMAGE_ONLY_PROMPT
    else:
        prompt = msg.text or raw_caption or ""

    asyncio.create_task(_process(uid, msg, prompt, file_paths))
