import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel


class RescheduleRequest(BaseModel):
    requested_date: dt.date
    requested_window: str | None = None
    reason: str | None = None


class RescheduleResponse(BaseModel):
    reschedule_id: uuid.UUID
    status: str
    requested_date: dt.date


class InvestigationRequest(BaseModel):
    type: Literal["not_received"] = "not_received"


class InvestigationResponse(BaseModel):
    investigation_id: uuid.UUID
    status: str
    callback_due_at: dt.datetime | None


class MerchantReferralRequest(BaseModel):
    reason: str | None = None


class MerchantReferralResponse(BaseModel):
    referral_id: uuid.UUID
    status: str


class AddressFlagRequest(BaseModel):
    correction_text: str


class AddressFlagResponse(BaseModel):
    flag_id: uuid.UUID
    status: str


class EscalateRequest(BaseModel):
    category: Literal["cancel", "complaint", "unclassified", "hostile", "verification_failed"]
    reason: str | None = None


class EscalateResponse(BaseModel):
    escalation_id: uuid.UUID
    status: str


class FallbackMessageRequest(BaseModel):
    channel: Literal["sms", "whatsapp"]
    content_type: Literal["tracking_link", "notice"]   # never "otp" — rejected by validation


class FallbackMessageResponse(BaseModel):
    message_id: uuid.UUID
    status: str
