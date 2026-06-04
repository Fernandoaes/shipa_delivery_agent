import datetime as dt

from app.models import Order
from app.twin.base import OrderRecord
from app.twin.sync import upsert_orders


def test_upsert_persists_delivery_tracking(db):
    due = dt.datetime(2026, 6, 4, 12, 0, 0)
    delivered = dt.datetime(2026, 6, 4, 11, 0, 0)
    rec = OrderRecord(
        twin_order_ref="TWIN-9001", customer_name="Test User", customer_phone="+971500009001",
        merchant="Amazon", status="delivered", delivery_address="Unit 1, Test Bldg",
        attempt_count=2, delivered_at=delivered, sla_due_at=due,
    )
    upsert_orders(db, [rec])
    db.flush()
    o = db.query(Order).filter_by(twin_order_ref="TWIN-9001").one()
    assert o.attempt_count == 2
    assert o.delivered_at == delivered
    assert o.sla_due_at == due


def test_upsert_defaults_attempt_count_and_preserves_timestamps(db):
    rec = OrderRecord(
        twin_order_ref="TWIN-9002", customer_name="Test Two", customer_phone="+971500009002",
        merchant="Noon", status="pending", delivery_address="Unit 2, Test Bldg",
    )
    upsert_orders(db, [rec])
    db.flush()
    o = db.query(Order).filter_by(twin_order_ref="TWIN-9002").one()
    assert o.attempt_count == 1
    assert o.delivered_at is None
    # a later partial sync without timestamps must not wipe a known delivered_at
    o.delivered_at = dt.datetime(2026, 6, 4, 10, 0, 0)
    db.flush()
    upsert_orders(db, [rec])  # rec still has delivered_at=None
    db.flush()
    assert o.delivered_at == dt.datetime(2026, 6, 4, 10, 0, 0)


def test_upsert_updates_attempt_count_but_omission_preserves_it(db):
    rec = OrderRecord(
        twin_order_ref="TWIN-9003", customer_name="Test Three", customer_phone="+971500009003",
        merchant="Amazon", status="failed", delivery_address="Unit 3, Test Bldg",
        attempt_count=1,
    )
    upsert_orders(db, [rec]); db.flush()
    o = db.query(Order).filter_by(twin_order_ref="TWIN-9003").one()
    assert o.attempt_count == 1
    # explicit higher value updates
    upsert_orders(db, [OrderRecord(twin_order_ref="TWIN-9003", customer_name="Test Three",
                  customer_phone="+971500009003", merchant="Amazon", status="failed",
                  delivery_address="Unit 3, Test Bldg", attempt_count=3)]); db.flush()
    assert o.attempt_count == 3
    # omitted (None) value must NOT reset it
    upsert_orders(db, [OrderRecord(twin_order_ref="TWIN-9003", customer_name="Test Three",
                  customer_phone="+971500009003", merchant="Amazon", status="failed",
                  delivery_address="Unit 3, Test Bldg")]); db.flush()
    assert o.attempt_count == 3
