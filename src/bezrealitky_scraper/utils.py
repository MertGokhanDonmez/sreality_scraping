from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

NBSP_RE = re.compile(r"[\u00a0\u202f]")
SPACE_RE = re.compile(r"\s+")
MONEY_RE = re.compile(r"(?P<amount>\d[\d\s\u00a0\u202f.,]*)")


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = NBSP_RE.sub(" ", value)
    return SPACE_RE.sub(" ", value).strip()


def parse_int_money(value: str | None) -> int | None:
    """Parse human-formatted CZK money into an integer.

    Decimal parts are supported and rounded to the nearest integer. Thousands
    separators may be spaces, non-breaking spaces, dots, or commas.
    """
    text = clean_text(value)
    match = MONEY_RE.search(text)
    if not match:
        return None
    number = match.group("amount").replace(" ", "")

    # If both separators occur, the right-most one is treated as decimal.
    if "." in number and "," in number:
        decimal = "." if number.rfind(".") > number.rfind(",") else ","
        thousands = "," if decimal == "." else "."
        number = number.replace(thousands, "").replace(decimal, ".")
    elif number.count(",") == 1 and len(number.rsplit(",", 1)[1]) in (1, 2):
        number = number.replace(",", ".")
    elif number.count(".") == 1 and len(number.rsplit(".", 1)[1]) in (1, 2):
        pass
    else:
        number = number.replace(",", "").replace(".", "")

    try:
        return round(float(number))
    except ValueError:
        return None


def absolute_url(base_url: str, href: str) -> str:
    return urljoin(base_url, href)


def with_page(url: str, page: int) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if page <= 1:
        query.pop("page", None)
    else:
        query["page"] = str(page)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def slugify_column(value: str) -> str:
    value = clean_text(value).lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "field"
