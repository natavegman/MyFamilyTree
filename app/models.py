import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.database import Base


class Person(Base):
    __tablename__ = "persons"

    id = Column(String, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    birth_date = Column(String, nullable=True)
    death_date = Column(String, nullable=True)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, unique=True, index=True)
    ocr_text = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
