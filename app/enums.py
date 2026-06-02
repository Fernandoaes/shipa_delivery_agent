from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class OrderStatus(StrEnum):
    pending = "pending"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    failed = "failed"
    rescheduled = "rescheduled"
    returned = "returned"
    cancelled = "cancelled"


class VerificationStatus(StrEnum):
    not_started = "not_started"
    passed = "passed"
    partial = "partial"
    failed = "failed"


class Intent(StrEnum):
    tracking = "tracking"
    not_received = "not_received"
    failed_delivery = "failed_delivery"
    wrong_items = "wrong_items"
    reschedule = "reschedule"
    cancel = "cancel"
    other = "other"


class Disposition(StrEnum):
    resolved_info = "resolved_info"
    rescheduled = "rescheduled"
    investigation_opened = "investigation_opened"
    re_attempt_scheduled = "re_attempt_scheduled"
    referred_to_merchant = "referred_to_merchant"
    escalated = "escalated"
    verification_failed = "verification_failed"
    no_order_found = "no_order_found"


class EscalationCategory(StrEnum):
    cancel = "cancel"
    complaint = "complaint"
    unclassified = "unclassified"
    hostile = "hostile"
    verification_failed = "verification_failed"
