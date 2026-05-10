import asyncio
from functools import lru_cache
from deepseek import DeepSeekClient, DeepSeekConnectionError, DeepSeekAPIError
from config import AUTH_TOKEN

__all__ = ["chat", "DeepSeekConnectionError", "DeepSeekAPIError"]


@lru_cache(maxsize=1)
def _client() -> DeepSeekClient:
    return DeepSeekClient(api_key=AUTH_TOKEN)


async def chat(
    prompt: str,
    model: str,
    thinking: bool,
    search: bool,
    session_id: str | None,
    files: list | None,
) -> tuple[str, str]:
    def _run():
        file_ids = None
        if files:
            file_ids = [
                _client().upload_file(f, model=model, thinking=thinking, timeout=300.0)
                for f in files
            ]
        return _client().chat(
            prompt,
            model=model,
            thinking=thinking,
            search=search,
            session_id=session_id,
            file_ids=file_ids,
        )

    response = await asyncio.to_thread(_run)
    return response.full_response, response.session_id
