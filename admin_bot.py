from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters

from config import BotConfig


async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.message:
        await update.message.reply_text('Admin panelga xush kelibsiz.')


def register_admin_handlers(application: Application, config: BotConfig) -> None:
    if not config.admin_ids:
        return

    application.add_handler(
        CommandHandler(
            'admin',
            admin_panel_handler,
            filters=filters.User(user_id=list(config.admin_ids)),
        )
    )
