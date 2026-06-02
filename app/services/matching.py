import unicodedata


def normalize(value: str | None) -> str:
    if not value:
        return ""
    nfkd = unicodedata.normalize("NFKD", value)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(no_accents.casefold().split())


def _alnum(value: str) -> str:
    return "".join(c for c in normalize(value) if c.isalnum())


def refs_match(a: str | None, b: str | None) -> bool:
    """Order refs / phones: normalize away case + separators, then exact."""
    if not a or not b:
        return False
    return _alnum(a) == _alnum(b)


def _levenshtein(a: str, b: str) -> int:
    """Damerau-Levenshtein: counts adjacent transpositions as 1 edit."""
    if a == b:
        return 0
    m, n = len(a), len(b)
    d = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        d[i][0] = i
    for j in range(n + 1):
        d[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + cost)
    return d[m][n]


def names_match(stored: str | None, spoken: str | None) -> bool:
    """Fuzzy name match tolerant of STT error. Token-subset OR close edit distance."""
    s_norm, k_norm = normalize(stored), normalize(spoken)
    if not s_norm or not k_norm:
        return False
    s_tokens, k_tokens = set(s_norm.split()), set(k_norm.split())
    # Every spoken token is close to some stored token (covers first-name-only + typos).
    for kt in k_tokens:
        if not any(_levenshtein(kt, st) <= 1 for st in s_tokens):
            return False
    return True
