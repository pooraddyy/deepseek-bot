import asyncio
import os
import tempfile
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

import state
import db
from config import DEFAULT_MODEL
from services.deepseek_ai import chat as ds_chat, DeepSeekConnectionError, DeepSeekAPIError
from services.duck_service import stream_chat as duck_stream, vision_chat, DuckChatError
from lib import escape_md

logger = logging.getLogger(__name__)

MSG_LIMIT       = 3800
STREAM_INTERVAL = 0.8

IMAGE_ONLY_PROMPT = "Describe this image in detail."
ALBUM_ONLY_PROMPT = "Describe these images in detail."
IMAGE_EXTS        = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".heic"}


def _is_image(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def _is_real_timeout(exc: Exception) -> bool:
    """Only match genuine DeepSeek file-parsing timeouts, not generic errors."""
    text = str(exc).lower()
    return "timed out" in text and ("parsing" in text or "file_id" in text or "fetch" in text)


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

    # Use UPLOAD_DOCUMENT animation for files, TYPING for plain text
    anim_action = ChatAction.UPLOAD_DOCUMENT if file_paths else ChatAction.TYPING
    stop_anim   = asyncio.Event()
    anim_task   = asyncio.create_task(_keep_typing(msg.chat, anim_action, stop_anim))

    try:
        if file_paths:
            # ── File uploads: ALWAYS use DeepSeek for OCR / vision ──────────────
            # Use current DS model if on deepseek, else fall back to default flash
            ds_model   = s["model"] if s["provider"] == "deepseek" else DEFAULT_MODEL
            all_images = all(_is_image(p) for p in file_paths)

            try:
                raw, sid = await ds_chat(
                    prompt,
                    model=ds_model,
                    thinking=s.get("thinking", False),
                    search=s["search"],
                    session_id=s["session_id"],
                    files=file_paths,
                )
                s["session_id"] = sid
                stop_anim.set()
                anim_task.cancel()
                await stream_to_message(msg, _ds_word_stream(raw))

            except (DeepSeekAPIError, Exception) as exc:
                if all_images and _is_real_timeout(exc):
                    # Real parse timeout → fallback to duck vision (images only)
                    logger.warning("DeepSeek vision timed out — falling back to duck vision: %s", exc)
                    stop_anim.set()
                    anim_task.cancel()
                    raw = await vision_chat(prompt, file_paths)
                    s["session_id"] = None
                    await stream_to_message(msg, _ds_word_stream(raw))
                else:
                    raise

        elif s["provider"] == "duck":
            # ── Text chat via duck ───────────────────────────────────────────────
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
            # ── Text chat via DeepSeek ───────────────────────────────────────────
            raw, sid = await ds_chat(
                prompt,
                model=s["model"],
                thinking=s["thinking"],
                search=s["search"],
                session_id=s["session_id"],
                files=None,
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
    first_msg  = items[0]["msg"]
    prompt     = next(
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

    # ── Album (multiple images/docs sent together) ───────────────────────────────
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

    # ── Single message ───────────────────────────────────────────────────────────
    file_paths: list[str] = []

    if msg.photo:
        tg_file = await msg.photo[-1].get_file()
        file_paths.append(await _download(tg_file, ".jpg"))
    elif msg.document:
        tg_file = await msg.document.get_file()
        suffix  = os.path.splitext(msg.document.file_name or "")[1] or ".bin"
        file_paths.append(await _download(tg_file, suffix))

    # Smart default prompt when no caption/text given
    if file_paths and not (msg.text or msg.caption):
        prompt = IMAGE_ONLY_PROMPT
    else:
        prompt = msg.text or msg.caption or ""

    asyncio.create_task(_process(uid, msg, prompt, file_paths))
