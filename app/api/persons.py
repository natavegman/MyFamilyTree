from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Person
from app.schemas import PersonOut

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("", response_model=list[PersonOut])
def get_persons(search: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Person)
    if search:
        query = query.filter(Person.full_name.ilike(f"%{search}%"))
    return query.order_by(Person.full_name.asc()).all()


@router.get("/{person_id}", response_model=PersonOut)
def get_person(person_id: str, db: Session = Depends(get_db)):
    person = db.query(Person).filter(Person.id == person_id).first()
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person
