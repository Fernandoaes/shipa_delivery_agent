import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.models import (
    AddressFlag, Escalation, FallbackMessage, Investigation, MerchantReferral, Order, Reschedule,
)
from app.schemas.dashboard import (
    AddressFlagSummary, CallSummary, CustomerDetail, CustomerListItem, EscalationSummary,
    FallbackMessageSummary, Insights, InvestigationSummary, MerchantReferralSummary, Metrics,
    OrderDetail, OrderListItem, RescheduleSummary,
)
from app.services.calls import list_calls as list_calls_service
from app.services.customers import get_customer_detail, list_customers
from app.services.insights import compute_insights
from app.services.metrics import compute_metrics
from app.services.orders import get_order_detail, list_orders

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/calls", response_model=list[CallSummary])
def list_calls(db: Session = Depends(get_db)):
    return list_calls_service(db)


@router.get("/investigations", response_model=list[InvestigationSummary])
def list_investigations(db: Session = Depends(get_db)):
    rows = db.query(Investigation).order_by(Investigation.opened_at.desc()).all()
    refs = dict(db.query(Order.order_id, Order.twin_order_ref).all())
    return [
        InvestigationSummary(
            investigation_id=r.investigation_id, call_id=r.call_id, order_id=r.order_id,
            type=r.type, status=r.status, callback_due_at=r.callback_due_at,
            opened_at=r.opened_at, twin_order_ref=refs.get(r.order_id),
        )
        for r in rows
    ]


@router.get("/reschedules", response_model=list[RescheduleSummary])
def list_reschedules(db: Session = Depends(get_db)):
    return db.query(Reschedule).order_by(Reschedule.created_at.desc()).all()


@router.get("/escalations", response_model=list[EscalationSummary])
def list_escalations(db: Session = Depends(get_db)):
    return db.query(Escalation).order_by(Escalation.created_at.desc()).all()


@router.get("/merchant-referrals", response_model=list[MerchantReferralSummary])
def list_merchant_referrals(db: Session = Depends(get_db)):
    return db.query(MerchantReferral).order_by(MerchantReferral.created_at.desc()).all()


@router.get("/address-flags", response_model=list[AddressFlagSummary])
def list_address_flags(db: Session = Depends(get_db)):
    return db.query(AddressFlag).order_by(AddressFlag.created_at.desc()).all()


@router.get("/fallback-messages", response_model=list[FallbackMessageSummary])
def list_fallback_messages(db: Session = Depends(get_db)):
    return db.query(FallbackMessage).order_by(FallbackMessage.sent_at.desc().nullslast()).all()


@router.get("/metrics", response_model=Metrics)
def metrics(days: int = 7, db: Session = Depends(get_db)):
    window = days if days in (1, 7, 30) else 7
    return compute_metrics(db, days=window)


@router.get("/insights", response_model=Insights)
def insights(days: int = 7, db: Session = Depends(get_db)):
    window = days if days in (1, 7, 30) else 7
    return compute_insights(db, days=window)


@router.get("/orders", response_model=list[OrderListItem])
def orders_list(db: Session = Depends(get_db)):
    return list_orders(db)


@router.get("/orders/{order_id}", response_model=OrderDetail)
def order_detail(order_id: uuid.UUID, db: Session = Depends(get_db)):
    detail = get_order_detail(db, order_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="order not found")
    return detail


@router.get("/customers", response_model=list[CustomerListItem])
def customers_list(db: Session = Depends(get_db)):
    return list_customers(db)


@router.get("/customers/{customer_id}", response_model=CustomerDetail)
def customer_detail(customer_id: uuid.UUID, db: Session = Depends(get_db)):
    detail = get_customer_detail(db, customer_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="customer not found")
    return detail
