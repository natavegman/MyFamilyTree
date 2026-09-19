"""Yandex Cloud Vision OCR API client.

Docs: https://aistudio.yandex.ru/docs/ru/vision/concepts/ocr/
"""

import base64
import os
from collections import defaultdict
from pathlib import Path

import requests

from app.services.metric_layout import (
    MARRIAGE_COLUMN_BOUNDARIES,
    CellRegion,
    build_cell_grid,
    detect_row_bands,
)

YANDEX_OCR_URL = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"


def yandex_configured() -> bool:
    return bool(os.getenv("YANDEX_IAM_TOKEN") and os.getenv("YANDEX_FOLDER_ID"))


def _mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "JPEG"
    if suffix == ".png":
        return "PNG"
    return "JPEG"


def recognize_text(image_path: str | Path, model: str = "table") -> dict:
    iam_token = os.getenv("YANDEX_IAM_TOKEN")
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    if not iam_token or not folder_id:
        raise RuntimeError("Set YANDEX_IAM_TOKEN and YANDEX_FOLDER_ID in .env")

    path = Path(image_path)
    payload = {
        "mimeType": _mime_type(path),
        "languageCodes": ["ru"],
        "model": model,
        "content": base64.b64encode(path.read_bytes()).decode("utf-8"),
    }

    response = requests.post(
        YANDEX_OCR_URL,
        headers={
            "Authorization": f"Bearer {iam_token}",
            "x-folder-id": folder_id,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    return response.json()


def _bbox_center(bbox: dict) -> tuple[int, int] | None:
    vertices = bbox.get("vertices") if bbox else None
    if not vertices:
        return None
    xs = [int(v.get("x", 0)) for v in vertices]
    ys = [int(v.get("y", 0)) for v in vertices]
    return sum(xs) // len(xs), sum(ys) // len(ys)


def extract_lines(ocr_result: dict) -> list[dict]:
    """Extract text lines with center coordinates from Yandex OCR response."""
    lines_out: list[dict] = []
    annotation = ocr_result.get("result", {}).get("textAnnotation") or {}

    def add_line(line_obj: dict) -> None:
        words = line_obj.get("words") or []
        text = " ".join(w.get("text", "") for w in words if w.get("text")).strip()
        if not text:
            text = (line_obj.get("text") or "").strip()
        if not text:
            return

        bbox = line_obj.get("boundingBox")
        if not bbox and words:
            bbox = words[0].get("boundingBox")
        center = _bbox_center(bbox) if bbox else None
        if center is None:
            return
        lines_out.append({"text": text, "x": center[0], "y": center[1]})

    for block in annotation.get("blocks", []):
        for line in block.get("lines", []):
            add_line(line)

    for page in annotation.get("pages", []):
        for block in page.get("blocks", []):
            for line in block.get("lines", []):
                add_line(line)

    lines_out.sort(key=lambda item: (item["y"], item["x"]))
    return lines_out


def column_for_x(x: int, width: int) -> str | None:
    ratio = x / width
    for name, start, end in MARRIAGE_COLUMN_BOUNDARIES:
        if start <= ratio < end:
            return name
    return None


def row_for_y(y: int, height: int) -> int | None:
    for band in detect_row_bands(height):
        if band.y1 <= y < band.y2:
            return band.index
    return None


def lines_to_cell_texts(
    lines: list[dict], width: int, height: int
) -> list[tuple[CellRegion, str]]:
    """Map OCR lines to table cells using bounding-box coordinates."""
    grouped: dict[tuple[int, str], list[str]] = defaultdict(list)

    for line in lines:
        col = column_for_x(line["x"], width)
        row = row_for_y(line["y"], height)
        if col is None or row is None:
            continue
        grouped[(row, col)].append(line["text"])

    cell_texts: list[tuple[CellRegion, str]] = []
    for cell in build_cell_grid(width, height):
        parts = grouped.get((cell.row_index, cell.column), [])
        cell_texts.append((cell, " ".join(parts)))
    return cell_texts


def lines_to_plain_text(lines: list[dict]) -> str:
    return "\n".join(line["text"] for line in lines)
