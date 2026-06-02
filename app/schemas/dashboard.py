import datetime as dt
import uuid

from pydantic import BaseModel


class CallSummary(BaseModel):
    call_id: uuid.UUID
    direction: str
    language: str | None
    verification_status: str
    intent: str | None
    disposition: str | None
    csat_score: float | None
    started_at: dt.datetime
    ended_at: dt.datetime | None
    # deliberately no transcript / otp / raw caller PII beyond what ops needs

    model_config = {"from_attributes": True}


class InvestigationSummary(BaseModel):
    investigation_id: uuid.UUID
    call_id: uuid.UUID
    order_id: uuid.UUID
    type: str
    status: str
    callback_due_at: dt.datetime | None
    opened_at: dt.datetime
    model_config = {"from_attributes": True}


class RescheduleSummary(BaseModel):
    reschedule_id: uuid.UUID
    call_id: uuid.UUID
    order_id: uuid.UUID
    requested_date: dt.date
    status: str
    synced_to_twin_at: dt.datetime | None
    model_config = {"from_attributes": True}


class EscalationSummary(BaseModel):
    escalation_id: uuid.UUID
    call_id: uuid.UUID
    category: str
    status: str
    created_at: dt.datetime
    model_config = {"from_attributes": True}


class Metrics(BaseModel):
    total_calls: int
    first_attempt_rate: float
    deflection_rate: float
    avg_csat: float | None
    avg_handle_time_seconds: float | None
