from app.models import Call


class VerificationRequired(Exception):
    """Raised when an action/read is attempted before the call is verified. Safety."""


def require_verified_call(call: Call) -> None:
    if call.verification_status != "passed":
        raise VerificationRequired(f"call {call.call_id} is '{call.verification_status}', not 'passed'")
