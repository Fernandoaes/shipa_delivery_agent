import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel

DispositionLiteral = Literal[
    "resolved_info", "rescheduled", "investigation_opened", "re_attempt_scheduled",
    "referred_to_merchant", "escalated", "verification_failed", "no_order_found",
]
IntentLiteral = Literal[
    "tracking", "not_received", "failed_delivery", "wrong_items", "reschedule", "cancel", "other",
]


class DispositionRequest(BaseModel):
    disposition: DispositionLiteral
    intent: IntentLiteral | None = None
    csat_score: float | None = None
    transcript: str | None = None
    notes: str | None = None
    recording_url: str | None = None


class DispositionResponse(BaseModel):
    call_id: uuid.UUID
    disposition: str
    intent: str | None
    csat_score: float | None
    transcript: str | None
    ended_at: dt.datetime | None
