import datetime as dt
import uuid
from typing import TypeVar

from sqlalchemy.orm import Session

from app.models import (
    AddressFlag,
    Call,
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


class ActionSyncError(Exception):
    """Raised when an action-sync item references an order that doesn't exist."""


def _resolve_call_order(db: Session, happyrobot_call_id: str, twin_order_ref: str | None,
                        *, order_required: bool) -> tuple[Call, Order | None]:
    from app.services.calls import get_or_create_call

    call = get_or_create_call(db, happyrobot_call_id=happyrobot_call_id)
    order = None
    if twin_order_ref:
        order = db.query(Order).filter_by(twin_order_ref=twin_order_ref).one_or_none()
        if order is None:
            raise ActionSyncError(f"order '{twin_order_ref}' not found")
    if order_required and order is None:
        raise ActionSyncError("twin_order_ref is required")
    if order is not None and call.order_id is None:  # backfill the call's order link
        call.order_id = order.order_id
        call.customer_id = order.customer_id
    return call, order


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


def upsert_reschedules(db: Session, items) -> list[Reschedule]:
    out: list[Reschedule] = []
    for item in items:
        call, order = _resolve_call_order(db, item.happyrobot_call_id, item.twin_order_ref, order_required=True)
        row = _get_existing(db, Reschedule, call.call_id)
        if row is None:
            row = Reschedule(call_id=call.call_id, created_at=item.created_at or _now())
            db.add(row)
        row.order_id = order.order_id
        row.requested_date = item.requested_date
        row.requested_window = item.requested_window
        row.reason = item.reason
        row.status = item.status
        row.synced_to_twin_at = item.synced_to_twin_at
        if item.created_at:
            row.created_at = item.created_at
        db.flush()
        out.append(row)
    return out


def upsert_investigations(db: Session, items) -> list[Investigation]:
    out: list[Investigation] = []
    for item in items:
        call, order = _resolve_call_order(db, item.happyrobot_call_id, item.twin_order_ref, order_required=True)
        row = _get_existing(db, Investigation, call.call_id)
        if row is None:
            row = Investigation(call_id=call.call_id, opened_at=item.opened_at or _now())
            db.add(row)
        row.order_id = order.order_id
        row.type = item.type
        row.status = item.status
        row.callback_due_at = item.callback_due_at
        row.resolved_at = item.resolved_at
        row.resolution_notes = item.resolution_notes
        row.assigned_to = item.assigned_to
        if item.opened_at:
            row.opened_at = item.opened_at
        db.flush()
        out.append(row)
    return out


def upsert_escalations(db: Session, items) -> list[Escalation]:
    out: list[Escalation] = []
    for item in items:
        call, order = _resolve_call_order(db, item.happyrobot_call_id, item.twin_order_ref, order_required=False)
        row = _get_existing(db, Escalation, call.call_id)
        if row is None:
            row = Escalation(call_id=call.call_id, created_at=item.created_at or _now())
            db.add(row)
        row.order_id = order.order_id if order else None
        row.category = item.category
        row.reason = item.reason
        row.status = item.status
        row.assigned_to = item.assigned_to
        row.resolved_at = item.resolved_at
        if item.created_at:
            row.created_at = item.created_at
        db.flush()
        out.append(row)
    return out


def upsert_merchant_referrals(db: Session, items) -> list[MerchantReferral]:
    out: list[MerchantReferral] = []
    for item in items:
        call, order = _resolve_call_order(db, item.happyrobot_call_id, item.twin_order_ref, order_required=True)
        row = _get_existing(db, MerchantReferral, call.call_id)
        if row is None:
            row = MerchantReferral(call_id=call.call_id, created_at=item.created_at or _now())
            db.add(row)
        row.order_id = order.order_id
        row.reason = item.reason
        row.status = item.status
        if item.created_at:
            row.created_at = item.created_at
        db.flush()
        out.append(row)
    return out


def upsert_address_flags(db: Session, items) -> list[AddressFlag]:
    out: list[AddressFlag] = []
    for item in items:
        call, order = _resolve_call_order(db, item.happyrobot_call_id, item.twin_order_ref, order_required=True)
        row = _get_existing(db, AddressFlag, call.call_id)
        if row is None:
            row = AddressFlag(call_id=call.call_id, created_at=item.created_at or _now())
            db.add(row)
        row.order_id = order.order_id
        row.original_address = item.original_address or order.delivery_address
        row.correction_text = item.correction_text
        row.status = item.status
        if item.created_at:
            row.created_at = item.created_at
        db.flush()
        out.append(row)
    return out


def upsert_fallback_messages(db: Session, items) -> list[FallbackMessage]:
    """Keyed on (call_id, channel, content_type) — no per-message id exists, so a repeat
    of the same channel+type for a call updates rather than duplicates."""
    out: list[FallbackMessage] = []
    for item in items:
        call, order = _resolve_call_order(db, item.happyrobot_call_id, item.twin_order_ref, order_required=True)
        row = (
            db.query(FallbackMessage)
            .filter_by(call_id=call.call_id, channel=item.channel, content_type=item.content_type)
            .first()
        )
        if row is None:
            row = FallbackMessage(call_id=call.call_id, channel=item.channel, content_type=item.content_type)
            db.add(row)
        row.order_id = order.order_id
        row.status = item.status
        row.sent_at = item.sent_at
        db.flush()
        out.append(row)
    return out
