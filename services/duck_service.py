import asyncio
import os
import tempfile
import threading
import logging
from duck_ai import DuckChat, DuckChatError, ImagePart, image_generation, gpt5_mini
from config import DUCK_EFFORT_MODELS

__all__ = [
    "chat", "stream_chat", "vision_chat",
    "generate_image", "edit_image", "DuckChatError",
]

logger = logging.getLogger(__name__)


def _duck_kwargs(model: str, effort: str) -> dict:
    kwargs: dict = {"model": model}
    if model in DUCK_EFFORT_MODELS:
        kwargs["effort"] = effort
    return kwargs


async def chat(
    prompt: str,
    model: str,
    search: bool = False,
    effort: str = "fast",
) -> str:
    def _run():
        with DuckChat(**_duck_kwargs(model, effort)) as duck:
            return duck.ask(prompt, web_search=search)
    return await asyncio.to_thread(_run)


async def stream_chat(
    prompt: str,
    model: str,
    search: bool = False,
    effort: str = "fast",
):
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _run():
        try:
            with DuckChat(**_duck_kwargs(model, effort)) as duck:
                for chunk in duck.stream(prompt, web_search=search):
                    loop.call_soon_threadsafe(queue.put_nowait, ("chunk", chunk))
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

    threading.Thread(target=_run, daemon=True).start()

    while True:
        kind, value = await queue.get()
        if kind == "done":
            break
        elif kind == "error":
            raise value
        else:
            yield value


async def vision_chat(prompt: str, image_paths: list[str]) -> str:
    def _run():
        parts = [prompt] + [ImagePart.from_path(p) for p in image_paths]
        with DuckChat(model=gpt5_mini) as duck:
            return duck.ask(parts)
    return await asyncio.to_thread(_run)


async def generate_image(prompt: str) -> str:
    def _run():
        fd, path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        logger.info("Generating image: %s", prompt[:60])
        with DuckChat(model=image_generation) as duck:
            duck.generate_image(prompt, save_to=path)
        logger.info("Image generated: %s", path)
        return path
    return await asyncio.to_thread(_run)


async def edit_image(caption: str, image_path: str) -> str:
    def _run():
        fd, path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        logger.info("Editing image %s | caption: %s", image_path, caption[:60])
        with DuckChat(model=image_generation) as duck:
            duck.edit_image(caption, image_path, save_to=path)
        logger.info("Image edited: %s", path)
        return path
    return await asyncio.to_thread(_run)
