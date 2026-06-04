import datetime as dt

from app.models import Call, Escalation, Reschedule
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


def test_get_order_detail_aggregates_related_records(db):
    orders = upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = next(o for o in orders if o.twin_order_ref == "TWIN-1001")
    # each operation table has a UNIQUE call_id, so make a distinct call per record
    c1 = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
              order_id=order.order_id, customer_id=order.customer_id, disposition="not_on_site",
              started_at=dt.datetime.now())
    c2 = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
              order_id=order.order_id, customer_id=order.customer_id, started_at=dt.datetime.now())
    db.add_all([c1, c2])
    db.flush()
    db.add(Escalation(call_id=c1.call_id, order_id=order.order_id, category="refund",
                      reason="late", status="open", created_at=dt.datetime.now()))
    db.add(Reschedule(call_id=c2.call_id, order_id=order.order_id,
                      requested_date=dt.date.today(), status="requested", created_at=dt.datetime.now()))
    db.flush()
    detail = get_order_detail(db, order.order_id)
    assert detail.attempt_count == order.attempt_count
    assert len(detail.calls) == 2
    assert len(detail.escalations) == 1
    assert detail.escalations[0].reason == "late"
    assert len(detail.reschedules) == 1


def test_get_order_detail_clean_order_has_empty_related(db):
    orders = upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    detail = get_order_detail(db, orders[0].order_id)
    assert detail.calls == []
    assert detail.escalations == []
    assert detail.reschedules == []
    assert detail.address_flags == []
