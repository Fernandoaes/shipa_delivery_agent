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


def test_list_calls_includes_notes_caller_and_reschedule(db):
    from app.models import Order, Reschedule
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    call = _seed_call(db, order, intent="reschedule", disposition="rescheduled")
    call.caller_number = "+971501234567"
    call.notes = "Customer asked to move delivery to the weekend."
    db.add(Reschedule(
        call_id=call.call_id, order_id=order.order_id,
        requested_date=dt.date(2026, 6, 6), requested_window="09:00-12:00",
        reason="Not home in morning", status="requested",
        created_at=dt.datetime.now(),
    ))
    db.flush()

    item = list_calls(db)[0]
    assert item.caller_number == "+971501234567"
    assert item.notes == "Customer asked to move delivery to the weekend."
    assert item.reschedule is not None
    assert item.reschedule.requested_date == dt.date(2026, 6, 6)
    assert item.reschedule.requested_window == "09:00-12:00"
    assert item.reschedule.reason == "Not home in morning"


def test_list_calls_no_reschedule_is_none(db):
    from app.models import Order
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    _seed_call(db, order)
    assert list_calls(db)[0].reschedule is None


def test_list_calls_orders_newest_first(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    from app.models import Order
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    _seed_call(db, order, started_at=dt.datetime(2026, 1, 1, 9, 0))
    _seed_call(db, order, started_at=dt.datetime(2026, 1, 2, 9, 0))
    items = list_calls(db)
    assert items[0].started_at > items[1].started_at
