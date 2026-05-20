import time
from typing import Any

from google import genai

MODEL_CANDIDATES = (
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite',
    'gemini-3-flash-preview',
)

TRANSCRIBE_PROMPT = (
    'Siz tibbiy audio transkriptorisiz. '
    'Audio ichidagi gaplarni aynan matnga aylantiring. '
    'Faqat transkriptni qaytaring, izoh yoki qo\'shimcha yozmang.'
)

STRUCTURE_PROMPT_TEMPLATE = '''
SEN PROFESSIONAL TIBBIY AI ASSISTENTSAN.
Foydalanuvchi audio, text yoki fayl yuboradi.
Sening vazifang:
- Bemor ma'lumotlarini tahlil qilish
- Professional tibbiy xulosa yozish
- Telegram va Word uchun bitta umumiy matn tayyorlash

MUHIM:
- Faqat bitta response qaytar.
- JSON ishlatma.
- Javob oddiy, toza matn bo'lsin.
- Javobda **, #, ##, ``` kabi markdown belgilar bo'lmasin.
- Noma'lum ma'lumotlarni to'qib yozma.
- Yetarli ma'lumot bo'lmasa: "Aniqlashtirish talab etiladi" deb yoz.
- Juda qisqa yozma. Har bir klinik bo'lim batafsil bo'lsin.
- 1-5 bo'limlarning har biri kamida 4-6 ta mazmunli gapdan iborat bo'lsin.
- Tibbiy terminlar, ehtimoliy sabablar, kuzatuv dinamikasi va amaliy tavsiyalar keng yoritilsin.
- Matn professional shifokor yozuviga o'xshasin.

QO'SHIMCHA TALABLAR:
- Audio yuborilsa speech-to-text qilingan deb hisobla.
- Tibbiy terminlardan foydalan.
- Xavfli simptom bo'lsa ogohlantirish yoz.
- Dori tavsiya qilinsa: "Faqat shifokor nazorati ostida" deb yoz.
- Yakuniy diagnoz qo'yma.
- Taxminiy klinik holat yoz.

CHIqarish formati (bitta umumiy matn):
QISQA XULOSA
F.I.Sh: ...
Tug'ilgan yil / jinsi: ...
SHIFOXONA NOMI
Tibbiy ko'rik varaqasi
Sana: __.__.20__
BEMOR HAQIDA MA'LUMOT
1. SHIKOYATI: ...
2. OBYEKTIV STATUSI: ...
3. LOKAL STATUS: ...
4. DINAMIKASI: ...
5. TAVSIYA: ...
Shifokor (F.I.Sh): ___________________
Shaxsiy imzo va muhr: ___________________

YOZISH TALABI:
- 1. SHIKOYATI bo'limida simptomlarning davomiyligi, xarakteri, qo'zg'atuvchi omillari, hamroh belgilarini batafsil bayon et.
- 2. OBYEKTIV STATUSI bo'limida umumiy ko'rik elementlarini klinik uslubda keng yoz.
- 3. LOKAL STATUS bo'limida lokal ko'rikdagi ehtimoliy belgilar va aniqlashtirilishi kerak nuqtalarni tushuntir.
- 4. DINAMIKASI bo'limida holat evolyutsiyasi, kuzatuv zarurati va monitoring rejimini yoz.
- 5. TAVSIYA bo'limida tekshiruvlar, mutaxassis konsultatsiyasi, red-flag belgilar va davolash tamoyillarini batafsil yoz.

KIRITILGAN MA'LUMOT:
{source_text}
'''


class GeminiServiceError(RuntimeError):
    pass



def _generate_with_fallback(client: genai.Client, contents: Any) -> str:
    last_error: Exception | None = None

    # High-demand periods can intermittently return 503. Retry each model
    # with small exponential backoff before moving to the next fallback model.
    for model_name in MODEL_CANDIDATES:
        for attempt in range(4):
            try:
                response = client.models.generate_content(model=model_name, contents=contents)
                if response.text:
                    return response.text
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                error_text = str(exc).upper()
                is_retryable = (
                    '503' in error_text
                    or 'UNAVAILABLE' in error_text
                    or 'RESOURCE_EXHAUSTED' in error_text
                    or 'TIMEOUT' in error_text
                )
                if not is_retryable or attempt == 3:
                    break
                time.sleep(1.5 * (2 ** attempt))

    if last_error:
        raise GeminiServiceError(f'Gemini generate_content failed: {last_error}') from last_error
    raise GeminiServiceError('Gemini generate_content failed: empty response')



def transcribe_audio(api_key: str, audio_path: str) -> str:
    client = genai.Client(api_key=api_key)

    uploaded_file = client.files.upload(file=audio_path)
    transcript = _generate_with_fallback(client, [TRANSCRIBE_PROMPT, uploaded_file]).strip()

    if not transcript:
        raise GeminiServiceError('Audio transcript is empty')

    return transcript



def build_structured_note(api_key: str, source_text: str) -> str:
    client = genai.Client(api_key=api_key)

    prompt = STRUCTURE_PROMPT_TEMPLATE.format(source_text=source_text)
    raw_response = _generate_with_fallback(client, prompt).strip()
    if not raw_response:
        raise GeminiServiceError('Gemini markdown response is empty')
    return raw_response
