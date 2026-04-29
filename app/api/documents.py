from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DocumentOut, DocumentsImportResponse
from app.services.document_import import import_documents_from_folder
from app.services.document_service import (
    get_document_by_id,
    get_documents as list_documents,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/import-folder", response_model=DocumentsImportResponse)
def import_documents_folder():
    try:
        imported = import_documents_from_folder("data/scans")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}") from exc
    return DocumentsImportResponse(imported=imported)


@router.get("", response_model=list[DocumentOut])
def get_documents(db: Session = Depends(get_db)):
    return list_documents(db)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)):
    document = get_document_by_id(document_id, db)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
