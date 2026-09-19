import re
from dataclasses import asdict, dataclass

from app.services.metric_layout import CellRegion


@dataclass
class MetricRecord:
    record_number: str | None
    month_day: str | None
    groom: str | None
    groom_age: str | None
    bride: str | None
    bride_age: str | None
    clergy: str | None
    witnesses: str | None
    signature: str | None
    raw_cells: dict[str, str]


def _clean(text: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    return cleaned or None


def _extract_record_number(text: str | None, groom: str | None = None) -> str | None:
    if text:
        match = re.search(r"\b(\d{1,4})\b", text)
        if match:
            return match.group(1)
        cleaned = _clean(text)
        if cleaned and cleaned.isdigit():
            return cleaned

    if groom:
        match = re.match(r"^\s*(\d{1,3})\b", groom)
        if match:
            return match.group(1)
    return None


def _extract_age(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"\b(\d{1,2})\b", text)
    return match.group(1) if match else _clean(text)


def assemble_records(
    cell_texts: list[tuple[CellRegion, str]], header_year: dict | None
) -> dict:
    rows: dict[int, dict[str, str]] = {}
    for cell, text in cell_texts:
        rows.setdefault(cell.row_index, {})[cell.column] = text

    records: list[MetricRecord] = []
    for row_index in sorted(rows.keys()):
        cells = rows[row_index]
        if not any(cells.values()):
            continue
        groom_text = _clean(cells.get("groom"))
        record = MetricRecord(
            record_number=_extract_record_number(cells.get("record_number"), groom_text),
            month_day=_clean(cells.get("month_day")),
            groom=groom_text,
            groom_age=_extract_age(cells.get("groom_age")),
            bride=_clean(cells.get("bride")),
            bride_age=_extract_age(cells.get("bride_age")),
            clergy=_clean(cells.get("clergy")),
            witnesses=_clean(cells.get("witnesses")),
            signature=_clean(cells.get("signature")),
            raw_cells={key: value for key, value in cells.items() if value},
        )
        if record.record_number or record.groom or record.bride or record.clergy:
            records.append(record)

    return {
        "parse_type": "metric_book_marriage",
        "document_type": "Метрическая книга о бракосочетавшихся",
        "header_year": header_year,
        "records": [asdict(record) for record in records],
        "record_count": len(records),
    }
