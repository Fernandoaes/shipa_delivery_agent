import hmac


def secrets_match(provided: str | None, expected: str) -> bool:
    return hmac.compare_digest(provided or "", expected)
