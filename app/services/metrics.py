import datetime as dt

from sqlalchemy.orm import Session

from app.models import Call, Escalation


def compute_metrics(db: Session, days: int = 7) -> dict:
    # Window by started_at (same server-clock convention as compute_insights) so
    # KPIs respond to the dashboard's 1d/7d/30d selector.
    start = dt.date.today() - dt.timedelta(days=days - 1)
    calls = [c for c in db.query(Call).all() if c.started_at.date() >= start]
    total = len(calls)
    completed = [c for c in calls if c.ended_at]
    # first-attempt: verified passed on the call (proxy for resolved without re-contact)
    first_attempt = [c for c in calls if c.verification_status == "passed"]
    # deflection: resolved by the agent without an escalation row
    escalated_call_ids = {e.call_id for e in db.query(Escalation).all()}
    deflected = [c for c in calls if c.disposition and c.call_id not in escalated_call_ids]
    csats = [float(c.csat_score) for c in calls if c.csat_score is not None]
    handle_times = [(c.ended_at - c.started_at).total_seconds() for c in completed]

    def rate(part: list, whole: int) -> float:
        return round(len(part) / whole, 3) if whole else 0.0

    return {
        "total_calls": total,
        "first_attempt_rate": rate(first_attempt, total),
        "deflection_rate": rate(deflected, total),
        "avg_csat": round(sum(csats) / len(csats), 2) if csats else None,
        "avg_handle_time_seconds": round(sum(handle_times) / len(handle_times), 1) if handle_times else None,
    }
