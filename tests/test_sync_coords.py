from app.models import Order
from app.twin.base import OrderRecord
from app.twin.sync import upsert_orders


def test_upsert_persists_coordinates(db):
    rec = OrderRecord(
        twin_order_ref="TWIN-COORD", customer_name="Coord Tester",
        customer_phone="+971500009999", merchant="Amazon", status="pending",
        delivery_address="Somewhere", merchant_lat=24.918, merchant_lng=55.161,
        delivery_lat=25.0805, delivery_lng=55.1403,
    )
    upsert_orders(db, [rec])
    db.flush()
    o = db.query(Order).filter_by(twin_order_ref="TWIN-COORD").one()
    assert (o.merchant_lat, o.merchant_lng) == (24.918, 55.161)
    assert (o.delivery_lat, o.delivery_lng) == (25.0805, 55.1403)


def test_resync_without_coords_preserves_existing(db):
    base = dict(twin_order_ref="TWIN-KEEP", customer_name="Keep Coords",
                customer_phone="+971500008888", merchant="Amazon", status="pending",
                delivery_address="Somewhere")
    upsert_orders(db, [OrderRecord(**base, delivery_lat=25.08, delivery_lng=55.14)])
    db.flush()
    # a later sync without coords (the call-path case) must not wipe the pin
    upsert_orders(db, [OrderRecord(**base)])
    db.flush()
    o = db.query(Order).filter_by(twin_order_ref="TWIN-KEEP").one()
    assert (o.delivery_lat, o.delivery_lng) == (25.08, 55.14)
