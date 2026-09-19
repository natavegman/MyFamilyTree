import os
import re
from functools import lru_cache
from pathlib import Path

REFUSAL_PATTERN = re.compile(
    r"(не могу|извините|нет видимого|размыт|can't help|cannot help|I'm sorry)",
    re.IGNORECASE,
)

CELL_OCR_PROMPT = """Перепиши ТОЛЬКО видимый текст на этом фрагменте архивного документа.
Это одна ячейка таблицы метрической книги.
Не выдумывай. Нечитаемое: [???].
Верни только текст, без JSON и без комментариев."""


def _clean_ocr_text(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned or REFUSAL_PATTERN.search(cleaned):
        return ""
    return cleaned


def _ocr_openai(image_path: str | Path) -> str:
    import base64
    import mimetypes

    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    path = Path(image_path)
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_OCR_MODEL", "gpt-4o")

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": CELL_OCR_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Транскрибируй ячейку."},
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
    return _clean_ocr_text(response.choices[0].message.content or "")


@lru_cache(maxsize=1)
def _paddle_available() -> bool:
    try:
        import paddleocr  # noqa: F401

        return True
    except ImportError:
        return False


def _ocr_paddle(image_path: str | Path) -> str:
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(use_angle_cls=True, lang="ru", show_log=False)
    result = ocr.ocr(str(image_path), cls=True)
    if not result or not result[0]:
        return ""
    lines = [str(block[1][0]).strip() for block in result[0] if block and block[1][0]]
    return _clean_ocr_text("\n".join(lines))


def ocr_image(image_path: str | Path) -> str:
    """OCR single image crop (used in legacy per-cell pipeline)."""
    path = str(image_path)
    engine = os.getenv("METRIC_OCR_ENGINE", "auto").lower()

    if engine == "yandex":
        from app.services.yandex_vision_ocr import extract_lines, recognize_text, lines_to_plain_text

        model = os.getenv("YANDEX_CELL_MODEL", "handwritten")
        result = recognize_text(path, model=model)
        return lines_to_plain_text(extract_lines(result))

    if engine == "paddle" or (engine == "auto" and _paddle_available()):
        try:
            return _ocr_paddle(path)
        except Exception:
            if engine == "paddle":
                raise

    return _ocr_openai(path)


def ocr_year_from_header(header_text: str) -> dict | None:
    match = re.search(r"(19\d{2})", header_text)
    if not match:
        return None
    return {
        "value": match.group(1),
        "confidence": "medium",
        "source_fragment": header_text.strip()[:200],
    }
