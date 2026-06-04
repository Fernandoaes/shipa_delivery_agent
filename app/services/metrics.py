import datetime as dt

from sqlalchemy.orm import Session

from app.models import AddressFlag, Call, Escalation, Order, Reschedule

_TERMINAL = ("delivered", "failed", "returned")
_AT_RISK = ("failed", "returned")
_ACTIVE = ("out_for_delivery", "pending")


def compute_metrics(db: Session, days: int = 7) -> dict:
    # Call KPIs window by started_at (matches compute_insights); delivery KPIs are current-snapshot.
    start = dt.date.today() - dt.timedelta(days=days - 1)
    calls = [c for c in db.query(Call).all() if c.started_at.date() >= start]
    total = len(calls)
    completed = [c for c in calls if c.ended_at]
    escalated_call_ids = {e.call_id for e in db.query(Escalation).all()}
    contained = [c for c in calls if c.disposition and c.call_id not in escalated_call_ids]
    csats = [float(c.csat_score) for c in calls if c.csat_score is not None]
    handle_times = [(c.ended_at - c.started_at).total_seconds() for c in completed]

    orders = db.query(Order).all()
    terminal = [o for o in orders if o.status in _TERMINAL]
    delivered = [o for o in orders if o.status == "delivered"]
    first_attempt = [o for o in delivered if o.attempt_count == 1]
    on_time_denom = [o for o in delivered if o.sla_due_at is not None and o.delivered_at is not None]
    on_time_num = [o for o in on_time_denom if o.delivered_at <= o.sla_due_at]
    at_risk = [o for o in orders if o.status in _AT_RISK]
    active = [o for o in orders if o.status in _ACTIVE]

    at_risk_ids = {o.order_id for o in at_risk}
    # Recovery is lifetime: an at-risk order counts as recovered if it EVER got a reschedule/address-fix.
    rescheduled_ids = {r.order_id for r in db.query(Reschedule.order_id).all()}
    flagged_ids = {f.order_id for f in db.query(AddressFlag.order_id).all()}
    recovered = at_risk_ids & (rescheduled_ids | flagged_ids)

    def rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 3) if denominator else 0.0

    return {
        "total_calls": total,
        "first_attempt_success": rate(len(first_attempt), len(terminal)),
        "on_time_rate": rate(len(on_time_num), len(on_time_denom)),
        "active_deliveries": len(active),
        "at_risk": len(at_risk),
        "containment_rate": rate(len(contained), total),
        "recovery_rate": rate(len(recovered), len(at_risk)),
        "avg_csat": round(sum(csats) / len(csats), 2) if csats else None,
        "avg_handle_time_seconds": round(sum(handle_times) / len(handle_times), 1) if handle_times else None,
    }
