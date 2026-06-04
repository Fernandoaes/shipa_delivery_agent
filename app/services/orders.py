import uuid

from sqlalchemy.orm import Session

from app.models import AddressFlag, Call, Escalation, Investigation, Order, Reschedule
from app.schemas.dashboard import (
    AddressFlagSummary, CallSummary, CustomerBrief, EscalationSummary, InvestigationSummary,
    OrderDetail, OrderListItem, RescheduleSummary,
)
from app.schemas.twin import TwinOrderRead


def get_order(db: Session, order_id: uuid.UUID) -> Order | None:
    return db.get(Order, order_id)


def list_twin_orders(db: Session) -> list[TwinOrderRead]:
    # Non-secret read cache for the HappyRobot Twin: order base fields plus an
    # operational overlay derived from the latest operation rows. The order
    # mirror itself is never mutated by actions, so the overlay is what makes a
    # mid-call reschedule/escalation visible to a polling Twin.
    out: list[TwinOrderRead] = []
    for o in db.query(Order).order_by(Order.twin_order_ref).all():
        latest_reschedule = (
            db.query(Reschedule)
            .filter_by(order_id=o.order_id)
            .order_by(Reschedule.created_at.desc())
            .first()
        )
        escalated = db.query(Escalation).filter_by(order_id=o.order_id).first() is not None
        investigation_open = (
            db.query(Investigation).filter_by(order_id=o.order_id, status="open").first() is not None
        )
        out.append(TwinOrderRead(
            twin_order_ref=o.twin_order_ref, merchant=o.merchant, status=o.status,
            delivery_area=o.delivery_area, delivery_window=o.delivery_window,
            assigned_driver=o.assigned_driver, expected_pieces=o.expected_pieces,
            last_synced_at=o.last_synced_at,
            reschedule_requested_date=latest_reschedule.requested_date if latest_reschedule else None,
            escalated=escalated, investigation_open=investigation_open,
        ))
    return out


# Only flagged problems become an issue (escalation / address correction); elevated
# attempt_count is a separate dimension the frontend renders on its own.
def _derive_issue(o: Order, esc_by_order: dict, flag_by_order: dict) -> str | None:
    if o.order_id in esc_by_order:
        return esc_by_order[o.order_id]
    if o.order_id in flag_by_order:
        return f"Address: {flag_by_order[o.order_id]}"
    return None


def _order_list_item(o: Order, esc_by_order: dict | None = None, flag_by_order: dict | None = None) -> OrderListItem:
    esc_by_order = esc_by_order or {}
    flag_by_order = flag_by_order or {}
    return OrderListItem(
        order_id=o.order_id, twin_order_ref=o.twin_order_ref, merchant=o.merchant,
        status=o.status, delivery_area=o.delivery_area, delivery_window=o.delivery_window,
        assigned_driver=o.assigned_driver, customer_name=o.customer.full_name,
        attempt_count=o.attempt_count, issue=_derive_issue(o, esc_by_order, flag_by_order),
    )


def list_orders(db: Session) -> list[OrderListItem]:
    orders = db.query(Order).order_by(Order.twin_order_ref).all()
    esc_by_order = {
        oid: (reason or category)
        for oid, reason, category in db.query(
            Escalation.order_id, Escalation.reason, Escalation.category
        ).filter(Escalation.status == "open", Escalation.order_id.isnot(None)).all()
    }
    flag_by_order = dict(
        db.query(AddressFlag.order_id, AddressFlag.correction_text)
        .filter(AddressFlag.status == "pending").all()
    )
    return [_order_list_item(o, esc_by_order, flag_by_order) for o in orders]


def get_order_detail(db: Session, order_id: uuid.UUID) -> OrderDetail | None:
    o = db.get(Order, order_id)
    if o is None:
        return None
    calls = (
        db.query(Call).filter(Call.order_id == order_id).order_by(Call.started_at.desc()).all()
    )
    escalations = (
        db.query(Escalation).filter(Escalation.order_id == order_id)
        .order_by(Escalation.created_at.desc()).all()
    )
    investigations = (
        db.query(Investigation).filter(Investigation.order_id == order_id)
        .order_by(Investigation.opened_at.desc()).all()
    )
    reschedules = (
        db.query(Reschedule).filter(Reschedule.order_id == order_id)
        .order_by(Reschedule.created_at.desc()).all()
    )
    address_flags = (
        db.query(AddressFlag).filter(AddressFlag.order_id == order_id)
        .order_by(AddressFlag.created_at.desc()).all()
    )
    return OrderDetail(
        order_id=o.order_id, twin_order_ref=o.twin_order_ref, merchant=o.merchant,
        status=o.status, delivery_address=o.delivery_address, delivery_area=o.delivery_area,
        delivery_window=o.delivery_window, assigned_driver=o.assigned_driver,
        expected_pieces=o.expected_pieces, attempt_count=o.attempt_count,
        delivered_at=o.delivered_at, sla_due_at=o.sla_due_at,
        merchant_lat=o.merchant_lat, merchant_lng=o.merchant_lng,
        delivery_lat=o.delivery_lat, delivery_lng=o.delivery_lng,
        last_synced_at=o.last_synced_at,
        customer=CustomerBrief.model_validate(o.customer),
        # customer_name/twin_order_ref stay None here — the order page already shows them in context
        calls=[CallSummary.model_validate(c) for c in calls],
        escalations=[EscalationSummary.model_validate(e) for e in escalations],
        investigations=[InvestigationSummary.model_validate(i) for i in investigations],
        reschedules=[RescheduleSummary.model_validate(r) for r in reschedules],
        address_flags=[AddressFlagSummary.model_validate(f) for f in address_flags],
    )
