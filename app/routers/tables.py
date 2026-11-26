from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Reservation, ReservationStatus, Table
from app.schema.schemas import TableCreate, TableOut, TableUpdate
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


@router.patch("/{table_id}", response_model=TableOut, dependencies=[Depends(require_admin)])
def update_table(table_id: int, data: TableUpdate, db: Session = Depends(get_db)):
    """Activate/deactivate a table. Confirmed reservations prevent deactivation."""
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(404, "Table not found")

    if table.is_active and not data.is_active:
        now = datetime.now()
        has_reservation = db.scalar(
            select(Reservation.id).where(
                Reservation.table_id == table_id,
                Reservation.status == ReservationStatus.CONFIRMED,
                Reservation.end_time > now,
            )
        )
        if has_reservation:
            raise HTTPException(
                409,
                "This table has a confirmed reservation. Cancel or move the reservation before taking the table out of service.",
            )

    table.is_active = data.is_active
    db.commit()
    db.refresh(table)
    return table
