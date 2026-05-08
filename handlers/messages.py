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
from services.duck_service import stream_chat as duck_stream, DuckChatError
from lib import escape_md

logger = logging.getLogger(__name__)

MSG_LIMIT       = 3800
STREAM_INTERVAL = 0.8


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


async def _ds_word_stream(text: str):
    words = text.split()
    batch: list[str] = []
    for word in words:
        batch.append(word)
        if len(batch) >= 5:
            yield " ".join(batch) + " "
            batch = []
            await asyncio.sleep(0.04)
    if batch:
        yield " ".join(batch)


async def stream_to_message(msg, chunks):
    sent        = await msg.reply_text("▌")
    accumulated = ""
    last_edit   = asyncio.get_event_loop().time()

    async for chunk in chunks:
        accumulated += chunk
        now = asyncio.get_event_loop().time()
        if now - last_edit >= STREAM_INTERVAL:
            display = accumulated if len(accumulated) <= MSG_LIMIT else accumulated[-MSG_LIMIT:]
            try:
                await sent.edit_text(escape_md(display) + "▌", parse_mode="MarkdownV2")
            except Exception:
                try:
                    await sent.edit_text(display + "▌")
                except Exception:
                    pass
            last_edit = now

    if not accumulated:
        accumulated = "(empty response)"

    if len(accumulated) <= MSG_LIMIT:
        escaped = escape_md(accumulated)
        try:
            await sent.edit_text(escaped, parse_mode="MarkdownV2")
        except Exception:
            await sent.edit_text(accumulated)
    else:
        try:
            await sent.delete()
        except Exception:
            pass
        for i in range(0, len(accumulated), MSG_LIMIT):
            part = accumulated[i : i + MSG_LIMIT]
            try:
                await msg.reply_text(escape_md(part), parse_mode="MarkdownV2")
            except Exception:
                await msg.reply_text(part)


async def _process(uid: int, msg, prompt: str, file_paths: list) -> None:
    s = state.get(uid)
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(
        _keep_typing(msg.chat, ChatAction.TYPING, stop_typing)
    )
    try:
        if s["provider"] == "duck":
            if file_paths:
                from duck_ai import DuckChat, ImagePart

                def _run_vision():
                    parts = [prompt] + [ImagePart.from_path(p) for p in file_paths]
                    with DuckChat(model=s["model"]) as duck:
                        return duck.ask(parts, web_search=s["search"])

                raw = await asyncio.to_thread(_run_vision)
                s["session_id"] = None

                async def _single_chunk():
                    yield raw

                await stream_to_message(msg, _single_chunk())
            else:
                s["session_id"] = None
                await stream_to_message(
                    msg,
                    duck_stream(
                        prompt,
                        model=s["model"],
                        search=s["search"],
                        effort=s["effort"],
                    ),
                )

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
            await stream_to_message(msg, _ds_word_stream(raw))

    except DeepSeekConnectionError:
        await send_error(msg, "Connection error — please try again.")
    except (DeepSeekAPIError, DuckChatError) as e:
        await send_error(msg, f"API error: {e}")
    except Exception as e:
        logger.exception("Unexpected error in _process")
        await send_error(msg, f"Unexpected error: {e}")
    finally:
        stop_typing.set()
        typing_task.cancel()
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
    asyncio.create_task(db.save_user(uid, user.username, user.first_name))

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

    asyncio.create_task(_process(uid, msg, prompt, file_paths))
