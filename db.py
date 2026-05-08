import motor.motor_asyncio
from config import MONGODB_URL

_client   = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
_db       = _client["multigpt_bot"]
users_col = _db["users"]
state_col = _db["user_state"]


async def save_user(uid: int, username: str | None, first_name: str | None) -> None:
    await users_col.update_one(
        {"uid": uid},
        {"$set": {"uid": uid, "username": username, "first_name": first_name}},
        upsert=True,
    )


async def save_state(uid: int, s: dict) -> None:
    await state_col.update_one(
        {"uid": uid},
        {"$set": {
            "uid":      uid,
            "provider": s["provider"],
            "model":    s["model"],
            "search":   s["search"],
            "thinking": s["thinking"],
            "effort":   s["effort"],
        }},
        upsert=True,
    )


async def load_state(uid: int) -> dict | None:
    doc = await state_col.find_one({"uid": uid})
    if doc:
        return {
            "provider": doc.get("provider", "deepseek"),
            "model":    doc.get("model"),
            "search":   doc.get("search", False),
            "thinking": doc.get("thinking", False),
            "effort":   doc.get("effort", "fast"),
        }
    return None
