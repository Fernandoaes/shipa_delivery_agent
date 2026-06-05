import datetime as dt
import uuid

from sqlalchemy.orm import Session

from app.models import Call, Customer, Order, Reschedule
from app.schemas.dashboard import CallSummary, RescheduleBrief
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


def _call_summary(
    call: Call,
    customer_name: str | None,
    twin_order_ref: str | None,
    reschedule: Reschedule | None = None,
) -> CallSummary:
    return CallSummary(
        call_id=call.call_id,
        order_id=call.order_id,
        direction=call.direction,
        language=call.language,
        verification_status=call.verification_status,
        intent=call.intent,
        disposition=call.disposition,
        csat_score=float(call.csat_score) if call.csat_score is not None else None,
        started_at=call.started_at,
        ended_at=call.ended_at,
        customer_name=customer_name,
        twin_order_ref=twin_order_ref,
        caller_number=call.caller_number,
        notes=call.notes,
        reschedule=RescheduleBrief.model_validate(reschedule) if reschedule else None,
    )


def list_calls(db: Session) -> list[CallSummary]:
    rows = (
        db.query(Call, Customer.full_name, Order.twin_order_ref)
        .outerjoin(Customer, Call.customer_id == Customer.customer_id)
        .outerjoin(Order, Call.order_id == Order.order_id)
        .order_by(Call.started_at.desc())
        .all()
    )
    reschedules = {r.call_id: r for r in db.query(Reschedule).all()}
    return [_call_summary(call, name, ref, reschedules.get(call.call_id)) for call, name, ref in rows]


def get_call(db: Session, call_id: uuid.UUID) -> Call | None:
    return db.get(Call, call_id)


def upsert_calls(db: Session, items) -> list[Call]:
    """External write path for call records — keyed on happyrobot_call_id; safe to replay."""
    out: list[Call] = []
    for item in items:
        call = db.query(Call).filter_by(happyrobot_call_id=item.happyrobot_call_id).one_or_none()
        if call is None:
            call = Call(
                happyrobot_call_id=item.happyrobot_call_id,
                started_at=item.started_at or _now(),
            )
            db.add(call)

        order = None
        if item.twin_order_ref:
            order = db.query(Order).filter_by(twin_order_ref=item.twin_order_ref).one_or_none()

        call.direction = item.direction
        call.agent_type = item.agent_type
        call.caller_number = item.caller_number
        call.language = item.language
        # Only overwrite a live-set status if the sync payload carries a real value;
        # the schema default "not_started" must not clobber "passed"/"partial"/"failed".
        if item.verification_status != "not_started" or call.verification_status == "not_started":
            call.verification_status = item.verification_status
        call.intent = item.intent
        call.disposition = item.disposition
        call.csat_score = item.csat_score
        call.recording_url = item.recording_url
        call.transcript = scrub_otp(item.transcript, order.otp_code if order else None)  # safety: OTP out of transcript
        call.notes = item.notes
        if order:
            call.order_id = order.order_id
            call.customer_id = order.customer_id
        if item.started_at:
            call.started_at = item.started_at
        call.ended_at = item.ended_at
        db.flush()
        out.append(call)
    return out


def set_disposition(db, call, *, disposition, intent=None, csat_score=None,
                    transcript=None, notes=None, recording_url=None):
    if call.disposition is not None:
        return call  # one disposition per call; a repeat POST is a no-op
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
