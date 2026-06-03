from app.models import Customer
from app.services.customers import get_customer_detail, list_customers
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def test_list_customers_counts_orders(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    items = list_customers(db)
    assert len(items) == 3
    assert all(i.order_count == 1 for i in items)


def test_get_customer_detail_lists_orders(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    cid = db.query(Customer).filter_by(full_name="Aisha Khan").one().customer_id
    detail = get_customer_detail(db, cid)
    assert detail.full_name == "Aisha Khan"
    assert detail.orders[0].twin_order_ref == "TWIN-1001"


def test_get_customer_detail_missing_returns_none(db):
    import uuid
    assert get_customer_detail(db, uuid.uuid4()) is None
