import datetime as dt
from typing import Literal

from pydantic import BaseModel

from app.schemas.calls import DispositionLiteral, IntentLiteral

EscalationCategory = Literal["cancel", "complaint", "unclassified", "hostile", "verification_failed"]


class IngestOrder(BaseModel):
    twin_order_ref: str
    customer_name: str
    customer_phone: str
    merchant: str
    status: str
    delivery_address: str
    delivery_area: str | None = None
    delivery_window: str | None = None
    otp_code: str | None = None
    assigned_driver: str | None = None
    expected_pieces: int | None = None
    language_pref: str | None = None
    twin_customer_ref: str | None = None


class IngestRequest(BaseModel):
    orders: list[IngestOrder]


class IngestResponse(BaseModel):
    upserted: int


class CallSyncItem(BaseModel):
    happyrobot_call_id: str  # upsert key
    direction: str = "inbound"
    agent_type: str = "inbound_exception"
    caller_number: str | None = None
    language: str | None = None
    verification_status: str = "not_started"
    intent: IntentLiteral | None = None
    disposition: DispositionLiteral | None = None
    csat_score: float | None = None
    recording_url: str | None = None
    transcript: str | None = None
    notes: str | None = None
    twin_order_ref: str | None = None  # optional link to an existing order
    started_at: dt.datetime | None = None
    ended_at: dt.datetime | None = None


class CallSyncRequest(BaseModel):
    calls: list[CallSyncItem]


class CallSyncResponse(BaseModel):
    upserted: int


class SyncResponse(BaseModel):
    upserted: int


# Action sync items: keyed on happyrobot_call_id (+ twin_order_ref → order).
# No verified-call gate and no future-working-day rule — these may carry completed/historical actions.

class RescheduleSyncItem(BaseModel):
    happyrobot_call_id: str
    twin_order_ref: str
    requested_date: dt.date
    requested_window: str | None = None
    reason: str | None = None
    status: str = "requested"
    synced_to_twin_at: dt.datetime | None = None
    created_at: dt.datetime | None = None


class RescheduleSyncRequest(BaseModel):
    reschedules: list[RescheduleSyncItem]


class InvestigationSyncItem(BaseModel):
    happyrobot_call_id: str
    twin_order_ref: str
    type: str = "not_received"
    status: str = "open"
    callback_due_at: dt.datetime | None = None
    opened_at: dt.datetime | None = None
    resolved_at: dt.datetime | None = None
    resolution_notes: str | None = None
    assigned_to: str | None = None


class InvestigationSyncRequest(BaseModel):
    investigations: list[InvestigationSyncItem]


class EscalationSyncItem(BaseModel):
    happyrobot_call_id: str
    twin_order_ref: str | None = None  # escalations may have no order
    category: EscalationCategory
    reason: str | None = None
    status: str = "open"
    assigned_to: str | None = None
    created_at: dt.datetime | None = None
    resolved_at: dt.datetime | None = None


class EscalationSyncRequest(BaseModel):
    escalations: list[EscalationSyncItem]


class MerchantReferralSyncItem(BaseModel):
    happyrobot_call_id: str
    twin_order_ref: str
    reason: str | None = None
    status: str = "open"
    created_at: dt.datetime | None = None


class MerchantReferralSyncRequest(BaseModel):
    merchant_referrals: list[MerchantReferralSyncItem]


class AddressFlagSyncItem(BaseModel):
    happyrobot_call_id: str
    twin_order_ref: str
    correction_text: str
    original_address: str | None = None  # defaults to the order's address if omitted
    status: str = "pending"
    created_at: dt.datetime | None = None


class AddressFlagSyncRequest(BaseModel):
    address_flags: list[AddressFlagSyncItem]


class FallbackMessageSyncItem(BaseModel):
    happyrobot_call_id: str
    twin_order_ref: str
    channel: Literal["sms", "whatsapp"]
    content_type: Literal["tracking_link", "notice"]  # never "otp"
    status: str = "queued"
    sent_at: dt.datetime | None = None


class FallbackMessageSyncRequest(BaseModel):
    fallback_messages: list[FallbackMessageSyncItem]
