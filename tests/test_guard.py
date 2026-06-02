import datetime as dt

import pytest

from app.models import Call
from app.services.guard import VerificationRequired, require_verified_call


def _call(db, status: str) -> Call:
    c = Call(direction="inbound", agent_type="inbound_exception", verification_status=status,
             started_at=dt.datetime.now(dt.timezone.utc))
    db.add(c)
    db.flush()
    return c


def test_guard_blocks_unverified(db):
    call = _call(db, "partial")
    with pytest.raises(VerificationRequired):
        require_verified_call(call)


def test_guard_allows_verified(db):
    call = _call(db, "passed")
    require_verified_call(call)  # no raise
