from datetime import datetime

from pydantic import BaseModel


class PersonOut(BaseModel):
    id: str
    full_name: str
    birth_date: str | None = None
    death_date: str | None = None

    class Config:
        from_attributes = True


class ImportGedcomRequest(BaseModel):
    file_path: str


class ImportGedcomResponse(BaseModel):
    imported_count: int


class DocumentOut(BaseModel):
    id: str
    file_name: str
    file_path: str
    ocr_text: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentsImportResponse(BaseModel):
    imported: int


class DocumentOcrResponse(BaseModel):
    document_id: str
    ocr_text: str


class MetricParseResponse(BaseModel):
    document_id: str
    parse_type: str
    record_count: int
    header_year: dict | None = None
    records: list[dict]
    ocr_text: str
