from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Reservation, ReservationStatus
from app.schema.schemas import ReservationCreate, ReservationOut
from app.services import table_service
from app.security import require_staff

router = APIRouter(prefix="/reservations", tags=["Reservations"], dependencies=[Depends(require_staff)])


@router.post("", response_model=ReservationOut, status_code=201)
def reserve_table(data: ReservationCreate, db: Session = Depends(get_db)):
    return table_service.create_reservation(db, data)


@router.get("", response_model=list[ReservationOut])
def list_reservations(status: ReservationStatus | None = None, db: Session = Depends(get_db)):
    query = select(Reservation).order_by(Reservation.start_time)
    if status:
        query = query.where(Reservation.status == status)
    return db.scalars(query).all()


@router.get("/{reservation_id}", response_model=ReservationOut)
def get_reservation(reservation_id: int, db: Session = Depends(get_db)):
    res = db.get(Reservation, reservation_id)
    if not res:
        raise HTTPException(404, "Reservation not found")
    return res


@router.delete("/{reservation_id}", response_model=ReservationOut)
def cancel_reservation(reservation_id: int, db: Session = Depends(get_db)):
    res = db.get(Reservation, reservation_id)
    if not res:
        raise HTTPException(404, "Reservation not found")
    res.status = ReservationStatus.CANCELLED
    db.commit()
    db.refresh(res)
    return res
