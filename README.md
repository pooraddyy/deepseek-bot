<div align="center">

<img src="https://img.shields.io/badge/MultiGPT_AI-Telegram_Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="MultiGPT AI" />

<br/>

**MultiGPT AI** — A powerful Telegram bot that unifies DeepSeek AI and DuckDuckGo AI (Duck.ai) into one interface. No separate apps, no switching — just one bot for everything.

<br/>

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/pooraddyy/multigpt)

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/python--telegram--bot-21.x-blue?style=flat-square)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat-square&logo=mongodb&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

</div>

---

## ✨ Features

| Feature | Details |
|---|---|
| 🤖 **8 AI Models** | DeepSeek Flash & Pro + GPT-4o Mini, GPT-5 Mini, Claude Haiku, Llama 4, Mistral, GPT-OSS 120B |
| 🎨 **Image Generation** | Generate images from text prompts via Duck.ai |
| ✏️ **Image Editing** | Edit any image with a text instruction |
| 🔍 **Web Search** | Force real-time web search on any query |
| 🧠 **Reasoning Mode** | Switch between Fast ⚡ and Reasoning 🧠 modes for supported models |
| 💾 **Persistent State** | Your model preference and settings saved to MongoDB |
| 📎 **File & Photo Support** | Send images or documents and ask questions about them |
| 🖼️ **Album Support** | Send multiple images at once |
| ✍️ **MarkdownV2 Rendering** | Bold, code blocks, math, and more |
| ⚡ **Auto-delete Commands** | All command messages vanish in 0.1s for a clean chat |

---

## 🤖 Commands

### Model Selection

| Command | Description |
|---|---|
| `/deep` | Pick a **DeepSeek** model (Flash / Pro) |
| `/duck` | Pick a **Duck AI** model (6 models) |
| `/mode` | Switch between ⚡ Fast and 🧠 Reasoning for supported models |

### Actions

| Command | Description |
|---|---|
| `/web <query>` | Search the web and get an AI answer |
| `/img_gen <prompt>` | Generate an image from a text description |
| `/img_edit <caption>` | Edit a photo — send with a photo or reply to one |

### Utility

| Command | Description |
|---|---|
| `/start` | Start the bot and restore your saved settings |
| `/status` | Show current model, provider, and session info |
| `/reset` | Clear conversation history and start fresh |

---

## 🧠 Available Models

### DeepSeek (via p2d-deepseek)

| Alias | Label |
|---|---|
| `deepseek-v4-flash` | ⚡ Flash — fast responses |
| `deepseek-v4-pro` | 🧠 Pro — deep reasoning |

### Duck AI (via p2d-duck · no API key needed)

| Alias | Model | Reasoning? | Web Search? |
|---|---|---|---|
| `gpt4` | GPT-4o Mini | ❌ | ✅ |
| `gpt5_mini` | GPT-5 Mini | ✅ | ✅ |
| `claude` | Claude Haiku 4.5 | ✅ | ✅ |
| `llama` | Llama 4 Scout | ❌ | ❌ |
| `mistral` | Mistral Small | ❌ | ❌ |
| `gpt-oss` | GPT-OSS 120B | ✅ | ❌ |

---

## 🚀 Deploy

### Option 1 — Render (Recommended)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/pooraddyy/multigpt)

1. Click the button above
2. Fill in the environment variables (see table below)
3. Click **Deploy**

### Option 2 — Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/pooraddyy/multigpt)

### Option 3 — Run Locally

```bash
git clone https://github.com/pooraddyy/multigpt.git
cd multigpt
pip install -r requirements.txt
python main.py
```

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Telegram Bot Token from [@BotFather](https://t.me/BotFather) |
| `AUTH_TOKEN` | ✅ | DeepSeek API key from [platform.deepseek.com](https://platform.deepseek.com) |
| `MONGODB_URL` | ✅ | MongoDB Atlas connection string |
| `PORT` | ❌ | HTTP health check port (default: `8000`) |

Create a `.env` file:

```env
BOT_TOKEN=your_telegram_bot_token
AUTH_TOKEN=your_deepseek_api_key
MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/...
PORT=8000
```

---

## 🗂️ Project Structure

```
├── main.py              # Entry point — bot + health server
├── config.py            # Env var loading & model definitions
├── state.py             # In-memory per-user state
├── db.py                # MongoDB persistence (motor)
├── keyboards.py         # Inline keyboard builders
├── handlers/
│   ├── commands.py      # All slash command handlers
│   ├── messages.py      # Text, photo, document, album routing
│   └── callbacks.py     # Inline button callbacks
├── services/
│   ├── deepseek_ai.py   # DeepSeek API wrapper
│   └── duck_service.py  # Duck AI wrapper (chat, image gen/edit)
├── lib/
│   └── __init__.py      # p2dmd markdown helper
├── render.yaml          # Render deployment config
└── requirements.txt
```

---

## 📦 Requirements

- Python 3.11+
- MongoDB Atlas (free tier works)
- DeepSeek API key
- Telegram Bot Token

---

## 📄 License

MIT
