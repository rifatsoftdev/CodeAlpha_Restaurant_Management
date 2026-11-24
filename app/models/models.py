import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    SERVED = "served"
    PAID = "paid"
    CANCELLED = "cancelled"


class ReservationStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20), default="staff")
    is_active: Mapped[bool] = mapped_column(default=True)


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    price: Mapped[float]  # use Numeric(10, 2) if you move to PostgreSQL
    category: Mapped[str] = mapped_column(String(50), default="main")
    is_available: Mapped[bool] = mapped_column(default=True)

    recipe: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="menu_item", cascade="all, delete-orphan"
    )


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    unit: Mapped[str] = mapped_column(String(20), default="kg")
    quantity: Mapped[float] = mapped_column(default=0)
    reorder_level: Mapped[float] = mapped_column(default=0)  # low-stock threshold


class RecipeIngredient(Base):
    """Links a menu item to the inventory it consumes (per 1 portion)."""

    __tablename__ = "recipe_ingredients"
    __table_args__ = (UniqueConstraint("menu_item_id", "inventory_item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    inventory_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id"))
    quantity_required: Mapped[float]

    menu_item: Mapped["MenuItem"] = relationship(back_populates="recipe")
    inventory_item: Mapped["InventoryItem"] = relationship()


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(unique=True)
    capacity: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"))
    customer_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(30))
    party_size: Mapped[int]
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus), default=ReservationStatus.CONFIRMED
    )

    table: Mapped["Table"] = relationship()


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int | None] = mapped_column(ForeignKey("tables.id"))
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING)
    notes: Mapped[str | None] = mapped_column(String(255))
    total_amount: Mapped[float] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    quantity: Mapped[int]
    unit_price: Mapped[float]  # price snapshot at the time of ordering

    order: Mapped["Order"] = relationship(back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship()
