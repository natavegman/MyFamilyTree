import json
import os
from pathlib import Path

import cv2

from app.services.metric_layout import build_cell_grid
from app.services.metric_ocr import ocr_image, ocr_year_from_header
from app.services.metric_parser import assemble_records
from app.services.metric_preprocess import extract_cell_crops, extract_header_crop
from app.services.yandex_vision_ocr import (
    extract_lines,
    lines_to_cell_texts,
    lines_to_plain_text,
    recognize_text as yandex_recognize,
    yandex_configured,
)


def _parse_metric_book_cells(image_path: str) -> dict:
    """Legacy path: OpenAI/Paddle OCR per cell."""
    path = Path(image_path)
    temp_paths: list[Path] = []

    try:
        header_path = extract_header_crop(str(path))
        temp_paths.append(header_path)
        header_text = ocr_image(header_path)
        header_year = ocr_year_from_header(header_text)

        img = cv2.imread(str(path))
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")
        height, width = img.shape[:2]
        cells = build_cell_grid(width, height)

        cell_crops = extract_cell_crops(str(path), cells)
        temp_paths.extend(crop_path for _, crop_path in cell_crops)

        cell_texts = []
        for cell, crop_path in cell_crops:
            text = ocr_image(crop_path)
            cell_texts.append((cell, text))

        result = assemble_records(cell_texts, header_year)
        result["header_ocr"] = header_text
        result["ocr_engine"] = os.getenv("METRIC_OCR_ENGINE", "openai")
        return result
    finally:
        for temp_path in temp_paths:
            if temp_path.exists():
                temp_path.unlink()


def _parse_metric_book_yandex(image_path: str) -> dict:
    """Yandex Vision OCR: table model on full spread + page model on header."""
    path = Path(image_path)
    table_model = os.getenv("YANDEX_OCR_MODEL", "table")
    header_model = os.getenv("YANDEX_HEADER_MODEL", "page")

    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")
    height, width = img.shape[:2]

    header_path = extract_header_crop(str(path))
    try:
        header_result = yandex_recognize(header_path, model=header_model)
        header_lines = extract_lines(header_result)
        header_text = lines_to_plain_text(header_lines)
    finally:
        if header_path.exists():
            header_path.unlink()

    header_year = ocr_year_from_header(header_text)

    table_result = yandex_recognize(path, model=table_model)
    lines = extract_lines(table_result)
    cell_texts = lines_to_cell_texts(lines, width, height)

    result = assemble_records(cell_texts, header_year)
    result["header_ocr"] = header_text
    result["ocr_engine"] = "yandex_vision"
    result["ocr_model"] = table_model
    result["line_count"] = len(lines)
    result["raw_transcription_lines"] = [line["text"] for line in lines]
    return result


def parse_metric_book(image_path: str) -> str:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    engine = os.getenv("METRIC_OCR_ENGINE", "auto").lower()

    if engine == "yandex" or (engine == "auto" and yandex_configured()):
        result = _parse_metric_book_yandex(str(path))
    else:
        result = _parse_metric_book_cells(str(path))

    return json.dumps(result, ensure_ascii=False, indent=2)
