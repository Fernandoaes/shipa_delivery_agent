import datetime as dt

from app.models import Call, Escalation, Order, Reschedule
from app.services.insights import compute_insights
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def _seed(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    now = dt.datetime.now()
    db.add(Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                intent="reschedule", disposition="rescheduled", csat_score=5,
                order_id=order.order_id, customer_id=order.customer_id, started_at=now))
    db.add(Call(direction="inbound", agent_type="inbound_support", verification_status="failed",
                intent="not_received", disposition=None, csat_score=None,
                order_id=order.order_id, customer_id=order.customer_id,
                started_at=now - dt.timedelta(days=3)))
    db.flush()
    return order


def test_interactions_per_day_zero_filled_with_voice_channel(db):
    _seed(db)
    out = compute_insights(db)  # default 7-day window
    assert len(out["interactions_per_day"]) == 7
    voice = sum(d["channels"].get("voice", 0) for d in out["interactions_per_day"])
    assert voice == 2
    dates = [d["date"] for d in out["interactions_per_day"]]
    assert dates == sorted(dates)


def test_interactions_include_fallback_messages(db):
    order = _seed(db)
    from app.models import FallbackMessage
    db.add(FallbackMessage(order_id=order.order_id, channel="whatsapp", content_type="text",
                           status="sent", sent_at=dt.datetime.now()))
    db.flush()
    out = compute_insights(db)
    wa = sum(d["channels"].get("whatsapp", 0) for d in out["interactions_per_day"])
    assert wa == 1


def test_intent_and_disposition_mix(db):
    _seed(db)
    out = compute_insights(db)
    intents = {d["intent"]: d["count"] for d in out["intent_mix"]}
    assert intents["reschedule"] == 1 and intents["not_received"] == 1
    dispositions = {d["disposition"]: d["count"] for d in out["disposition_mix"]}
    assert dispositions["unknown"] == 1  # the None disposition is labeled "unknown"


def test_needs_attention_work_queue(db):
    order = _seed(db)
    call = db.query(Call).order_by(Call.started_at.desc()).first()
    from app.models import AddressFlag, Investigation
    db.add(Escalation(call_id=call.call_id, order_id=order.order_id, category="dispute",
                      status="open", created_at=dt.datetime.now()))
    db.add(Reschedule(call_id=call.call_id, order_id=order.order_id, requested_date=dt.date.today(),
                      status="requested", synced_to_twin_at=None, created_at=dt.datetime.now()))
    db.add(Investigation(call_id=call.call_id, order_id=order.order_id, type="missing_item",
                         status="open", callback_due_at=dt.datetime.now() - dt.timedelta(hours=1),
                         opened_at=dt.datetime.now()))
    db.add(AddressFlag(call_id=call.call_id, order_id=order.order_id, original_address="x",
                       correction_text="y", status="pending", created_at=dt.datetime.now()))
    db.flush()
    na = compute_insights(db)["needs_attention"]
    assert na["open_escalations"] == 1
    assert na["overdue_callbacks"] == 1
    assert na["pending_reschedules"] == 1
    assert na["pending_address_flags"] == 1


def test_failures_by_area(db):
    _seed(db)
    db.query(Order).filter_by(twin_order_ref="TWIN-1002").one().status = "failed"
    db.flush()
    areas = {a["area"]: a["count"] for a in compute_insights(db)["failures_by_area"]}
    assert areas.get("Al Barsha") == 1


def test_map_points_only_active_with_coords(db):
    _seed(db)
    order_with_coords = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    order_no_coords = db.query(Order).filter_by(twin_order_ref="TWIN-1003").one()

    order_with_coords.status = "out_for_delivery"
    order_with_coords.delivery_lat, order_with_coords.delivery_lng = 25.1, 55.2

    order_no_coords.status = "out_for_delivery"
    order_no_coords.delivery_lat, order_no_coords.delivery_lng = None, None

    db.flush()
    out = compute_insights(db)

    refs = {p["twin_order_ref"] for p in out["map_points"]}
    assert order_with_coords.twin_order_ref in refs     # coords present -> included
    assert order_no_coords.twin_order_ref not in refs   # coords absent -> excluded
    assert all(p["status"] in ("out_for_delivery", "pending", "failed", "rescheduled")
               for p in out["map_points"])


def test_map_points_include_merchant_origin(db):
    _seed(db)
    order = db.query(Order).filter_by(twin_order_ref="TWIN-1001").one()
    order.status = "out_for_delivery"
    order.delivery_lat, order.delivery_lng = 25.1, 55.2
    order.merchant = "Noon"
    order.merchant_lat, order.merchant_lng = 24.92, 55.16
    db.flush()

    out = compute_insights(db)
    pt = next(p for p in out["map_points"] if p["twin_order_ref"] == "TWIN-1001")
    assert pt["merchant"] == "Noon"
    assert pt["merchant_lat"] == 24.92
    assert pt["merchant_lng"] == 55.16
