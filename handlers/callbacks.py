import asyncio
from telegram import Update
from telegram.ext import ContextTypes
import state
import db
from config import DEEPSEEK_MODELS, DUCK_CHAT_MODELS, DUCK_EFFORT_MODELS


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid   = update.effective_user.id
    s     = state.get(uid)
    data  = query.data

    if data.startswith("set_model:"):
        _, provider, model_id = data.split(":", 2)
        if provider == "deepseek" and model_id in DEEPSEEK_MODELS:
            s["provider"] = "deepseek"
            s["model"]    = model_id
            label = DEEPSEEK_MODELS[model_id]
            await query.answer(f"Switched to DeepSeek {label}", show_alert=False)
        elif provider == "duck" and model_id in DUCK_CHAT_MODELS:
            s["provider"] = "duck"
            s["model"]    = model_id
            label = DUCK_CHAT_MODELS[model_id]
            await query.answer(f"Switched to {label}", show_alert=False)
        else:
            await query.answer("Unknown model.", show_alert=False)
            await query.message.delete()
            return

        await db.save_state(uid, s)
        await query.message.delete()

        text = f"✅ Model set to {label}"
        if provider == "duck" and model_id in DUCK_EFFORT_MODELS:
            text += f"\n\nThis model supports ⚡ Fast / 🧠 Reasoning — use /mode to switch."
        await context.bot.send_message(chat_id=query.message.chat_id, text=text)

    elif data.startswith("set_effort:"):
        effort = data.split(":", 1)[1]
        s["effort"] = effort
        await db.save_state(uid, s)
        label = "⚡ Fast" if effort == "fast" else "🧠 Reasoning"
        await query.answer(f"Mode set to {label}", show_alert=False)
        await query.message.delete()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"✅ Mode set to {label}",
        )

    else:
        await query.answer()
