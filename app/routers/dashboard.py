from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.models import Call, Escalation, Investigation, Reschedule
from app.schemas.dashboard import (
    CallSummary, EscalationSummary, InvestigationSummary, Metrics, RescheduleSummary,
)
from app.services.metrics import compute_metrics

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/calls", response_model=list[CallSummary])
def list_calls(db: Session = Depends(get_db)):
    return db.query(Call).order_by(Call.started_at.desc()).all()


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
