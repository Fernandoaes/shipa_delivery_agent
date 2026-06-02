from pydantic import BaseModel


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
