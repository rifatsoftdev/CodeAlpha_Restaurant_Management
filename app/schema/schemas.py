from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.models import OrderStatus, ReservationStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Inventory ----------
class InventoryItemCreate(BaseModel):
    name: str
    unit: str = "kg"
    quantity: float = Field(0, ge=0)
    reorder_level: float = Field(0, ge=0)


class InventoryItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    quantity: float | None = Field(default=None, ge=0)
    reorder_level: float | None = Field(default=None, ge=0)

    @field_validator("name", "unit")
    @classmethod
    def trim_inventory_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_inventory_patch(self):
        null_fields = [field for field in self.model_fields_set if getattr(self, field) is None]
        if null_fields:
            raise ValueError(f"Fields cannot be null: {', '.join(sorted(null_fields))}")
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        return self


class InventoryItemOut(ORMModel, InventoryItemCreate):
    id: int


class RestockIn(BaseModel):
    quantity: float = Field(gt=0)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# ---------- Menu ----------
class RecipeIngredientIn(BaseModel):
    inventory_item_id: int
    quantity_required: float = Field(gt=0)


class RecipeIngredientOut(ORMModel, RecipeIngredientIn):
    pass


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    price: float = Field(gt=0)
    category: str = Field(default="main", min_length=1, max_length=50)
    is_available: bool = True

    @field_validator("name", "category")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    price: float | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    is_available: bool | None = None

    @field_validator("name", "category")
    @classmethod
    def trim_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_patch_fields(self):
        required_fields = {"name", "price", "category", "is_available"}
        null_fields = [field for field in required_fields if field in self.model_fields_set and getattr(self, field) is None]
        if null_fields:
            raise ValueError(f"Fields cannot be null: {', '.join(sorted(null_fields))}")
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        return self


class MenuItemOut(ORMModel, MenuItemCreate):
    id: int
    recipe: list[RecipeIngredientOut] = []


# ---------- Tables ----------
class TableCreate(BaseModel):
    number: int = Field(gt=0)
    capacity: int = Field(gt=0)


class TableUpdate(BaseModel):
    is_active: bool


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
