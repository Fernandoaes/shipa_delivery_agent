import datetime as dt
import uuid

from sqlalchemy.orm import Session

from app.models import Call, Order
from app.security import scrub_otp


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


def set_disposition(db, call, *, disposition, intent=None, csat_score=None,
                    transcript=None, notes=None, recording_url=None):
    otp = None
    if call.order_id:
        order = db.get(Order, call.order_id)
        otp = order.otp_code if order else None
    call.disposition = disposition
    call.intent = intent
    call.csat_score = csat_score
    call.transcript = scrub_otp(transcript, otp)   # safety: OTP out of stored transcript
    call.notes = notes
    call.recording_url = recording_url
    call.ended_at = _now()
    db.flush()
    return call
