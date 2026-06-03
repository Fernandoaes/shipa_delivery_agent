from app.models import Order


def test_order_has_coordinate_columns():
    cols = Order.__table__.columns.keys()
    for c in ("merchant_lat", "merchant_lng", "delivery_lat", "delivery_lng"):
        assert c in cols
