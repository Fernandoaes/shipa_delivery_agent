import pytest

from app.models import Call, Verification
from app.services.calls import get_or_create_call
from app.services.verification import VerifyInput, verify_caller
from app.twin.mock import MockTwinClient
from app.twin.sync import upsert_orders


@pytest.fixture()
def seeded(db):
    upsert_orders(db, MockTwinClient().fetch_all())
    db.flush()
    return db


def _call(db) -> Call:
    return get_or_create_call(db, happyrobot_call_id="hr-1", caller_number="+971500000001")


def test_pass_on_order_ref_plus_name(seeded):
    call = _call(seeded)
    res = verify_caller(seeded, call, VerifyInput(order_ref="TWIN-1001", name="Aisha Khan"))
    assert res.result == "passed"
    assert res.order is not None
    assert res.order.twin_order_ref == "TWIN-1001"
    seeded.refresh(call)
    assert call.verification_status == "passed"
    assert call.order_id == res.order.order_id


def test_pass_on_phone_name_area_fallback(seeded):
    call = _call(seeded)
    res = verify_caller(seeded, call, VerifyInput(
        registered_phone="+971500000001", name="Aisha Khan", delivery_area="Dubai Marina"))
    assert res.result == "passed"


def test_partial_when_only_name_matches(seeded):
    call = _call(seeded)
    res = verify_caller(seeded, call, VerifyInput(order_ref="TWIN-1001", name="Wrong Person"))
    assert res.result in ("partial", "failed")
    assert res.order is None  # never disclose on non-pass


def test_failed_when_nothing_matches(seeded):
    call = _call(seeded)
    res = verify_caller(seeded, call, VerifyInput(order_ref="NOPE", name="Nobody"))
    assert res.result == "failed"
    assert res.order is None


def test_attempt_cap_escalates_after_three(seeded):
    call = _call(seeded)
    for _ in range(3):
        verify_caller(seeded, call, VerifyInput(order_ref="NOPE", name="Nobody"))
    res = verify_caller(seeded, call, VerifyInput(order_ref="NOPE", name="Nobody"))
    assert res.escalated is True
    assert seeded.query(Verification).filter_by(call_id=call.call_id).count() >= 3


def test_each_attempt_is_recorded(seeded):
    call = _call(seeded)
    verify_caller(seeded, call, VerifyInput(order_ref="TWIN-1001", name="Aisha Khan"))
    v = seeded.query(Verification).filter_by(call_id=call.call_id).one()
    assert v.attempt_no == 1
    assert "order_ref" in v.factors_checked
