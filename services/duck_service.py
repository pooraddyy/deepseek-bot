import asyncio
import os
import tempfile
from duck_ai import DuckChat, DuckChatError
from config import DUCK_EFFORT_MODELS

__all__ = ["chat", "generate_image", "edit_image", "DuckChatError"]


async def chat(
    prompt: str,
    model: str,
    search: bool = False,
    effort: str = "fast",
) -> str:
    def _run():
        kwargs: dict = {"model": model}
        if model in DUCK_EFFORT_MODELS:
            kwargs["effort"] = effort
        with DuckChat(**kwargs) as duck:
            return duck.ask(prompt, web_search=search)

    return await asyncio.to_thread(_run)


async def generate_image(prompt: str) -> str:
    def _run():
        fd, path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        with DuckChat(model="image") as duck:
            duck.generate_image(prompt, save_to=path)
        return path

    return await asyncio.to_thread(_run)


async def edit_image(caption: str, image_path: str) -> str:
    def _run():
        fd, path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        with DuckChat(model="image") as duck:
            duck.edit_image(caption, image_path, save_to=path)
        return path

    return await asyncio.to_thread(_run)
