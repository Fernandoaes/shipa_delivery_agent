import datetime as dt
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Call, Customer, Escalation, Order, Verification
from app.services.matching import names_match, refs_match


@dataclass
class VerifyInput:
    name: str | None = None
    order_ref: str | None = None
    registered_phone: str | None = None
    delivery_area: str | None = None
    item: str | None = None


@dataclass
class VerifyResult:
    result: str            # passed | partial | failed
    order: Order | None    # populated ONLY on pass (safety)
    attempt_no: int
    escalated: bool = False


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _candidate_order(db: Session, data: VerifyInput) -> Order | None:
    if data.order_ref:
        for o in db.query(Order).all():
            if refs_match(o.twin_order_ref, data.order_ref):
                return o
    if data.registered_phone:
        cust = None
        for c in db.query(Customer).all():
            if refs_match(c.primary_phone, data.registered_phone):
                cust = c
                break
        if cust:
            order = db.query(Order).filter_by(customer_id=cust.customer_id).first()
            if order:
                return order
    return None


def _evaluate(order: Order | None, data: VerifyInput) -> tuple[str, list[str], list[str]]:
    checked: list[str] = []
    passed: list[str] = []
    if data.order_ref is not None:
        checked.append("order_ref")
        if order and refs_match(order.twin_order_ref, data.order_ref):
            passed.append("order_ref")
    if data.name is not None:
        checked.append("name")
        if order and names_match(order.customer.full_name, data.name):
            passed.append("name")
    if data.registered_phone is not None:
        checked.append("registered_phone")
        if order and refs_match(order.customer.primary_phone, data.registered_phone):
            passed.append("registered_phone")
    if data.delivery_area is not None:
        checked.append("delivery_area")
        if order and names_match(order.delivery_area, data.delivery_area):
            passed.append("delivery_area")

    ps = set(passed)
    strong = {"order_ref", "name"}.issubset(ps)
    fallback = {"registered_phone", "name", "delivery_area"}.issubset(ps)
    if strong or fallback:
        return "passed", checked, passed
    if passed:
        return "partial", checked, passed
    return "failed", checked, passed


def verify_caller(db: Session, call: Call, data: VerifyInput) -> VerifyResult:
    prior = db.query(Verification).filter_by(call_id=call.call_id).count()
    attempt_no = prior + 1

    order = _candidate_order(db, data)
    result, checked, passed = _evaluate(order, data)

    db.add(Verification(
        call_id=call.call_id, order_id=order.order_id if order else None,
        factors_checked=checked, factors_passed=passed, result=result,
        attempt_no=attempt_no, created_at=_now(),
    ))
    call.verification_status = result

    escalated = False
    matched_order: Order | None = None
    if result == "passed":
        matched_order = order
        call.order_id = order.order_id
        call.customer_id = order.customer_id
    elif attempt_no > settings.verification_max_attempts:
        # Safety: cap attempts, hand to a human.
        db.add(Escalation(
            call_id=call.call_id, category="verification_failed",
            reason="exceeded verification attempt cap", status="open", created_at=_now(),
        ))
        escalated = True

    db.flush()
    return VerifyResult(result=result, order=matched_order, attempt_no=attempt_no, escalated=escalated)
