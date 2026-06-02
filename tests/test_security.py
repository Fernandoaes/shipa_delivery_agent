from app.security import scrub_otp


def test_scrub_otp_redacts_known_code():
    text = "Agent: your collection code is 4821, please keep it."
    assert "4821" not in scrub_otp(text, otp="4821")
    assert "[REDACTED]" in scrub_otp(text, otp="4821")


def test_scrub_otp_handles_none():
    assert scrub_otp("no code here", otp=None) == "no code here"
    assert scrub_otp(None, otp="4821") is None
