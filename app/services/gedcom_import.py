from pathlib import Path
from tempfile import NamedTemporaryFile

from gedcom.element.individual import IndividualElement
from gedcom.parser import Parser
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Person

DEFAULT_GEDCOM_FILE_PATH = "data/tree.ged"


def _extract_event_date(individual: IndividualElement, event_tag: str) -> str | None:
    for child in individual.get_child_elements():
        if child.get_tag() != event_tag:
            continue
        for event_child in child.get_child_elements():
            if event_child.get_tag() == "DATE":
                return event_child.get_value()
    return None


def _extract_full_name(individual: IndividualElement) -> str:
    # `python-gedcom` usually keeps a normalized name in this helper.
    name = individual.get_name()
    if isinstance(name, tuple):
        given, surname = name
        return " ".join(part for part in (given, surname) if part).strip()
    if name:
        return name
    return individual.get_pointer()


def _decode_gedcom_bytes(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, "Unable to decode GEDCOM file")


def _normalize_gedcom_text(text: str) -> str:
    normalized = text.lstrip("\ufeff")
    if normalized.startswith("ï»¿"):
        normalized = normalized.removeprefix("ï»¿")
    return normalized


def import_gedcom(file_path: str = DEFAULT_GEDCOM_FILE_PATH, db: Session | None = None) -> int:
    path = Path(file_path)
    if not path.is_absolute():
        app_root = Path(__file__).resolve().parent.parent
        path = app_root / file_path
    if not path.exists():
        raise FileNotFoundError(f"GEDCOM file not found: {path}")

    parser = Parser()
    raw_content = path.read_bytes()
    decoded_content = _normalize_gedcom_text(_decode_gedcom_bytes(raw_content))

    with NamedTemporaryFile("w", encoding="utf-8", suffix=".ged", delete=True) as temp_file:
        temp_file.write(decoded_content)
        temp_file.flush()
        parser.parse_file(temp_file.name, strict=False)

    imported_count = 0
    own_session = db is None
    session = db or SessionLocal()

    try:
        for individual in parser.get_element_list():
            if not isinstance(individual, IndividualElement):
                continue
            pointer = individual.get_pointer()
            full_name = _extract_full_name(individual)
            birth_date = _extract_event_date(individual, "BIRT")
            death_date = _extract_event_date(individual, "DEAT")

            session.merge(
                Person(
                    id=pointer,
                    full_name=full_name,
                    birth_date=birth_date,
                    death_date=death_date,
                )
            )
            imported_count += 1

        session.commit()
        return imported_count
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()
