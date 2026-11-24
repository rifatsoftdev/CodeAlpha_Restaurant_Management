from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import MenuItem, Order, OrderItem, OrderStatus
from app.schema.schemas import InventoryItemOut
from app.security import require_admin
from app.services import inventory_service

router = APIRouter(prefix="/reports", tags=["Reports"], dependencies=[Depends(require_admin)])


@router.get("/daily-sales")
def daily_sales(day: date | None = None, db: Session = Depends(get_db)):
    """Revenue, order count and best sellers for one day (cancelled orders excluded)."""
    day = day or date.today()
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    in_day = (Order.created_at >= start, Order.created_at < end, Order.status != OrderStatus.CANCELLED)

    orders, revenue = db.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.total_amount), 0)).where(*in_day)
    ).one()

    top = db.execute(
        select(MenuItem.name, func.sum(OrderItem.quantity).label("qty"))
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(*in_day)
        .group_by(MenuItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    ).all()

    return {
        "date": day.isoformat(),
        "total_orders": orders,
        "total_revenue": round(revenue, 2),
        "top_items": [{"name": n, "quantity_sold": q} for n, q in top],
    }


@router.get("/stock-alerts", response_model=list[InventoryItemOut])
def stock_alerts(db: Session = Depends(get_db)):
    return inventory_service.low_stock_items(db)
