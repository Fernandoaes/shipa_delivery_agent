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


import datetime as dt

from app.models import Call, Order


def test_customer_detail_includes_call_insights(db):
    from app.twin.mock import MockTwinClient
    from app.twin.sync import upsert_orders
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    db.add(Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                intent="delivery_status", disposition="info_provided", csat_score=2,
                order_id=order.order_id, customer_id=order.customer_id,
                started_at=dt.datetime(2026, 1, 5, 10, 0)))
    db.flush()
    detail = get_customer_detail(db, order.customer_id)
    assert len(detail.calls) == 1
    assert detail.calls[0].twin_order_ref == "TWIN-1001"
    assert detail.avg_csat == 2.0
    assert detail.last_contact_at == dt.datetime(2026, 1, 5, 10, 0)
    assert detail.needs_follow_up is True  # avg csat < 3.0
