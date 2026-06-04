import datetime as dt
import uuid

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    twin_customer_ref: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    primary_phone: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    alt_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    language_pref: Mapped[str | None] = mapped_column(String, nullable=True)
    last_synced_at: Mapped[dt.datetime] = mapped_column(nullable=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="customer")

    __table_args__ = (
        UniqueConstraint("primary_phone", name="uq_customers_primary_phone"),
        Index("idx_customers_primary_phone", "primary_phone"),
    )


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    twin_order_ref: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.customer_id"))
    merchant: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_address: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_area: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_window: Mapped[str | None] = mapped_column(Text, nullable=True)
    otp_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_driver: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_pieces: Mapped[int | None] = mapped_column(nullable=True)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
    delivered_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    sla_due_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    merchant_lat: Mapped[float | None] = mapped_column(nullable=True)
    merchant_lng: Mapped[float | None] = mapped_column(nullable=True)
    delivery_lat: Mapped[float | None] = mapped_column(nullable=True)
    delivery_lng: Mapped[float | None] = mapped_column(nullable=True)
    last_synced_at: Mapped[dt.datetime] = mapped_column(nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="orders")

    __table_args__ = (Index("idx_orders_customer_id", "customer_id"),)
