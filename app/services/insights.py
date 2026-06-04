import datetime as dt
from collections import Counter

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.models import Call, Escalation, Order, Reschedule

_ACTIVE_STATUSES = ("out_for_delivery", "pending", "failed", "rescheduled")


def compute_insights(db: Session, days: int = 7) -> dict:
    calls = db.query(Call).all()

    # Day bucketing uses the server clock (UTC in deployment), matching stored started_at and the compute_metrics convention.
    today = dt.date.today()
    start = today - dt.timedelta(days=days - 1)
    per_day: dict[dt.date, int] = {start + dt.timedelta(days=i): 0 for i in range(days)}
    # charts + mixes + needs_attention reflect the selected window; map_points stay current-state.
    windowed = [c for c in calls if c.started_at.date() >= start]
    for c in windowed:
        d = c.started_at.date()
        if d in per_day:
            per_day[d] += 1
    calls_per_day = [{"date": d, "count": n} for d, n in sorted(per_day.items())]

    intent_counter = Counter((c.intent or "unknown") for c in windowed)
    disposition_counter = Counter((c.disposition or "unknown") for c in windowed)
    intent_mix = [{"intent": k, "count": v} for k, v in intent_counter.most_common()]
    disposition_mix = [{"disposition": k, "count": v} for k, v in disposition_counter.most_common()]

    # windowed by the row's own timestamp; failed_orders by their call's started_at
    # (every order has a call in the demo data) so Network Risk tracks the range.
    needs_attention = {
        "open_escalations": db.query(Escalation)
        .filter(Escalation.status == "open", Escalation.created_at >= start)
        .count(),
        "pending_reschedules": db.query(Reschedule)
        .filter(Reschedule.synced_to_twin_at.is_(None), Reschedule.created_at >= start)
        .count(),
        "failed_orders": db.query(func.count(distinct(Order.order_id)))
        .join(Call, Call.order_id == Order.order_id)
        .filter(Order.status.in_(["failed", "returned"]), Call.started_at >= start)
        .scalar(),
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
