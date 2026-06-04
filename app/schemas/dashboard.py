import datetime as dt
import uuid

from pydantic import BaseModel


class RescheduleBrief(BaseModel):
    requested_date: dt.date
    requested_window: str | None
    reason: str | None
    status: str
    synced_to_twin_at: dt.datetime | None
    model_config = {"from_attributes": True}


class CallSummary(BaseModel):
    call_id: uuid.UUID
    order_id: uuid.UUID | None = None
    direction: str
    language: str | None
    verification_status: str
    intent: str | None
    disposition: str | None
    csat_score: float | None
    started_at: dt.datetime
    ended_at: dt.datetime | None
    customer_name: str | None = None
    twin_order_ref: str | None = None
    caller_number: str | None = None
    notes: str | None = None
    reschedule: RescheduleBrief | None = None
    # transcript / recording_url / otp stay out

    model_config = {"from_attributes": True}


class InvestigationSummary(BaseModel):
    investigation_id: uuid.UUID
    call_id: uuid.UUID
    order_id: uuid.UUID
    twin_order_ref: str | None = None
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
    reason: str | None = None
    status: str
    created_at: dt.datetime
    model_config = {"from_attributes": True}


class MerchantReferralSummary(BaseModel):
    referral_id: uuid.UUID
    call_id: uuid.UUID
    order_id: uuid.UUID
    reason: str | None
    status: str
    created_at: dt.datetime
    model_config = {"from_attributes": True}


class AddressFlagSummary(BaseModel):
    flag_id: uuid.UUID
    call_id: uuid.UUID
    order_id: uuid.UUID
    original_address: str
    correction_text: str
    status: str
    created_at: dt.datetime
    model_config = {"from_attributes": True}


class FallbackMessageSummary(BaseModel):
    message_id: uuid.UUID
    call_id: uuid.UUID | None
    order_id: uuid.UUID
    channel: str
    content_type: str
    status: str
    sent_at: dt.datetime | None
    model_config = {"from_attributes": True}


class Metrics(BaseModel):
    total_calls: int
    first_attempt_success: float
    on_time_rate: float
    active_deliveries: int
    at_risk: int
    containment_rate: float
    recovery_rate: float
    avg_csat: float | None
    avg_handle_time_seconds: float | None


class CustomerBrief(BaseModel):
    customer_id: uuid.UUID
    full_name: str
    primary_phone: str
    language_pref: str | None
    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    order_id: uuid.UUID
    twin_order_ref: str
    merchant: str
    status: str
    delivery_area: str | None
    delivery_window: str | None
    assigned_driver: str | None
    customer_name: str


class OrderDetail(BaseModel):
    order_id: uuid.UUID
    twin_order_ref: str
    merchant: str
    status: str
    delivery_address: str
    delivery_area: str | None
    delivery_window: str | None
    assigned_driver: str | None
    expected_pieces: int | None
    merchant_lat: float | None
    merchant_lng: float | None
    delivery_lat: float | None
    delivery_lng: float | None
    last_synced_at: dt.datetime
    customer: CustomerBrief
    # deliberately no otp_code


class CustomerListItem(BaseModel):
    customer_id: uuid.UUID
    full_name: str
    primary_phone: str
    language_pref: str | None
    order_count: int


class CustomerDetail(BaseModel):
    customer_id: uuid.UUID
    full_name: str
    primary_phone: str
    language_pref: str | None
    orders: list[OrderListItem]
    calls: list[CallSummary]
    avg_csat: float | None
    last_contact_at: dt.datetime | None
    needs_follow_up: bool


class IntentCount(BaseModel):
    intent: str
    count: int


class DispositionCount(BaseModel):
    disposition: str
    count: int


class ChannelDay(BaseModel):
    date: dt.date
    channels: dict[str, int]


class AreaCount(BaseModel):
    area: str
    count: int


class NeedsAttention(BaseModel):
    open_escalations: int
    overdue_callbacks: int
    pending_reschedules: int
    pending_address_flags: int


class MapPoint(BaseModel):
    order_id: uuid.UUID
    twin_order_ref: str
    status: str
    delivery_area: str | None
    delivery_lat: float
    delivery_lng: float
    merchant: str
    merchant_lat: float | None
    merchant_lng: float | None


class Insights(BaseModel):
    interactions_per_day: list[ChannelDay]
    intent_mix: list[IntentCount]
    disposition_mix: list[DispositionCount]
    failures_by_area: list[AreaCount]
    needs_attention: NeedsAttention
    map_points: list[MapPoint]
