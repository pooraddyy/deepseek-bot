from collections import defaultdict
from config import DEFAULT_MODEL


def _default_state() -> dict:
    return {
        "session_id": None,
        "model":      DEFAULT_MODEL,
        "thinking":   False,
        "search":     False,
    }


_users: dict = defaultdict(_default_state)
album_buffer: dict = defaultdict(list)


def get(uid: int) -> dict:
    return _users[uid]


def reset(uid: int) -> None:
    _users[uid] = _default_state()
