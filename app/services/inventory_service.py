from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import InventoryItem, MenuItem


def required_ingredients(menu_items_qty: list[tuple[MenuItem, int]]) -> dict[int, float]:
    """Total inventory needed (inventory_item_id -> amount) for a list of (menu item, qty)."""
    needed: dict[int, float] = defaultdict(float)
    for item, qty in menu_items_qty:
        for ing in item.recipe:
            needed[ing.inventory_item_id] += ing.quantity_required * qty
    return needed


def check_and_deduct(db: Session, needed: dict[int, float]) -> None:
    """Verify there is enough stock for everything, then deduct it.

    Does NOT commit - the caller commits so the whole order is one transaction.
    """
    if not needed:
        return
    stock = {
        i.id: i
        for i in db.scalars(select(InventoryItem).where(InventoryItem.id.in_(needed.keys())))
    }
    shortages = [
        f"{stock[i].name} (need {amt:g}, have {stock[i].quantity:g} {stock[i].unit})"
        for i, amt in needed.items()
        if stock[i].quantity < amt
    ]
    if shortages:
        raise HTTPException(409, "Insufficient stock: " + "; ".join(shortages))
    for i, amt in needed.items():
        stock[i].quantity -= amt


def restore(db: Session, needed: dict[int, float]) -> None:
    """Put stock back (e.g. when an order is cancelled). Caller commits."""
    for i, amt in needed.items():
        item = db.get(InventoryItem, i)
        if item:
            item.quantity += amt


def low_stock_items(db: Session) -> list[InventoryItem]:
    return list(
        db.scalars(
            select(InventoryItem)
            .where(InventoryItem.quantity <= InventoryItem.reorder_level)
            .order_by(InventoryItem.name)
        )
    )
