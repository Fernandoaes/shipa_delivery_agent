import datetime as dt
from collections import Counter

from sqlalchemy.orm import Session

from app.models import (
    AddressFlag, Call, Escalation, FallbackMessage, Investigation, Order, Reschedule,
)

_ACTIVE_STATUSES = ("out_for_delivery", "pending", "failed", "rescheduled")
_AT_RISK = ("failed", "returned")


def compute_insights(db: Session, days: int = 7) -> dict:
    today = dt.date.today()
    start = today - dt.timedelta(days=days - 1)
    window_days = [start + dt.timedelta(days=i) for i in range(days)]

    # Stacked interactions: voice calls + fallback messages, by channel, per day.
    per_day: dict[dt.date, Counter] = {d: Counter() for d in window_days}
    calls = db.query(Call).all()
    windowed_calls = [c for c in calls if c.started_at.date() >= start]
    for c in windowed_calls:
        d = c.started_at.date()
        if d in per_day:
            per_day[d]["voice"] += 1
    for m in db.query(FallbackMessage).filter(FallbackMessage.sent_at.isnot(None)).all():
        d = m.sent_at.date()
        if d in per_day:
            per_day[d][m.channel] += 1
    interactions_per_day = [
        {"date": d, "channels": dict(per_day[d])} for d in window_days
    ]

    intent_counter = Counter((c.intent or "unknown") for c in windowed_calls)
    disposition_counter = Counter((c.disposition or "unknown") for c in windowed_calls)
    intent_mix = [{"intent": k, "count": v} for k, v in intent_counter.most_common()]
    disposition_mix = [{"disposition": k, "count": v} for k, v in disposition_counter.most_common()]

    now = dt.datetime.now()
    needs_attention = {
        "open_escalations": db.query(Escalation).filter(Escalation.status == "open").count(),
        "overdue_callbacks": db.query(Investigation).filter(
            Investigation.status == "open", Investigation.callback_due_at < now
        ).count(),
        "pending_reschedules": db.query(Reschedule).filter(Reschedule.synced_to_twin_at.is_(None)).count(),
        "pending_address_flags": db.query(AddressFlag).filter(AddressFlag.status == "pending").count(),
    }

    failure_counter: Counter = Counter()
    for o in db.query(Order).filter(Order.status.in_(_AT_RISK)).all():
        failure_counter[o.delivery_area or "Unknown"] += 1
    failures_by_area = [{"area": k, "count": v} for k, v in failure_counter.most_common()]

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
        "interactions_per_day": interactions_per_day,
        "intent_mix": intent_mix,
        "disposition_mix": disposition_mix,
        "failures_by_area": failures_by_area,
        "needs_attention": needs_attention,
        "map_points": map_points,
    }
