from app.services.orders import get_order_detail, list_orders
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def test_list_orders_includes_customer_name(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    items = list_orders(db)
    assert len(items) == 3
    aisha = next(i for i in items if i.twin_order_ref == "TWIN-1001")
    assert aisha.customer_name == "Aisha Khan"


def test_get_order_detail_has_coords_and_customer(db):
    orders = upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    oid = next(o.order_id for o in orders if o.twin_order_ref == "TWIN-1001")
    detail = get_order_detail(db, oid)
    assert detail.delivery_lat == 25.0805
    assert detail.customer.full_name == "Aisha Khan"


def test_get_order_detail_missing_returns_none(db):
    import uuid
    assert get_order_detail(db, uuid.uuid4()) is None
