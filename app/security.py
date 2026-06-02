import hmac


def secrets_match(provided: str | None, expected: str) -> bool:
    return hmac.compare_digest(provided or "", expected)


def scrub_otp(text: str | None, otp: str | None) -> str | None:
    """Remove a known OTP value from text before persistence. Safety: OTP discipline."""
    if text is None or not otp:
        return text
    return text.replace(otp, "[REDACTED]")
