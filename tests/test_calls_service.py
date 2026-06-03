import datetime as dt

from app.models import Call
from app.services.calls import list_calls
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def _seed_call(db, order, **kw):
    call = Call(
        direction=kw.get("direction", "inbound"),
        agent_type=kw.get("agent_type", "inbound_support"),
        verification_status=kw.get("verification_status", "passed"),
        intent=kw.get("intent", "delivery_status"),
        disposition=kw.get("disposition", "info_provided"),
        csat_score=kw.get("csat_score", 4),
        order_id=order.order_id,
        customer_id=order.customer_id,
        started_at=kw.get("started_at", dt.datetime.now()),
    )
    db.add(call)
    db.flush()
    return call


def test_list_calls_includes_customer_and_order(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    from app.models import Order
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    _seed_call(db, order)
    items = list_calls(db)
    assert len(items) == 1
    assert items[0].twin_order_ref == "TWIN-1001"
    assert items[0].customer_name == order.customer.full_name


def test_list_calls_orders_newest_first(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    from app.models import Order
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    _seed_call(db, order, started_at=dt.datetime(2026, 1, 1, 9, 0))
    _seed_call(db, order, started_at=dt.datetime(2026, 1, 2, 9, 0))
    items = list_calls(db)
    assert items[0].started_at > items[1].started_at
