import datetime as dt
import uuid

from sqlalchemy import ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Call(Base):
    __tablename__ = "calls"

    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    happyrobot_call_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.order_id"), nullable=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.customer_id"), nullable=True)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    agent_type: Mapped[str] = mapped_column(Text, nullable=False)
    caller_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(Text, nullable=False, default="not_started")
    intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    disposition: Mapped[str | None] = mapped_column(Text, nullable=True)
    csat_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[dt.datetime] = mapped_column(nullable=False)
    ended_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("idx_calls_order_id", "order_id"),
        Index("idx_calls_started_at", "started_at"),
    )
