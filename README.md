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

## Metric book OCR (Yandex Vision)

Recommended engine for archive scans: [Yandex Vision OCR](https://aistudio.yandex.ru/docs/ru/vision/concepts/ocr/).

1. Create a folder in [Yandex Cloud](https://cloud.yandex.ru/) and enable Vision OCR.
2. Create a service account with role `ai.vision.user`, get IAM token.
3. Copy `.env.example` → `.env` and set:

```env
METRIC_OCR_ENGINE=yandex
YANDEX_IAM_TOKEN=<IAM-token>
YANDEX_FOLDER_ID=<folder-id>
YANDEX_OCR_MODEL=table
YANDEX_HEADER_MODEL=page
```

4. `POST /documents/{id}/parse-metric` — one API call to Yandex (`table` model) + header (`page` model).

Models: `table` for spreads, `handwritten` for difficult cells, `page` for header year.

## Notes

- In current MVP schema is recreated on startup (see `app/main.py`) for deterministic test imports.
- Do not commit generated DB files or secrets.

