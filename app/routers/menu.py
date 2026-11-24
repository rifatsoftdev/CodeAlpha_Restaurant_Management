from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import InventoryItem, MenuItem, RecipeIngredient
from app.schema.schemas import MenuItemCreate, MenuItemOut, MenuItemUpdate, RecipeIngredientIn
from app.security import require_admin

router = APIRouter(prefix="/menu", tags=["Menu"])


@router.get("", response_model=list[MenuItemOut])
def list_menu(category: str | None = None, only_available: bool = True, db: Session = Depends(get_db)):
    query = select(MenuItem).order_by(MenuItem.category, MenuItem.name)
    if category:
        query = query.where(MenuItem.category == category)
    if only_available:
        query = query.where(MenuItem.is_available.is_(True))
    return db.scalars(query).all()


@router.get("/{item_id}", response_model=MenuItemOut)
def get_menu_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(MenuItem, item_id)
    if not item:
        raise HTTPException(404, "Menu item not found")
    return item


@router.post("", response_model=MenuItemOut, status_code=201, dependencies=[Depends(require_admin)])
def create_menu_item(data: MenuItemCreate, db: Session = Depends(get_db)):
    item = MenuItem(**data.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A menu item with that name already exists")
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=MenuItemOut, dependencies=[Depends(require_admin)])
def update_menu_item(item_id: int, data: MenuItemUpdate, db: Session = Depends(get_db)):
    item = db.get(MenuItem, item_id)
    if not item:
        raise HTTPException(404, "Menu item not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_menu_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(MenuItem, item_id)
    if not item:
        raise HTTPException(404, "Menu item not found")
    db.delete(item)
    try:
        db.commit()
    except IntegrityError:  # already used in past orders
        db.rollback()
        raise HTTPException(409, "Item is used in orders; set is_available=false instead")


@router.put("/{item_id}/recipe", response_model=MenuItemOut, dependencies=[Depends(require_admin)])
def set_recipe(item_id: int, ingredients: list[RecipeIngredientIn], db: Session = Depends(get_db)):
    """Define which inventory items (and how much) one portion consumes."""
    item = db.get(MenuItem, item_id)
    if not item:
        raise HTTPException(404, "Menu item not found")
    for ing in ingredients:
        if not db.get(InventoryItem, ing.inventory_item_id):
            raise HTTPException(404, f"Inventory item {ing.inventory_item_id} not found")
    item.recipe = [RecipeIngredient(**ing.model_dump()) for ing in ingredients]
    db.commit()
    db.refresh(item)
    return item
