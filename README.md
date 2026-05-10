# DeepSeek Telegram Bot

A fully-featured Telegram bot powered by **DeepSeek AI** — supports web search, image and document reading, code generation, and multi-turn conversations with per-user session memory.

Built using [p2d-deepseek](https://github.com/pooraddyy/deepseek-free) — an unofficial free Python client for DeepSeek that works with just your **browser auth token**. No paid API key needed.

---

## What this bot can do

| Capability | Details |
|---|---|
| **Chat** | Multi-turn conversation with full memory per user |
| **Web Search** | Real-time web results via `/search` toggle or `/web` one-off |
| **Image Reading** | Send any photo — the bot describes, analyses, or answers questions about it |
| **Document OCR** | Upload PDFs, Word docs, Excel sheets, code files, CSVs — the bot reads and responds |
| **Code Generation** | Ask for code in any language — generates, explains, and debugs |
| **Album Support** | Send multiple photos or documents at once — all processed together |
| **Model Switching** | Flash (fast) or Pro (deeper reasoning) via `/deep` |
| **Persistent Settings** | Model preference and search toggle saved per user in MongoDB |

---

## Models

| Model | Label | Best for |
|---|---|---|
| `deepseek-v4-flash` | Flash | Fast replies, everyday chat, code — **default** |
| `deepseek-v4-pro` | Pro | Complex reasoning, maths, long documents, research |

---

## Commands

| Command | Action |
|---|---|
| `/start` | Greet and restore saved settings |
| `/help` | Show all commands |
| `/deep` | Switch between DeepSeek Flash and Pro |
| `/web <query>` | One-off forced web search |
| `/search` | Toggle web search on / off for all messages |
| `/status` | Show current model and settings |
| `/reset` | Clear conversation history |

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/pooraddyy/deepseek-bot.git
cd deepseek-bot
```

### 2. Install dependencies

```bash
pip install -r bot/requirements.txt
```

### 3. Configure environment

Copy `bot/sample.env` to `bot/.env` and fill in your values:

```bash
cp bot/sample.env bot/.env
```

```env
BOT_TOKEN=your_telegram_bot_token_here
AUTH_TOKEN=your_deepseek_auth_token_here
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
PORT=8000
```

- **BOT_TOKEN** — get from [@BotFather](https://t.me/BotFather) on Telegram
- **AUTH_TOKEN** — your DeepSeek auth token (see section below — no paid API key needed)
- **MONGODB_URL** — MongoDB Atlas connection string (free tier works)

### 4. Run

```bash
cd bot
python main.py
```

---

## Getting your DeepSeek AUTH_TOKEN

This bot uses [p2d-deepseek](https://github.com/pooraddyy/deepseek-free) — an unofficial client that authenticates with DeepSeek using your **browser session token**, the same one DeepSeek's own website uses. This means you get full DeepSeek access completely free — no API subscription required.

### Method 1 — LocalStorage (Fastest, Desktop)

1. Go to [chat.deepseek.com](https://chat.deepseek.com) and log in
2. Press `F12` to open DevTools
3. Go to the **Application** tab (click `»` if hidden)
4. In the left sidebar: **Local Storage** → `https://chat.deepseek.com`
5. Find the key `userToken` and copy its **value** — that is your `AUTH_TOKEN`

### Method 2 — Network Tab (Desktop)

1. Go to [chat.deepseek.com](https://chat.deepseek.com) and log in
2. Open DevTools → **Network** tab
3. Send any message in the chat
4. Click any request going to `chat.deepseek.com`
5. Open **Headers** → find the `authorization` header
6. Copy the value **without** the `Bearer ` prefix

### Method 3 — Kiwi Browser (Android)

1. Install [Kiwi Browser](https://play.google.com/store/apps/details?id=com.kiwibrowser.browser) from the Play Store
2. Open [chat.deepseek.com](https://chat.deepseek.com) and log in
3. Tap menu (⋮) → **Developer Tools**
4. Go to **Application** tab → **Local Storage** → `https://chat.deepseek.com`
5. Find `userToken` and copy its **value**

> **Token expired?** Tokens expire when your DeepSeek session ends or you log out. Just repeat any method above to get a fresh one.

---

## Built with

- [p2d-deepseek](https://github.com/pooraddyy/deepseek-free) — free unofficial DeepSeek Python client (auth token, no API key)
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) v22
- [Motor](https://motor.readthedocs.io/) — async MongoDB driver
- [aiohttp](https://docs.aiohttp.org/) — lightweight health check server

---

## Project structure

```
bot/
├── main.py                  # Entry point, handler registration, health server
├── config.py                # Env vars, model definitions
├── state.py                 # In-memory per-user state
├── db.py                    # MongoDB persistence (users + settings)
├── keyboards.py             # Inline keyboards (model picker)
├── sample.env               # Template env file (copy to .env)
├── requirements.txt         # Python dependencies
├── handlers/
│   ├── commands.py          # /start /help /deep /web /search /status /reset
│   ├── messages.py          # Text, photo, document, album processing
│   └── callbacks.py         # Inline button callbacks
├── services/
│   └── deepseek_ai.py       # DeepSeek client wrapper (p2d-deepseek)
└── lib/
    └── __init__.py          # MarkdownV2 escape helper
```

---

## License

MIT
