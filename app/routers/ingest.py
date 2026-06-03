from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, require_webhook_secret
from app.schemas.ingest import (
    CallSyncRequest,
    CallSyncResponse,
    IngestRequest,
    IngestResponse,
)
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
