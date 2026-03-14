# medichelpai-bot

## .env

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
ADMINS=123456789
```

## Run

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Routing Flow

1. `/start` -> `🛣️ Ruting yaratish`
2. Bot `audio yoki matn` so'raydi.
3. Faqat bitta xabar qabul qiladi.
4. `Qayta ishlash jarayonida...` xabari chiqadi.
5. Gemini orqali transkript + 5 bo'limli JSON qaytadi.
