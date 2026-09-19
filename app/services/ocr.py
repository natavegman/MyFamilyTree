import base64
import json
import mimetypes
import os
from pathlib import Path

from openai import OpenAI

from app.services.image_preprocess import crop_header, preprocess_for_ocr
from app.services.ocr_postprocess import minimal_postprocess

TRANSCRIPTION_PROMPT = """Ты — консервативный транскрибатор рукописных архивных сканов (генеалогия).

Твоя задача — ТОЛЬКО переписать видимый текст. Не интерпретировать. Не достраивать.

ЖЁСТКИЕ ЗАПРЕТЫ:
- Запрещено подставлять типовые имена (Иван Иванов, Мария Петрова, Петр Сидоров и т.п.), если их НЕТ на изображении.
- Запрещено угадывать цифры года. Если цифра сомнительна — «190[?]» или «19[??]».
- Запрещено объединять строки из разных колонок в одну.
- Запрещено дописывать фамилии, отчества, губернии по шаблону метрики.

КАК ЧИТАТЬ:
- Построчно, сверху вниз, слева направо.
- Каждый элемент raw_transcription_lines = одна визуальная строка таблицы или шапки.
- Нечитаемо: [???]. Сомнительная буква: [?].
- Цифры года в шапке читай ПО ЦИФРАМ (2 и 3 часто путают).

Верни ТОЛЬКО JSON:
{
  "raw_transcription_lines": ["..."],
  "uncertain_fragments": [
    {"fragment": "...", "reason": "...", "confidence": "low"}
  ],
  "reading_limitations": ["..."]
}"""

HEADER_YEAR_PROMPT = """На изображении — только верхняя шапка метрической книги.
Найди год после «НА ... ГОДЪ». Читай каждую цифру отдельно.
2 и 3 часто путают — будь осторожен.

Верни ТОЛЬКО JSON:
{
  "year": "1902",
  "raw_fragment": "фрагмент текста с годом",
  "confidence": "high|medium|low",
  "note": "если цифра сомнительна — опиши"
}

Если год не читается — year: null. Не угадывай."""


def _mime_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "image/jpeg"


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def _model() -> str:
    return os.getenv("OPENAI_OCR_MODEL", "gpt-4o")


def _parse_json_response(raw: str | None, finish_reason: str | None = None) -> dict:
    text = (raw or "").strip()
    if not text:
        raise ValueError("OpenAI returned empty OCR response")
    if finish_reason == "length":
        raise ValueError("OpenAI response was truncated (max_tokens)")
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON from OpenAI: {exc}") from exc


def _vision_json(client: OpenAI, system: str, user_text: str, image_path: Path) -> dict:
    mime = _mime_type(image_path)
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    response = client.chat.completions.create(
        model=_model(),
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=8192,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{encoded}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
    )
    choice = response.choices[0]
    return _parse_json_response(choice.message.content, choice.finish_reason)


def _read_header_year(client: OpenAI, source_path: Path) -> dict | None:
    header_path = crop_header(str(source_path))
    try:
        return _vision_json(
            client,
            HEADER_YEAR_PROMPT,
            "Прочитай год в шапке. Только год, без догадок.",
            header_path,
        )
    finally:
        if header_path.exists():
            header_path.unlink()


def _transcribe_page(client: OpenAI, image_path: Path) -> dict:
    return _vision_json(
        client,
        TRANSCRIPTION_PROMPT,
        "Транскрибируй весь видимый текст. Не выдумывай имена и даты.",
        image_path,
    )


def recognize_text(image_path: str) -> str:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    preprocessed_path = preprocess_for_ocr(str(path))
    client = _client()

    try:
        header = _read_header_year(client, path)
        transcription = _transcribe_page(client, preprocessed_path)

        result = {
            "document_type": None,
            "document_type_confidence": "unknown",
            "header_year": header,
            "raw_transcription_lines": transcription.get("raw_transcription_lines") or [],
            "uncertain_fragments": transcription.get("uncertain_fragments") or [],
            "reading_limitations": transcription.get("reading_limitations") or [],
            "dates": [],
            "persons": [],
            "locations": [],
            "disclaimer": (
                "persons/dates/locations извлекаются только из raw_transcription_lines; "
                "проверяйте транскрипцию вручную"
            ),
        }
        result = minimal_postprocess(result)
        return json.dumps(result, ensure_ascii=False, indent=2)
    finally:
        if preprocessed_path.exists():
            preprocessed_path.unlink()
