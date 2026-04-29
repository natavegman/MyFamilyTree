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
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentsImportResponse(BaseModel):
    imported: int
