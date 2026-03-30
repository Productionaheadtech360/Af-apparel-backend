"""Inventory models: Warehouse, InventoryRecord, InventoryAdjustment."""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.product import ProductVariant
    from app.models.user import User


class Warehouse(BaseModel):
    __tablename__ = "warehouses"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    address_line1: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(2), default="US", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    inventory_records: Mapped[list["InventoryRecord"]] = relationship(
        "InventoryRecord", back_populates="warehouse", cascade="all, delete-orphan"
    )


class InventoryRecord(BaseModel):
    """Current stock quantity for a specific variant at a specific warehouse."""

    __tablename__ = "inventory"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    variant: Mapped["ProductVariant"] = relationship("ProductVariant", back_populates="inventory_records")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="inventory_records")
    adjustments: Mapped[list["InventoryAdjustment"]] = relationship(
        "InventoryAdjustment", back_populates="inventory_record", cascade="all, delete-orphan"
    )


class InventoryAdjustment(BaseModel):
    """Audit trail for every stock change."""

    __tablename__ = "inventory_adjustments"

    inventory_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    adjusted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    quantity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    # Reason: received | damaged | returned | correction | sold | migration
    reason: Mapped[str] = mapped_column(
        Enum("received", "damaged", "returned", "correction", "sold", "migration",
             name="adjustment_reason"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)

    inventory_record: Mapped["InventoryRecord"] = relationship(
        "InventoryRecord", back_populates="adjustments"
    )
    adjusted_by: Mapped["User | None"] = relationship("User")
