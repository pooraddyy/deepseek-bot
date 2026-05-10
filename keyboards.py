from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import KeyboardButtonStyle


def deepseek_picker_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🔵 Flash",
            callback_data="set_model:deepseek-v4-flash",
            style=KeyboardButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            "🔴 Pro",
            callback_data="set_model:deepseek-v4-pro",
            style=KeyboardButtonStyle.DANGER,
        ),
    ]])
