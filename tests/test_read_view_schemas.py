from app.schemas.dashboard import CustomerBrief, OrderDetail


def test_order_detail_excludes_otp():
    assert "otp_code" not in OrderDetail.model_fields
    assert "customer" in OrderDetail.model_fields
    assert "delivery_lat" in OrderDetail.model_fields


def test_customer_brief_fields():
    assert set(CustomerBrief.model_fields) >= {"customer_id", "full_name", "primary_phone", "language_pref"}
