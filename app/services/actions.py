import datetime as dt
import uuid
from typing import TypeVar

from sqlalchemy.orm import Session

from app.models import (
    AddressFlag,
    Escalation,
    FallbackMessage,
    Investigation,
    MerchantReferral,
    Order,
    Reschedule,
)

T = TypeVar("T")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _get_existing(db: Session, model: type[T], call_id: uuid.UUID) -> T | None:
    return db.query(model).filter_by(call_id=call_id).one_or_none()


def create_reschedule(db: Session, call_id: uuid.UUID, order_id: uuid.UUID,
                      requested_date: dt.date, requested_window: str | None, reason: str | None) -> Reschedule:
    existing = _get_existing(db, Reschedule, call_id)
    if existing:
        return existing
    row = Reschedule(call_id=call_id, order_id=order_id, requested_date=requested_date,
                     requested_window=requested_window, reason=reason, status="requested", created_at=_now())
    db.add(row)
    db.flush()
    return row


def create_investigation(db: Session, call_id: uuid.UUID, order_id: uuid.UUID, type_: str) -> Investigation:
    existing = _get_existing(db, Investigation, call_id)
    if existing:
        return existing
    row = Investigation(call_id=call_id, order_id=order_id, type=type_, status="open",
                        callback_due_at=_now() + dt.timedelta(hours=24), opened_at=_now())
    db.add(row)
    db.flush()
    return row


def create_merchant_referral(db: Session, call_id: uuid.UUID, order_id: uuid.UUID, reason: str | None) -> MerchantReferral:
    existing = _get_existing(db, MerchantReferral, call_id)
    if existing:
        return existing
    row = MerchantReferral(call_id=call_id, order_id=order_id, reason=reason, status="open", created_at=_now())
    db.add(row)
    db.flush()
    return row


def create_address_flag(db: Session, call_id: uuid.UUID, order: Order, correction_text: str) -> AddressFlag:
    existing = _get_existing(db, AddressFlag, call_id)
    if existing:
        return existing
    row = AddressFlag(call_id=call_id, order_id=order.order_id, original_address=order.delivery_address,
                      correction_text=correction_text, status="pending", created_at=_now())
    db.add(row)
    db.flush()
    return row


def create_escalation(db: Session, call_id: uuid.UUID, order_id: uuid.UUID | None,
                      category: str, reason: str | None) -> Escalation:
    existing = _get_existing(db, Escalation, call_id)
    if existing:
        return existing
    row = Escalation(call_id=call_id, order_id=order_id, category=category, reason=reason,
                     status="open", created_at=_now())
    db.add(row)
    db.flush()
    return row


def create_fallback_message(db: Session, call_id: uuid.UUID, order_id: uuid.UUID,
                            channel: str, content_type: str) -> FallbackMessage:
    # Not one-per-call (multiple follow-ups allowed). content_type is constrained by the schema.
    row = FallbackMessage(call_id=call_id, order_id=order_id, channel=channel,
                          content_type=content_type, status="queued")
    db.add(row)
    db.flush()
    return row
