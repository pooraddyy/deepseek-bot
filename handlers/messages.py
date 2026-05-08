import os
import tempfile
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

import state
import db
from services.deepseek_ai import chat as ds_chat, DeepSeekConnectionError, DeepSeekAPIError
from services.duck_service import chat as duck_chat, DuckChatError
from lib import escape_md

logger = logging.getLogger(__name__)

SPLIT_MARKER = "\n@|@|@|@\n\n"
MSG_LIMIT    = 3800


async def _download(file_obj, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    await file_obj.download_to_drive(path)
    return path


async def _send_response(msg, raw_text: str) -> None:
    if not raw_text:
        raw_text = "(empty response)"

    parts: list[str] = []
    for chunk in raw_text.split(SPLIT_MARKER):
        if len(chunk) <= MSG_LIMIT:
            parts.append(chunk)
        else:
            for i in range(0, len(chunk), MSG_LIMIT):
                parts.append(chunk[i : i + MSG_LIMIT])

    for part in parts:
        escaped = escape_md(part)
        try:
            await msg.reply_text(escaped, parse_mode="MarkdownV2")
        except Exception:
            await msg.reply_text(part)


async def _process(uid: int, msg, prompt: str, file_paths: list) -> None:
    s = state.get(uid)
    try:
        await msg.chat.send_action(ChatAction.TYPING)

        if s["provider"] == "duck":
            if file_paths:
                from duck_ai import DuckChat, ImagePart
                import asyncio

                def _run_vision():
                    parts = [prompt] + [ImagePart.from_path(p) for p in file_paths]
                    with DuckChat(model=s["model"]) as duck:
                        return duck.ask(parts, web_search=s["search"])

                raw = await asyncio.to_thread(_run_vision)
            else:
                raw = await duck_chat(
                    prompt,
                    model=s["model"],
                    search=s["search"],
                    effort=s["effort"],
                )
            s["session_id"] = None
            await _send_response(msg, raw)

        else:
            raw, sid = await ds_chat(
                prompt,
                model=s["model"],
                thinking=s["thinking"],
                search=s["search"],
                session_id=s["session_id"],
                files=file_paths or None,
            )
            s["session_id"] = sid
            await _send_response(msg, raw)

    except DeepSeekConnectionError:
        await msg.reply_text("Connection error — please try again.")
    except (DeepSeekAPIError, DuckChatError) as e:
        await msg.reply_text(f"API error: {e}")
    except Exception as e:
        logger.exception("Unexpected error in _process")
        await msg.reply_text(f"Unexpected error: {e}")
    finally:
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
    prompt    = next((it["caption"] for it in items if it["caption"]), "Describe these images")

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
    await db.save_user(uid, user.username, user.first_name)

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
            "caption": msg.caption or "",
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

    prompt     = msg.text or msg.caption or "Describe this"
    file_paths: list[str] = []

    if msg.photo:
        tg_file = await msg.photo[-1].get_file()
        file_paths.append(await _download(tg_file, ".jpg"))
    elif msg.document:
        tg_file = await msg.document.get_file()
        suffix  = os.path.splitext(msg.document.file_name or "")[1] or ".bin"
        file_paths.append(await _download(tg_file, suffix))

    await _process(uid, msg, prompt, file_paths)
