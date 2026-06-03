import datetime as dt
from collections import Counter

from sqlalchemy.orm import Session

from app.models import Call, Escalation, Order, Reschedule

_ACTIVE_STATUSES = ("out_for_delivery", "pending", "failed", "rescheduled")


def compute_insights(db: Session) -> dict:
    calls = db.query(Call).all()

    today = dt.date.today()
    start = today - dt.timedelta(days=13)
    per_day: dict[dt.date, int] = {start + dt.timedelta(days=i): 0 for i in range(14)}
    for c in calls:
        d = c.started_at.date()
        if d in per_day:
            per_day[d] += 1
    calls_per_day = [{"date": d, "count": n} for d, n in sorted(per_day.items())]

    intent_counter = Counter((c.intent or "unknown") for c in calls)
    disposition_counter = Counter((c.disposition or "unknown") for c in calls)
    intent_mix = [{"intent": k, "count": v} for k, v in intent_counter.most_common()]
    disposition_mix = [{"disposition": k, "count": v} for k, v in disposition_counter.most_common()]

    needs_attention = {
        "open_escalations": db.query(Escalation).filter(Escalation.status == "open").count(),
        "pending_reschedules": db.query(Reschedule).filter(Reschedule.synced_to_twin_at.is_(None)).count(),
        "failed_orders": db.query(Order).filter(Order.status.in_(["failed", "returned"])).count(),
    }

    map_orders = (
        db.query(Order)
        .filter(
            Order.delivery_lat.isnot(None),
            Order.delivery_lng.isnot(None),
            Order.status.in_(_ACTIVE_STATUSES),
        )
        .all()
    )
    map_points = [
        {
            "order_id": o.order_id,
            "twin_order_ref": o.twin_order_ref,
            "status": o.status,
            "delivery_area": o.delivery_area,
            "delivery_lat": o.delivery_lat,
            "delivery_lng": o.delivery_lng,
        }
        for o in map_orders
    ]

    return {
        "calls_per_day": calls_per_day,
        "intent_mix": intent_mix,
        "disposition_mix": disposition_mix,
        "needs_attention": needs_attention,
        "map_points": map_points,
    }
