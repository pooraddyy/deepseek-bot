from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def deepseek_picker_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("DeepSeek Flash", callback_data="set_model:deepseek-v4-flash"),
        InlineKeyboardButton("DeepSeek Pro",   callback_data="set_model:deepseek-v4-pro"),
    ]])
