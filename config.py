import os
import sys
from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        sys.exit(f"[config] ERROR: {key} is not set.")
    return val

BOT_TOKEN: str   = _require("BOT_TOKEN")
AUTH_TOKEN: str  = _require("AUTH_TOKEN")
PORT: int        = int(os.getenv("PORT", "8000"))
MONGODB_URL: str = _require("MONGODB_URL")

DEEPSEEK_MODELS: dict[str, str] = {
    "deepseek-v4-flash": "Flash",
    "deepseek-v4-pro":   "Pro",
}

DEFAULT_PROVIDER = "deepseek"
DEFAULT_MODEL    = "deepseek-v4-flash"
