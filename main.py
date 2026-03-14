from telegram.ext import Application

from admin_bot import register_admin_handlers
from config import load_config
from handlears import register_handlers


def main() -> None:
    config = load_config()

    application = Application.builder().token(config.bot_token).build()

    register_handlers(application, config)
    register_admin_handlers(application, config)

    application.run_polling()


if __name__ == '__main__':
    main()
