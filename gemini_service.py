import json
import re
from typing import Any

from google import genai

MODEL_CANDIDATES = (
    'gemini-3-flash-preview',
    'gemini-2.5-flash',
)

TRANSCRIBE_PROMPT = (
    'Siz tibbiy audio transkriptorisiz. '
    'Audio ichidagi gaplarni aynan matnga aylantiring. '
    'Faqat transkriptni qaytaring, izoh yoki qo\'shimcha yozmang.'
)

STRUCTURE_PROMPT_TEMPLATE = '''
Quyidagi shifokor diktovka matnidan tayyor kuzatuv kundaligi tuzing.
Javob faqat JSON bo'lsin. JSON ichida aynan quyidagi 6 ta kalit bo'lsin:
1) "audio_text"
2) "shikoyatlar"
3) "obyektiv_status"
4) "lokal_status_ogriqsizlantirish"
5) "holat_dinamikasi"
6) "buyruqlar_tavsiyalar"

Talablar:
- "buyruqlar_tavsiyalar" qiymati ro'yxat (array) bo'lsin.
- Tibbiy uslubda, lo'nda va aniq yozing.
- Matnda yo'q ma'lumotni to'qimang.
- JSON tashqarisida hech narsa yozmang.

Diktovka matni:
{source_text}
'''


class GeminiServiceError(RuntimeError):
    pass



def _generate_with_fallback(client: genai.Client, contents: Any) -> str:
    last_error: Exception | None = None

    for model_name in MODEL_CANDIDATES:
        try:
            response = client.models.generate_content(model=model_name, contents=contents)
            if response.text:
                return response.text
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if last_error:
        raise GeminiServiceError(f'Gemini generate_content failed: {last_error}') from last_error
    raise GeminiServiceError('Gemini generate_content failed: empty response')



def _extract_json(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{.*\}', text, flags=re.DOTALL)
    if not match:
        raise GeminiServiceError('Gemini JSON response not found')

    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise GeminiServiceError('Gemini JSON parse failed') from exc

    if not isinstance(parsed, dict):
        raise GeminiServiceError('Gemini JSON must be an object')

    return parsed



def transcribe_audio(api_key: str, audio_path: str) -> str:
    client = genai.Client(api_key=api_key)

    uploaded_file = client.files.upload(file=audio_path)
    transcript = _generate_with_fallback(client, [TRANSCRIBE_PROMPT, uploaded_file]).strip()

    if not transcript:
        raise GeminiServiceError('Audio transcript is empty')

    return transcript



def build_structured_note(api_key: str, source_text: str) -> dict[str, Any]:
    client = genai.Client(api_key=api_key)

    prompt = STRUCTURE_PROMPT_TEMPLATE.format(source_text=source_text)
    raw_response = _generate_with_fallback(client, prompt)
    data = _extract_json(raw_response)

    data.setdefault('audio_text', source_text)
    data.setdefault('shikoyatlar', '')
    data.setdefault('obyektiv_status', '')
    data.setdefault('lokal_status_ogriqsizlantirish', '')
    data.setdefault('holat_dinamikasi', '')
    data.setdefault('buyruqlar_tavsiyalar', [])

    if not isinstance(data['buyruqlar_tavsiyalar'], list):
        data['buyruqlar_tavsiyalar'] = [str(data['buyruqlar_tavsiyalar'])]

    return data
