import datetime as dt

from pydantic import BaseModel


class TwinOrderRead(BaseModel):
    twin_order_ref: str
    merchant: str
    status: str
    delivery_area: str | None
    delivery_window: str | None
    assigned_driver: str | None
    expected_pieces: int | None
    last_synced_at: dt.datetime
    # operational overlay derived from the latest operation rows per order
    reschedule_requested_date: dt.date | None = None
    escalated: bool = False
    investigation_open: bool = False
    # deliberately no otp_code and no delivery_address / customer PII
