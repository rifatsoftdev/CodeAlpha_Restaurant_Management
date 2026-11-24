from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Order, OrderStatus
from app.security import require_staff
from app.schema.schemas import OrderCreate, OrderOut, OrderStatusUpdate
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["Orders"], dependencies=[Depends(require_staff)])


@router.post("", response_model=OrderOut, status_code=201)
def place_order(data: OrderCreate, db: Session = Depends(get_db)):
    return order_service.place_order(db, data)


@router.get("", response_model=list[OrderOut])
def list_orders(status: OrderStatus | None = None, db: Session = Depends(get_db)):
    query = select(Order).order_by(Order.created_at.desc())
    if status:
        query = query.where(Order.status == status)
    return db.scalars(query).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(order_id: int, data: OrderStatusUpdate, db: Session = Depends(get_db)):
    return order_service.update_status(db, order_id, data.status)
