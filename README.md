<div align="center">

<img src="https://img.shields.io/badge/DeepSeek-Telegram%20Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="DeepSeek Telegram Bot"/>

<br/><br/>

A powerful Telegram bot powered by **DeepSeek AI** — web search, image reading, document OCR, code generation, reasoning mode, and multi-turn conversations. No paid API key needed — just your browser auth token.

<br/>

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/pooraddyy/deepseek-bot)

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![PTB](https://img.shields.io/badge/python--telegram--bot-22.x-blue?style=flat-square)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat-square&logo=mongodb&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

</div>

---

## Features

| Capability | Details |
|---|---|
| **Chat** | Multi-turn conversation with full memory per user |
| **Web Search** | Real-time web results via `/search` toggle or `/web` one-off |
| **Thinking Mode** | DeepSeek chain-of-thought reasoning via `/think` |
| **Image Reading** | Send any photo — bot describes, analyses, or answers questions |
| **Document OCR** | Upload PDFs, Word docs, Excel sheets, code files, CSVs |
| **Code Generation** | Ask for code in any language — generates, explains, debugs |
| **Album Support** | Send multiple photos or documents at once — all processed together |
| **Persistent Settings** | Model, thinking, and search toggle saved per user in MongoDB |

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
| `/help` | Show all commands with formatting |
| `/deep` | Switch between Flash and Pro |
| `/think` | Toggle DeepSeek reasoning mode on / off |
| `/web <query>` | One-off forced web search |
| `/search` | Toggle web search on / off for all messages |
| `/status` | Show current model, thinking, and search state |
| `/reset` | Clear conversation history |

---

## Getting your DeepSeek AUTH\_TOKEN

This bot uses [p2d-deepseek](https://github.com/pooraddyy/deepseek-free) — a free unofficial client that uses your **browser session token**. No API subscription required.

### Method 1 — LocalStorage (Fastest, Desktop)

1. Go to [chat.deepseek.com](https://chat.deepseek.com) and log in
2. Press `F12` → **Application** tab → **Local Storage** → `https://chat.deepseek.com`
3. Find the key `userToken` and copy its value

### Method 2 — Network Tab (Desktop)

1. Go to [chat.deepseek.com](https://chat.deepseek.com) and log in
2. Open DevTools → **Network** tab → send any message
3. Click any request to `chat.deepseek.com` → **Headers** → copy the `authorization` value (without `Bearer `)

### Method 3 — Kiwi Browser (Android)

1. Install [Kiwi Browser](https://play.google.com/store/apps/details?id=com.kiwibrowser.browser)
2. Open [chat.deepseek.com](https://chat.deepseek.com) and log in
3. Menu (⋮) → **Developer Tools** → **Application** → **Local Storage**
4. Find `userToken` and copy the value

> Token expired? Just repeat any method above after logging back in.

---

## Deploy

### Run Locally

```bash
git clone https://github.com/pooraddyy/deepseek-bot.git
cd deepseek-bot
pip install -r requirements.txt
cp sample.env .env
# Fill in .env, then:
python main.py
```

### Docker

```bash
git clone https://github.com/pooraddyy/deepseek-bot.git
cd deepseek-bot
cp sample.env .env
# Fill in .env, then:
docker build -t deepseek-bot .
docker run --env-file .env deepseek-bot
```

### Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/pooraddyy/deepseek-bot)

1. Click the button above
2. Set the environment variables: `BOT_TOKEN`, `AUTH_TOKEN`, `MONGODB_URL`
3. Click **Deploy**

### Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/pooraddyy/deepseek-bot)

1. Click **Deploy on Railway**
2. Add environment variables in the Railway dashboard
3. Railway auto-detects Python and runs `python main.py`

### Heroku

```bash
git clone https://github.com/pooraddyy/deepseek-bot.git
cd deepseek-bot
heroku create your-bot-name
heroku config:set BOT_TOKEN=... AUTH_TOKEN=... MONGODB_URL=...
echo "worker: python main.py" > Procfile
git add Procfile && git commit -m "add Procfile"
git push heroku main
heroku ps:scale worker=1
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Telegram Bot Token from [@BotFather](https://t.me/BotFather) |
| `AUTH_TOKEN` | ✅ | DeepSeek browser auth token (see above — free, no API key) |
| `MONGODB_URL` | ✅ | MongoDB Atlas connection string |
| `PORT` | ❌ | Health check port (default: `8000`) |

Copy `sample.env` to `.env` and fill in the values.

---

## Built with

- [p2d-deepseek](https://github.com/pooraddyy/deepseek-free) — free unofficial DeepSeek Python client
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) v22
- [Motor](https://motor.readthedocs.io/) — async MongoDB driver
- [aiohttp](https://docs.aiohttp.org/) — health check server

---

## License

MIT
