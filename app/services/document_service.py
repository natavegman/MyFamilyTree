from sqlalchemy.orm import Session

from app.models import Document
from app.services.metric_book_service import parse_metric_book
from app.services.ocr import recognize_text


def get_documents(db: Session) -> list[Document]:
    return db.query(Document).order_by(Document.created_at.desc()).all()


def get_document_by_id(document_id: str, db: Session) -> Document | None:
    return db.query(Document).filter(Document.id == document_id).first()


def run_ocr(document_id: str, db: Session) -> Document:
    document = get_document_by_id(document_id, db)
    if document is None:
        raise ValueError("Document not found")

    ocr_text = recognize_text(document.file_path)
    document.ocr_text = ocr_text
    db.commit()
    db.refresh(document)
    return document


def run_metric_parse(document_id: str, db: Session) -> Document:
    document = get_document_by_id(document_id, db)
    if document is None:
        raise ValueError("Document not found")

    parsed = parse_metric_book(document.file_path)
    document.ocr_text = parsed
    db.commit()
    db.refresh(document)
    return document
