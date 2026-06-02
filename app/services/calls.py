import datetime as dt
import uuid

from sqlalchemy.orm import Session

from app.models import Call


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def get_or_create_call(
    db: Session,
    *,
    happyrobot_call_id: str | None = None,
    caller_number: str | None = None,
    language: str | None = None,
) -> Call:
    """One call row per HappyRobot call; reused if the agent retries /verify."""
    if happyrobot_call_id:
        existing = db.query(Call).filter_by(happyrobot_call_id=happyrobot_call_id).one_or_none()
        if existing:
            return existing
    call = Call(
        happyrobot_call_id=happyrobot_call_id, caller_number=caller_number, language=language,
        direction="inbound", agent_type="inbound_exception", verification_status="not_started",
        started_at=_now(),
    )
    db.add(call)
    db.flush()
    return call


def get_call(db: Session, call_id: uuid.UUID) -> Call | None:
    return db.get(Call, call_id)
