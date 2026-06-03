import uuid

from sqlalchemy.orm import Session

from app.models import Escalation, Investigation, Order, Reschedule
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
