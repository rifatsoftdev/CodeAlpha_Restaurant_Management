from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Table
from app.schema.schemas import TableCreate, TableOut
from app.security import require_admin, require_staff
from app.services import table_service

router = APIRouter(prefix="/tables", tags=["Tables"], dependencies=[Depends(require_staff)])


@router.get("", response_model=list[TableOut])
def list_tables(db: Session = Depends(get_db)):
    return db.scalars(select(Table).order_by(Table.number)).all()


@router.get("/available", response_model=list[TableOut])
def check_availability(
    start_time: datetime,
    party_size: int = Query(1, gt=0),
    duration_minutes: int = Query(90, gt=0, le=480),
    db: Session = Depends(get_db),
):
    """Tables that are free (and big enough) for the requested time window."""
    end = start_time + timedelta(minutes=duration_minutes)
    return table_service.available_tables(db, start_time, end, party_size)


@router.post("", response_model=TableOut, status_code=201, dependencies=[Depends(require_admin)])
def create_table(data: TableCreate, db: Session = Depends(get_db)):
    table = Table(**data.model_dump())
    db.add(table)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Table number already exists")
    db.refresh(table)
    return table
