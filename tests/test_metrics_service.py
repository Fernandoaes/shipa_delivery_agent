import datetime as dt

from app.models import AddressFlag, Call, Escalation, Order, Reschedule
from app.services.metrics import compute_metrics
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


def _seed_orders(db):
    upsert_orders(db, MockTwinClient().fetch_all())  # 1001 OFD, 1002 failed, 1003 delivered
    db.flush()
    o1003 = db.query(Order).filter_by(twin_order_ref="TWIN-1003").one()
    o1003.attempt_count = 1
    o1003.delivered_at = dt.datetime(2026, 6, 1, 11, 0, 0)
    o1003.sla_due_at = dt.datetime(2026, 6, 1, 13, 0, 0)  # on time
    db.flush()
    return db.query(Order).filter_by(twin_order_ref="TWIN-1002").one()


def test_delivery_kpis(db):
    _seed_orders(db)
    m = compute_metrics(db)
    assert m["active_deliveries"] == 1   # 1001 out_for_delivery
    assert m["at_risk"] == 1             # 1002 failed
    # terminal = {delivered, failed, returned} = {1003, 1002}; first-attempt delivered = 1003
    assert m["first_attempt_success"] == 0.5
    assert m["on_time_rate"] == 1.0      # 1003 delivered_at <= sla_due_at


def test_recovery_rate_counts_rescheduled_or_address_fixed(db):
    failed = _seed_orders(db)
    now = dt.datetime.now()
    call = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                order_id=failed.order_id, customer_id=failed.customer_id, started_at=now)
    db.add(call)
    db.flush()
    db.add(Reschedule(call_id=call.call_id, order_id=failed.order_id,
                      requested_date=dt.date.today(), status="requested", created_at=now))
    db.flush()
    m = compute_metrics(db)
    assert m["recovery_rate"] == 1.0  # the one at-risk order has a reschedule


def test_containment_excludes_escalated_calls(db):
    order = _seed_orders(db)
    now = dt.datetime.now()
    handled = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                   disposition="rescheduled", order_id=order.order_id, customer_id=order.customer_id,
                   started_at=now)
    escalated = Call(direction="inbound", agent_type="inbound_support", verification_status="passed",
                     disposition="escalated", order_id=order.order_id, customer_id=order.customer_id,
                     started_at=now)
    db.add_all([handled, escalated])
    db.flush()
    db.add(Escalation(call_id=escalated.call_id, order_id=order.order_id, category="dispute",
                      status="open", created_at=now))
    db.flush()
    m = compute_metrics(db)
    assert m["total_calls"] == 2
    assert m["containment_rate"] == 0.5  # 1 of 2 calls resolved without escalation


def test_empty_db_rates_are_zero(db):
    m = compute_metrics(db)
    assert m["first_attempt_success"] == 0.0
    assert m["on_time_rate"] == 0.0
    assert m["recovery_rate"] == 0.0
    assert m["active_deliveries"] == 0
