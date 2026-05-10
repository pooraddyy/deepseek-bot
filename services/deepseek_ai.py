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
        return _client().chat(
            prompt,
            model=model,
            thinking=thinking,
            search=search,
            session_id=session_id,
            files=files if files else None,
        )

    response = await asyncio.to_thread(_run)
    return response.full_response, response.session_id
