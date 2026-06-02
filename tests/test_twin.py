from app.models import Customer, Order
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def test_seed_upsert_creates_orders_and_customers(db):
    records = MockTwinClient().fetch_all()
    assert len(records) >= 3
    upsert_orders(db, records)
    db.flush()
    assert db.query(Order).count() == len(records)
    # customers deduped on phone
    assert db.query(Customer).count() >= 1


def test_upsert_is_idempotent(db):
    records = MockTwinClient().fetch_all()
    upsert_orders(db, records)
    db.flush()
    first = db.query(Order).count()
    upsert_orders(db, records)  # second time: update, not insert
    db.flush()
    assert db.query(Order).count() == first


def test_upsert_refreshes_status_and_otp(db):
    client = MockTwinClient()
    records = client.fetch_all()
    upsert_orders(db, records)
    db.flush()
    ref = records[0].twin_order_ref
    records[0].status = "delivered"
    records[0].otp_code = "9999"
    upsert_orders(db, records)
    db.flush()
    order = db.query(Order).filter_by(twin_order_ref=ref).one()
    assert order.status == "delivered"
    assert order.otp_code == "9999"
