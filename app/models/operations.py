import datetime as dt
import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Verification(Base):
    __tablename__ = "verifications"
    verification_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.call_id"), nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.order_id"), nullable=True)
    factors_checked: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    factors_passed: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_no: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(nullable=False)


class Reschedule(Base):
    __tablename__ = "reschedules"
    reschedule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.call_id"), nullable=False, unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    requested_date: Mapped[dt.date] = mapped_column(nullable=False)
    requested_window: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="requested")
    synced_to_twin_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(nullable=False)


class Investigation(Base):
    __tablename__ = "investigations"
    investigation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.call_id"), nullable=False, unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    callback_due_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    opened_at: Mapped[dt.datetime] = mapped_column(nullable=False)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(Text, nullable=True)


class Escalation(Base):
    __tablename__ = "escalations"
    escalation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.call_id"), nullable=False, unique=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.order_id"), nullable=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    assigned_to: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(nullable=False)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)


class AddressFlag(Base):
    __tablename__ = "address_flags"
    flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.call_id"), nullable=False, unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    original_address: Mapped[str] = mapped_column(Text, nullable=False)
    correction_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    created_at: Mapped[dt.datetime] = mapped_column(nullable=False)


class FallbackMessage(Base):
    __tablename__ = "fallback_messages"
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("calls.call_id"), nullable=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    sent_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)


class MerchantReferral(Base):
    __tablename__ = "merchant_referrals"
    referral_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.call_id"), nullable=False, unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    created_at: Mapped[dt.datetime] = mapped_column(nullable=False)
