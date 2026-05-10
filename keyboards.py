from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import DEEPSEEK_MODELS


def deepseek_picker_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(label, callback_data=f"set_model:{mid}")
        for mid, label in DEEPSEEK_MODELS.items()
    ]
    return InlineKeyboardMarkup([buttons])
