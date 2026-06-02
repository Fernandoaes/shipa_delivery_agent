import datetime as dt

from app.models import Call, Customer, Order, Verification


def test_customer_order_call_chain(db):
    cust = Customer(full_name="Aisha Khan", primary_phone="+971500000001", last_synced_at=dt.datetime.now(dt.timezone.utc))
    db.add(cust)
    db.flush()
    order = Order(
        twin_order_ref="TWIN-1",
        customer_id=cust.customer_id,
        merchant="Amazon",
        status="out_for_delivery",
        delivery_address="Flat 1, Dubai Marina",
        last_synced_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(order)
    db.flush()
    call = Call(
        direction="inbound",
        agent_type="inbound_exception",
        verification_status="not_started",
        started_at=dt.datetime.now(dt.timezone.utc),
        customer_id=cust.customer_id,
        order_id=order.order_id,
    )
    db.add(call)
    db.flush()
    v = Verification(
        call_id=call.call_id, factors_checked=["name", "order_ref"],
        factors_passed=["name"], result="partial", attempt_no=1,
        created_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(v)
    db.flush()
    assert order.customer_id == cust.customer_id
    assert call.order_id == order.order_id
    assert v.factors_checked == ["name", "order_ref"]
