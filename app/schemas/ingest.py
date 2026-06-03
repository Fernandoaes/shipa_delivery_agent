import datetime as dt

from pydantic import BaseModel

from app.schemas.calls import DispositionLiteral, IntentLiteral


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
