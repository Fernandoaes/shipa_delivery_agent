from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.deps import get_db, require_webhook_secret
from app.schemas.ingest import (
    AddressFlagSyncRequest,
    CallSyncRequest,
    CallSyncResponse,
    EscalationSyncRequest,
    FallbackMessageSyncRequest,
    IngestRequest,
    IngestResponse,
    InvestigationSyncRequest,
    MerchantReferralSyncRequest,
    RescheduleSyncRequest,
    SyncResponse,
)
from app.services import actions
from app.services.actions import ActionSyncError
from app.services.calls import upsert_calls
from app.twin.base import OrderRecord
from app.twin.sync import upsert_orders

router = APIRouter(dependencies=[Depends(require_webhook_secret)])


@router.post("/orders/sync", response_model=IngestResponse)
def sync_orders(payload: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    records = [OrderRecord(**o.model_dump()) for o in payload.orders]
    rows = upsert_orders(db, records)
    db.commit()
    return IngestResponse(upserted=len(rows))


@router.post("/calls/sync", response_model=CallSyncResponse)
def sync_calls(payload: CallSyncRequest, db: Session = Depends(get_db)) -> CallSyncResponse:
    rows = upsert_calls(db, payload.calls)
    db.commit()
    return CallSyncResponse(upserted=len(rows))


def _run_action_sync(db: Session, fn, items) -> SyncResponse:
    try:
        rows = fn(db, items)
    except ActionSyncError as exc:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc))
    db.commit()
    return SyncResponse(upserted=len(rows))


@router.post("/reschedules/sync", response_model=SyncResponse)
def sync_reschedules(payload: RescheduleSyncRequest, db: Session = Depends(get_db)) -> SyncResponse:
    return _run_action_sync(db, actions.upsert_reschedules, payload.reschedules)


@router.post("/investigations/sync", response_model=SyncResponse)
def sync_investigations(payload: InvestigationSyncRequest, db: Session = Depends(get_db)) -> SyncResponse:
    return _run_action_sync(db, actions.upsert_investigations, payload.investigations)


@router.post("/escalations/sync", response_model=SyncResponse)
def sync_escalations(payload: EscalationSyncRequest, db: Session = Depends(get_db)) -> SyncResponse:
    return _run_action_sync(db, actions.upsert_escalations, payload.escalations)


@router.post("/merchant-referrals/sync", response_model=SyncResponse)
def sync_merchant_referrals(payload: MerchantReferralSyncRequest, db: Session = Depends(get_db)) -> SyncResponse:
    return _run_action_sync(db, actions.upsert_merchant_referrals, payload.merchant_referrals)


@router.post("/address-flags/sync", response_model=SyncResponse)
def sync_address_flags(payload: AddressFlagSyncRequest, db: Session = Depends(get_db)) -> SyncResponse:
    return _run_action_sync(db, actions.upsert_address_flags, payload.address_flags)


@router.post("/fallback-messages/sync", response_model=SyncResponse)
def sync_fallback_messages(payload: FallbackMessageSyncRequest, db: Session = Depends(get_db)) -> SyncResponse:
    return _run_action_sync(db, actions.upsert_fallback_messages, payload.fallback_messages)
