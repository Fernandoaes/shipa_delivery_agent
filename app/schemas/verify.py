import uuid

from pydantic import BaseModel


class VerifyRequest(BaseModel):
    happyrobot_call_id: str | None = None
    caller_number: str | None = None
    language: str | None = None
    name: str | None = None
    order_ref: str | None = None
    registered_phone: str | None = None
    delivery_area: str | None = None
    item: str | None = None


class OrderPublic(BaseModel):
    """Order fields safe to return to a VERIFIED caller. No otp_code here (safety)."""
    order_id: uuid.UUID
    twin_order_ref: str
    merchant: str
    status: str
    delivery_address: str
    delivery_area: str | None
    delivery_window: str | None
    assigned_driver: str | None
    expected_pieces: int | None


class VerifyResponse(BaseModel):
    call_id: uuid.UUID
    result: str
    attempt_no: int
    escalated: bool
    order: OrderPublic | None
