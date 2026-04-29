from fastapi import APIRouter

from app.services.gedcom_import import import_gedcom

router = APIRouter()


@router.post("/import-gedcom", tags=["import"])
def import_data():
    count = import_gedcom("data/tree.ged")
    return {"imported": count}
