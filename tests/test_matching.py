from app.services.matching import names_match, normalize, refs_match


def test_normalize_casefolds_and_strips():
    assert normalize("  Aïsha   Khan ") == "aisha khan"


def test_refs_match_ignores_case_and_spaces():
    assert refs_match("twin-1", "TWIN 1") is True
    assert refs_match("twin-1", "twin-2") is False


def test_names_match_tolerates_minor_stt_error():
    assert names_match("Aisha Khan", "aisha kahn") is True   # transposition
    assert names_match("Aisha Khan", "John Smith") is False


def test_names_match_token_subset():
    # caller gives first name only
    assert names_match("Aisha Khan", "aisha") is True


def test_names_match_short_tokens_require_exact():
    # 2-char tokens must match exactly; fuzzy tolerance must not apply.
    assert names_match("Al Khan", "al khan") is True       # exact short tokens ok
    assert names_match("Al Khan", "az khan") is False       # 'az' != 'al', too short to fuzz
