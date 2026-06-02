from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, require_webhook_secret
from app.schemas.ingest import IngestRequest, IngestResponse
from app.twin.base import OrderRecord
from app.twin.sync import upsert_orders

router = APIRouter(dependencies=[Depends(require_webhook_secret)])


@router.post("/orders/sync", response_model=IngestResponse)
def sync_orders(payload: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    records = [OrderRecord(**o.model_dump()) for o in payload.orders]
    rows = upsert_orders(db, records)
    db.commit()
    return IngestResponse(upserted=len(rows))
