from collections import defaultdict
from config import DEFAULT_MODEL, DEFAULT_PROVIDER


def _default_state() -> dict:
    return {
        "session_id": None,
        "provider":   DEFAULT_PROVIDER,
        "model":      DEFAULT_MODEL,
        "thinking":   False,
        "search":     False,
        "effort":     "fast",
    }


_users: dict = defaultdict(_default_state)
album_buffer: dict = defaultdict(list)


def get(uid: int) -> dict:
    return _users[uid]


def reset(uid: int) -> None:
    _users[uid] = _default_state()
