from telegram import KeyboardButton, ReplyKeyboardMarkup

BTN_CREATE_ROUTING = '🛣️ Ruting yaratish'
BTN_HELP = '🆘 Yordam'
BTN_HISTORY = '📜 Tarix'
BTN_LANGUAGE = '🌐 Tilni sozlash'


def home_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(text=BTN_CREATE_ROUTING),
                KeyboardButton(text=BTN_HELP),
            ],
            [
                KeyboardButton(text=BTN_HISTORY),
                KeyboardButton(text=BTN_LANGUAGE),
            ],
        ],
        resize_keyboard=True,
    )
