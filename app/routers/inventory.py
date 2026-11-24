from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import InventoryItem
from app.schema.schemas import InventoryItemCreate, InventoryItemOut, RestockIn
from app.security import require_admin, require_staff
from app.services import inventory_service

# Staff can view and restock inventory; creating inventory records is admin-only.
router = APIRouter(prefix="/inventory", tags=["Inventory"], dependencies=[Depends(require_staff)])


@router.get("", response_model=list[InventoryItemOut])
def list_inventory(db: Session = Depends(get_db)):
    return db.scalars(select(InventoryItem).order_by(InventoryItem.name)).all()


@router.get("/low-stock", response_model=list[InventoryItemOut])
def low_stock(db: Session = Depends(get_db)):
    return inventory_service.low_stock_items(db)


@router.post("", response_model=InventoryItemOut, status_code=201, dependencies=[Depends(require_admin)])
def create_inventory_item(data: InventoryItemCreate, db: Session = Depends(get_db)):
    item = InventoryItem(**data.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Inventory item already exists")
    db.refresh(item)
    return item


@router.patch("/{item_id}/restock", response_model=InventoryItemOut)
def restock(item_id: int, data: RestockIn, db: Session = Depends(get_db)):
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(404, "Inventory item not found")
    item.quantity += data.quantity
    db.commit()
    db.refresh(item)
    return item
