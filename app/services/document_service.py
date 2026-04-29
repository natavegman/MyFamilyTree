from sqlalchemy.orm import Session

from app.models import Document


def get_documents(db: Session) -> list[Document]:
    return db.query(Document).order_by(Document.created_at.desc()).all()


def get_document_by_id(document_id: str, db: Session) -> Document | None:
    return db.query(Document).filter(Document.id == document_id).first()
