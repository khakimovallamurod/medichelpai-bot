from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass
class BotConfig:
    bot_token: str
    gemini_api_key: str
    admin_ids: set[int]


def _parse_admins(raw_admins: str) -> set[int]:
    admin_ids: set[int] = set()
    for admin_id in raw_admins.split(','):
        admin_id = admin_id.strip()
        if admin_id.isdigit():
            admin_ids.add(int(admin_id))
    return admin_ids


def load_config() -> BotConfig:
    load_dotenv()

    bot_token = (os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TOKEN') or '').strip()
    gemini_api_key = (os.getenv('GEMINI_API_KEY') or '').strip()
    admin_ids = _parse_admins(os.getenv('ADMINS', ''))

    if not bot_token:
        raise ValueError('TELEGRAM_BOT_TOKEN (or TOKEN) is not set in .env')

    if not gemini_api_key:
        raise ValueError('GEMINI_API_KEY is not set in .env')

    return BotConfig(
        bot_token=bot_token,
        gemini_api_key=gemini_api_key,
        admin_ids=admin_ids,
    )
