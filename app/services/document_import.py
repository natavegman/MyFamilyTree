import hashlib
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import Document

STORAGE_DIR = Path("storage/documents")
ALLOWED_EXTENSIONS = {".jpg", ".png"}


def get_file_hash(path: Path) -> str:
    md5 = hashlib.md5()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            md5.update(chunk)
    return md5.hexdigest()


def import_documents_from_folder(folder_path: str) -> int:
    source_dir = Path(folder_path)
    if not source_dir.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    imported = 0
    db = SessionLocal()
    try:
        for file_path in source_dir.iterdir():
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue

            file_hash = get_file_hash(file_path)
            existing = db.query(Document).filter_by(file_hash=file_hash).first()
            if existing:
                continue

            target_name = f"{uuid.uuid4()}{file_path.suffix.lower()}"
            target_path = STORAGE_DIR / target_name
            shutil.copy2(file_path, target_path)

            db.add(
                Document(
                    file_name=file_path.name,
                    file_path=str(target_path),
                    file_hash=file_hash,
                    created_at=datetime.utcnow(),
                )
            )
            try:
                db.commit()
                imported += 1
            except IntegrityError:
                db.rollback()
                if target_path.exists():
                    target_path.unlink()
        return imported
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
