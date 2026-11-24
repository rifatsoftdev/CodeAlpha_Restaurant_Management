from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Reservation, ReservationStatus, Table
from app.schema.schemas import ReservationCreate


def is_table_free(db: Session, table_id: int, start: datetime, end: datetime) -> bool:
    """A table is free if no confirmed reservation overlaps [start, end)."""
    clash = db.scalar(
        select(Reservation.id).where(
            Reservation.table_id == table_id,
            Reservation.status == ReservationStatus.CONFIRMED,
            Reservation.start_time < end,
            Reservation.end_time > start,
        )
    )
    return clash is None


def available_tables(db: Session, start: datetime, end: datetime, party_size: int = 1) -> list[Table]:
    tables = db.scalars(
        select(Table)
        .where(Table.is_active.is_(True), Table.capacity >= party_size)
        .order_by(Table.capacity, Table.number)
    )
    return [t for t in tables if is_table_free(db, t.id, start, end)]


def create_reservation(db: Session, data: ReservationCreate) -> Reservation:
    end = data.start_time + timedelta(minutes=data.duration_minutes)

    if data.table_id is not None:
        table = db.get(Table, data.table_id)
        if not table or not table.is_active:
            raise HTTPException(404, "Table not found")
        if table.capacity < data.party_size:
            raise HTTPException(400, f"Table {table.number} seats only {table.capacity}")
        if not is_table_free(db, table.id, data.start_time, end):
            raise HTTPException(409, "Table is already reserved for that time")
    else:  # auto-assign the smallest table that fits
        free = available_tables(db, data.start_time, end, data.party_size)
        if not free:
            raise HTTPException(409, "No table available for that time and party size")
        table = free[0]

    reservation = Reservation(
        table_id=table.id,
        customer_name=data.customer_name,
        phone=data.phone,
        party_size=data.party_size,
        start_time=data.start_time,
        end_time=end,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation
