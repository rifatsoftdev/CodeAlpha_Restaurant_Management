from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import MenuItem, Order, OrderItem, OrderStatus, Table
from app.schema.schemas import OrderCreate
from app.services import inventory_service

# Allowed status transitions
TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.SERVED, OrderStatus.CANCELLED},
    OrderStatus.SERVED: {OrderStatus.PAID},
    OrderStatus.PAID: set(),
    OrderStatus.CANCELLED: set(),
}


def place_order(db: Session, data: OrderCreate) -> Order:
    """Validate -> check stock -> deduct stock -> save order (single transaction)."""
    if data.table_id is not None and not db.get(Table, data.table_id):
        raise HTTPException(404, f"Table {data.table_id} not found")

    order = Order(table_id=data.table_id, notes=data.notes)
    lines: list[tuple[MenuItem, int]] = []
    total = 0.0

    for line in data.items:
        menu_item = db.get(MenuItem, line.menu_item_id)
        if not menu_item:
            raise HTTPException(404, f"Menu item {line.menu_item_id} not found")
        if not menu_item.is_available:
            raise HTTPException(409, f"'{menu_item.name}' is currently unavailable")
        lines.append((menu_item, line.quantity))
        total += menu_item.price * line.quantity
        order.items.append(
            OrderItem(menu_item_id=menu_item.id, quantity=line.quantity, unit_price=menu_item.price)
        )

    needed = inventory_service.required_ingredients(lines)
    inventory_service.check_and_deduct(db, needed)  # raises 409 if not enough stock

    order.total_amount = round(total, 2)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def update_status(db: Session, order_id: int, new_status: OrderStatus) -> Order:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if new_status not in TRANSITIONS[order.status]:
        raise HTTPException(409, f"Cannot move order from '{order.status.value}' to '{new_status.value}'")

    if new_status == OrderStatus.CANCELLED:  # give the ingredients back
        lines = [(db.get(MenuItem, oi.menu_item_id), oi.quantity) for oi in order.items]
        inventory_service.restore(db, inventory_service.required_ingredients(lines))

    order.status = new_status
    db.commit()
    db.refresh(order)
    return order
