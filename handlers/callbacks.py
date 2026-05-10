from telegram import Update
from telegram.ext import ContextTypes

from . import state, db
from config import DEEPSEEK_MODELS


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid   = update.effective_user.id
    s     = state.get(uid)
    data  = query.data
    if data.startswith("set_model:"):
        model_id = data.split(":", 1)[1]
        if model_id in DEEPSEEK_MODELS:
            s["model"] = model_id
            label = DEEPSEEK_MODELS[model_id]
            await db.save_state(uid, s)
            await query.answer(f"Switched to DeepSeek {label}", show_alert=False)
            await query.message.delete()
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"Model set to DeepSeek {label}",
            )
        else:
            await query.answer("Unknown model.", show_alert=False)
            await query.message.delete()
    else:
        await query.answer()
