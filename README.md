# MyFamilyTree API

Backend service for importing and browsing genealogy data (GEDCOM + document links) via REST API.

## Task

Build a compact API to:

- import family trees from GEDCOM;
- store people and relationships in SQL;
- attach and retrieve related documents.

## Tech stack

- Python, FastAPI, Uvicorn
- SQLAlchemy
- PostgreSQL (Docker Compose)
- python-gedcom

## Functional blocks

- `app/api/import_gedcom.py` - GEDCOM import endpoint.
- `app/api/persons.py` - people query endpoints.
- `app/api/documents.py` - document linkage endpoints.
- `app/services/*` - parsing/import business logic.
- `app/database.py` + `app/models.py` - DB layer.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d
uvicorn app.main:app --reload --port 8000
```

Open docs: `http://localhost:8000/docs`

## Notes

- In current MVP schema is recreated on startup (see `app/main.py`) for deterministic test imports.
- Do not commit generated DB files or secrets.

