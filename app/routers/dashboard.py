import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.models import Escalation, Investigation, Reschedule
from app.schemas.dashboard import (
    CallSummary, CustomerDetail, CustomerListItem, EscalationSummary, Insights,
    InvestigationSummary, Metrics, OrderDetail, OrderListItem, RescheduleSummary,
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
    return db.query(Investigation).order_by(Investigation.opened_at.desc()).all()


@router.get("/reschedules", response_model=list[RescheduleSummary])
def list_reschedules(db: Session = Depends(get_db)):
    return db.query(Reschedule).order_by(Reschedule.created_at.desc()).all()


@router.get("/escalations", response_model=list[EscalationSummary])
def list_escalations(db: Session = Depends(get_db)):
    return db.query(Escalation).order_by(Escalation.created_at.desc()).all()


@router.get("/metrics", response_model=Metrics)
def metrics(db: Session = Depends(get_db)):
    return compute_metrics(db)


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
