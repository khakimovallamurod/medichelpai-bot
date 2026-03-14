import asyncio
import json
import os
import re
import tempfile
from contextlib import suppress

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import BotConfig
from gemini_service import GeminiServiceError, build_structured_note, transcribe_audio
from keyboards import (
    BTN_CREATE_ROUTING,
    BTN_HELP,
    BTN_HISTORY,
    BTN_LANGUAGE,
    home_keyboard,
)

WAIT_ROUTING_INPUT = 1


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if not update.message:
        return

    await update.message.reply_text(
        text='Assalomu alaykum! Kerakli bo\'limni tanlang:',
        reply_markup=home_keyboard(),
    )


async def routing_entry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    del context
    if update.message:
        await update.message.reply_text(
            'Audio yoki matn yuboring. Faqat 1 ta xabar qabul qilinadi.'
        )
    return WAIT_ROUTING_INPUT


async def routing_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END

    config: BotConfig = context.application.bot_data['config']

    processing_msg = await update.message.reply_text('Qayta ishlash jarayonida...')

    temp_audio_path: str | None = None
    try:
        source_text = ''

        if update.message.voice or update.message.audio or (
            update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith('audio/')
        ):
            temp_audio_path = await _download_audio_to_temp(update, context)
            source_text = await asyncio.to_thread(transcribe_audio, config.gemini_api_key, temp_audio_path)
        elif update.message.text:
            source_text = update.message.text.strip()
        else:
            await update.message.reply_text('Faqat audio yoki matn yuborishingiz mumkin.')
            return ConversationHandler.END

        result_json = await asyncio.to_thread(build_structured_note, config.gemini_api_key, source_text)
        result_text = json.dumps(result_json, ensure_ascii=False, indent=2)

        with suppress(BadRequest):
            await processing_msg.delete()

        await update.message.reply_text(result_text)
    except GeminiServiceError as exc:
        with suppress(BadRequest):
            await processing_msg.delete()
        await update.message.reply_text(f'Gemini xatosi: {exc}')
    except Exception as exc:  # noqa: BLE001
        with suppress(BadRequest):
            await processing_msg.delete()
        await update.message.reply_text(f'Xatolik yuz berdi: {exc}')
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            with suppress(OSError):
                os.remove(temp_audio_path)

    return ConversationHandler.END


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.message:
        await update.message.reply_text('Yordam bo\'limi hozircha tayyorlanmoqda.')


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.message:
        await update.message.reply_text('Tarix bo\'limi hozircha tayyorlanmoqda.')


async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.message:
        await update.message.reply_text('Tilni sozlash bo\'limi hozircha tayyorlanmoqda.')


async def _download_audio_to_temp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if not update.message:
        raise RuntimeError('Message not found')

    suffix = '.ogg'
    file_id = ''

    if update.message.voice:
        file_id = update.message.voice.file_id
        suffix = '.ogg'
    elif update.message.audio:
        file_id = update.message.audio.file_id
        if update.message.audio.file_name and '.' in update.message.audio.file_name:
            suffix = '.' + update.message.audio.file_name.rsplit('.', 1)[1]
    elif update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith('audio/'):
        file_id = update.message.document.file_id
        if update.message.document.file_name and '.' in update.message.document.file_name:
            suffix = '.' + update.message.document.file_name.rsplit('.', 1)[1]

    if not file_id:
        raise RuntimeError('Audio file_id topilmadi')

    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)

    tg_file = await context.bot.get_file(file_id)
    await tg_file.download_to_drive(custom_path=temp_path)

    return temp_path


def register_handlers(application: Application, config: BotConfig) -> None:
    application.bot_data['config'] = config

    application.add_handler(CommandHandler('start', start_handler))

    text_filter = filters.TEXT & ~filters.COMMAND
    audio_or_text_filter = (
        filters.TEXT
        | filters.VOICE
        | filters.AUDIO
        | filters.Document.AUDIO
    )

    routing_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                text_filter & filters.Regex(f'^{re.escape(BTN_CREATE_ROUTING)}$'),
                routing_entry_handler,
            )
        ],
        states={
            WAIT_ROUTING_INPUT: [
                MessageHandler(audio_or_text_filter, routing_input_handler),
            ]
        },
        fallbacks=[CommandHandler('start', start_handler)],
        allow_reentry=True,
    )

    application.add_handler(routing_conversation)
    application.add_handler(
        MessageHandler(text_filter & filters.Regex(f'^{re.escape(BTN_HELP)}$'), help_handler)
    )
    application.add_handler(
        MessageHandler(text_filter & filters.Regex(f'^{re.escape(BTN_HISTORY)}$'), history_handler)
    )
    application.add_handler(
        MessageHandler(text_filter & filters.Regex(f'^{re.escape(BTN_LANGUAGE)}$'), language_handler)
    )
