import datetime as dt
from dataclasses import dataclass
from typing import Protocol


@dataclass
class OrderRecord:
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
    merchant_lat: float | None = None
    merchant_lng: float | None = None
    delivery_lat: float | None = None
    delivery_lng: float | None = None
    attempt_count: int = 1
    delivered_at: "dt.datetime | None" = None
    sla_due_at: "dt.datetime | None" = None


class TwinClient(Protocol):
    def fetch_all(self) -> list[OrderRecord]:
        """Return the full current order feed."""

    def fetch_by_ref(self, twin_order_ref: str) -> OrderRecord | None:
        """Live single-order lookup (fresh status + OTP at call start)."""
