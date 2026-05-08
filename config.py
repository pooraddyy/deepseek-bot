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
    "deepseek-v4-flash": "⚡ Flash",
    "deepseek-v4-pro":   "🧠 Pro",
}

DUCK_CHAT_MODELS: dict[str, str] = {
    "gpt4":     "GPT-4o Mini",
    "gpt5_mini":"GPT-5 Mini",
    "claude":   "Claude Haiku",
    "llama":    "Llama 4",
    "mistral":  "Mistral",
    "gpt-oss":  "GPT-OSS 120B",
}

DUCK_EFFORT_MODELS: set[str] = {"gpt5_mini", "claude", "gpt-oss"}

DEFAULT_PROVIDER = "deepseek"
DEFAULT_MODEL    = "deepseek-v4-flash"
