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
