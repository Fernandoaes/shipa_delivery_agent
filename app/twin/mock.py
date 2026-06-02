from app.twin.base import OrderRecord

_SEED = [
    OrderRecord(
        twin_order_ref="TWIN-1001", customer_name="Aisha Khan", customer_phone="+971500000001",
        merchant="Amazon", status="out_for_delivery", delivery_address="Apt 12, Marina Gate 1, Dubai Marina",
        delivery_area="Dubai Marina", delivery_window="2026-06-03 09:00-12:00", otp_code="4821",
        assigned_driver="Rahul P.", expected_pieces=1, language_pref="en",
    ),
    OrderRecord(
        twin_order_ref="TWIN-1002", customer_name="Omar Al Farsi", customer_phone="+971500000002",
        merchant="Temu", status="failed", delivery_address="Villa 7, Al Barsha 2",
        delivery_area="Al Barsha", delivery_window="2026-06-02 14:00-18:00", otp_code="7310",
        assigned_driver="Sara M.", expected_pieces=3, language_pref="ar",
    ),
    OrderRecord(
        twin_order_ref="TWIN-1003", customer_name="Fatima Noor", customer_phone="+971500000003",
        merchant="Trendyol", status="delivered", delivery_address="Office 401, Business Bay Tower",
        delivery_area="Business Bay", delivery_window="2026-06-01 10:00-13:00", otp_code="1599",
        assigned_driver="Ali K.", expected_pieces=2, language_pref="en",
    ),
]


class MockTwinClient:
    def fetch_all(self) -> list[OrderRecord]:
        # Return copies so tests can mutate without corrupting the seed.
        from dataclasses import replace
        return [replace(r) for r in _SEED]

    def fetch_by_ref(self, twin_order_ref: str) -> OrderRecord | None:
        from dataclasses import replace
        for r in _SEED:
            if r.twin_order_ref == twin_order_ref:
                return replace(r)
        return None
