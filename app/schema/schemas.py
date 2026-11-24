from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import OrderStatus, ReservationStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Inventory ----------
class InventoryItemCreate(BaseModel):
    name: str
    unit: str = "kg"
    quantity: float = Field(0, ge=0)
    reorder_level: float = Field(0, ge=0)


class InventoryItemOut(ORMModel, InventoryItemCreate):
    id: int


class RestockIn(BaseModel):
    quantity: float = Field(gt=0)


# ---------- Menu ----------
class RecipeIngredientIn(BaseModel):
    inventory_item_id: int
    quantity_required: float = Field(gt=0)


class RecipeIngredientOut(ORMModel, RecipeIngredientIn):
    pass


class MenuItemCreate(BaseModel):
    name: str
    description: str | None = None
    price: float = Field(gt=0)
    category: str = "main"
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = Field(default=None, gt=0)
    category: str | None = None
    is_available: bool | None = None


class MenuItemOut(ORMModel, MenuItemCreate):
    id: int
    recipe: list[RecipeIngredientOut] = []


# ---------- Tables ----------
class TableCreate(BaseModel):
    number: int = Field(gt=0)
    capacity: int = Field(gt=0)


class TableOut(ORMModel, TableCreate):
    id: int
    is_active: bool


# ---------- Reservations ----------
class ReservationCreate(BaseModel):
    customer_name: str
    phone: str | None = None
    party_size: int = Field(gt=0)
    start_time: datetime
    duration_minutes: int = Field(90, gt=0, le=480)
    table_id: int | None = None  # omit to auto-assign the smallest suitable table


class ReservationOut(ORMModel):
    id: int
    table_id: int
    customer_name: str
    phone: str | None
    party_size: int
    start_time: datetime
    end_time: datetime
    status: ReservationStatus


# ---------- Orders ----------
class OrderItemIn(BaseModel):
    menu_item_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    table_id: int | None = None
    notes: str | None = None
    items: list[OrderItemIn] = Field(min_length=1)


class OrderItemOut(ORMModel):
    menu_item_id: int
    quantity: int
    unit_price: float


class OrderOut(ORMModel):
    id: int
    table_id: int | None
    status: OrderStatus
    notes: str | None
    total_amount: float
    created_at: datetime
    items: list[OrderItemOut]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
