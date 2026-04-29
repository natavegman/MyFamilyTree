from fastapi import FastAPI
from sqlalchemy import text

from app.api.documents import router as documents_router
from app.api.import_gedcom import router as import_router
from app.api.persons import router as persons_router
from app.database import Base, engine

app = FastAPI(title="MyFamilyTree API", version="0.1.0")

# Recreate schema on each start for deterministic MVP imports.
with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS document_links CASCADE"))
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

app.include_router(import_router)
app.include_router(persons_router)
app.include_router(documents_router)
