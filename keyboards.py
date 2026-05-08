from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import DEEPSEEK_MODELS, DUCK_CHAT_MODELS


def deepseek_picker_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(label, callback_data=f"set_model:deepseek:{mid}")
        for mid, label in DEEPSEEK_MODELS.items()
    ]
    return InlineKeyboardMarkup([buttons])


def duck_picker_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(label, callback_data=f"set_model:duck:{mid}")
        for mid, label in DUCK_CHAT_MODELS.items()
    ]
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


def effort_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⚡ Fast",       callback_data="set_effort:fast"),
        InlineKeyboardButton("🧠 Reasoning",  callback_data="set_effort:reasoning"),
    ]])
