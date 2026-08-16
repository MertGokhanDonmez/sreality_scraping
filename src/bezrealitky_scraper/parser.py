from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup, Tag

from .models import Listing, SearchCard
from .utils import absolute_url, clean_text, parse_int_money, stable_unique

LISTING_PATH_RE = re.compile(r"/(?:properties-flats-houses|nemovitosti-byty-domy)/\d+[-/]", re.I)
SIMILAR_HEADINGS = {"similar listings", "similar offers", "podobné nabídky", "podobne nabidky"}

SECTION_HEADINGS = {
    "characteristics": {"property characteristics", "parametry nemovitosti"},
    "amenities": {
        "what does this listing have to offer?",
        "co tato nemovitost nabízí?",
        "co tato nemovitost nabizi?",
    },
    "nearby": {
        "what you will find nearby",
        "v okolí nemovitosti najdete",
        "v okoli nemovitosti najdete",
    },
}

FINANCIAL_LABELS = {
    "monthly_rent_czk": ("monthly rent", "měsíční nájemné", "mesicni najemne"),
    "service_charges_czk": ("service charges", "poplatky za služby", "poplatky za sluzby"),
    "utility_charges_czk": ("utility charges", "poplatky za energie"),
    "refundable_deposit_czk": ("refundable deposit", "vratná kauce", "vratna kauce"),
}

KNOWN_CHARACTERISTIC_LABELS = [
    "Available from",
    "Dostupné od",
    "Building construction",
    "Konstrukce budovy",
    "Fully furnished",
    "Vybaveno",
    "Listing ID",
    "Číslo inzerátu",
    "Location",
    "Umístění",
    "Price per unit",
    "Cena za jednotku",
    "Condition",
    "Stav",
    "Layout",
    "Dispozice",
    "Floor",
    "Podlaží",
    "Ownership",
    "Vlastnictví",
    "Usable area",
    "Užitná plocha",
    "Floor area",
    "Plocha podlahová",
    "Plot area",
    "Plocha pozemku",
    "Energy performance",
    "Energetická náročnost",
    "Heating",
    "Vytápění",
    "Building type",
    "Typ budovy",
    "Year of construction",
    "Rok výstavby",
    "Year of reconstruction",
    "Rok rekonstrukce",
    "Number of floors",
    "Počet podlaží",
    "Ceiling height",
    "Výška stropu",
]

CTA_OR_MARKETING = (
    "request a tour",
    "interested?",
    "communicate all private owners",
    "save czk",
    "na inzerát již není možné reagovat",
    "máte zájem?",
    "domluvit prohlídku",
)

STATUS_WORDS = (
    "New",
    "Reserved",
    "Don't miss out",
    "Don’t miss out",
    "Nové",
    "Rezervováno",
)


@dataclass(slots=True)
class SearchParseResult:
    cards: list[SearchCard]
    page_count: int
    reported_count: int | None


def _heading_key(tag: Tag) -> str:
    return clean_text(tag.get_text(" ", strip=True)).lower()


def _is_heading(tag: Tag, accepted: set[str]) -> bool:
    return tag.name in {"h1", "h2", "h3", "h4"} and _heading_key(tag) in accepted


def _iter_before_similar(soup: BeautifulSoup) -> Iterable[Tag]:
    for tag in soup.find_all(True):
        if tag.name in {"h1", "h2", "h3", "h4"} and any(name in _heading_key(tag) for name in SIMILAR_HEADINGS):
            break
        yield tag


def _nearest_card_text(anchor: Tag) -> str:
    current: Tag | None = anchor
    best = clean_text(anchor.get_text(" ", strip=True))
    for _ in range(6):
        parent = current.parent if current else None
        if not isinstance(parent, Tag):
            break
        text = clean_text(parent.get_text(" ", strip=True))
        if len(best) < len(text) <= 800:
            best = text
        if parent.name in {"article", "li"}:
            return best
        current = parent
    return best


def _status_from_text(text: str) -> str:
    lowered = text.lower()
    for status in STATUS_WORDS:
        if status.lower() in lowered:
            return status
    return ""


def parse_search_page(html: str, page_url: str, page_number: int) -> SearchParseResult:
    soup = BeautifulSoup(html, "lxml")
    cards: list[SearchCard] = []
    seen: set[str] = set()

    for tag in _iter_before_similar(soup):
        if tag.name != "a":
            continue
        href = tag.get("href")
        if not isinstance(href, str) or not LISTING_PATH_RE.search(href):
            continue
        url = absolute_url(page_url, href).split("#", 1)[0]
        if url in seen:
            continue
        seen.add(url)
        summary = _nearest_card_text(tag)
        cards.append(
            SearchCard(
                url=url,
                search_page=page_number,
                title=clean_text(tag.get_text(" ", strip=True)),
                status=_status_from_text(summary),
                summary_text=summary,
            )
        )

    pages = {1}
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        query = parse_qs(urlsplit(absolute_url(page_url, href)).query)
        for raw in query.get("page", []):
            if raw.isdigit():
                pages.add(int(raw))
    page_count = max(pages)

    body_text = clean_text(soup.get_text(" ", strip=True))
    count_match = re.search(r"\((\d[\d\s\u00a0\u202f]*)\s+(?:buildings|nemovitostí|nemovitosti)\)", body_text, re.I)
    reported_count = None
    if count_match:
        reported_count = int(re.sub(r"\D", "", count_match.group(1)))

    return SearchParseResult(cards=cards, page_count=page_count, reported_count=reported_count)


def _find_heading(soup: BeautifulSoup, names: set[str]) -> Tag | None:
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        if _heading_key(tag) in names:
            return tag
    return None


def _section_tags(start_heading: Tag | None, stop_names: set[str] | None = None) -> list[Tag]:
    if start_heading is None:
        return []
    result: list[Tag] = []
    for tag in start_heading.find_all_next(True):
        if tag is start_heading:
            continue
        if tag.name in {"h1", "h2", "h3", "h4"}:
            if stop_names is None or any(name in _heading_key(tag) for name in stop_names):
                break
        result.append(tag)
    return result


def _section_text(start_heading: Tag | None, stop_names: set[str] | None = None) -> str:
    lines: list[str] = []
    for tag in _section_tags(start_heading, stop_names):
        # Leaf-ish elements avoid repeating the same nested text many times.
        if tag.name in {"script", "style", "svg", "path"}:
            continue
        if tag.find(["div", "p", "li", "tr", "dt", "dd", "h1", "h2", "h3", "h4"]):
            continue
        text = clean_text(tag.get_text(" ", strip=True))
        if text:
            lines.append(text)
    return "\n".join(stable_unique(lines))


def _extract_generic_pairs(tags: list[Tag]) -> dict[str, str]:
    pairs: dict[str, str] = {}

    for tr in [tag for tag in tags if tag.name == "tr"]:
        cells = [clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"], recursive=False)]
        cells = [value for value in cells if value]
        if len(cells) >= 2 and len(cells[0]) <= 80:
            pairs.setdefault(cells[0], " ".join(cells[1:]))

    for dt in [tag for tag in tags if tag.name == "dt"]:
        dd = dt.find_next_sibling("dd")
        key = clean_text(dt.get_text(" ", strip=True))
        value = clean_text(dd.get_text(" ", strip=True)) if dd else ""
        if key and value:
            pairs.setdefault(key, value)

    for tag in tags:
        children = [child for child in tag.find_all(recursive=False) if isinstance(child, Tag)]
        if len(children) != 2:
            continue
        key = clean_text(children[0].get_text(" ", strip=True))
        value = clean_text(children[1].get_text(" ", strip=True))
        whole = clean_text(tag.get_text(" ", strip=True))
        if key and value and key != value and len(key) <= 80 and len(whole) <= 300:
            pairs.setdefault(key, value)

    return pairs


def _extract_known_pairs(text: str) -> dict[str, str]:
    normalized = clean_text(text)
    if not normalized:
        return {}
    labels = sorted(KNOWN_CHARACTERISTIC_LABELS, key=len, reverse=True)
    label_pattern = "|".join(re.escape(label) for label in labels)
    matches = list(re.finditer(rf"(?i)(?<!\w)({label_pattern})(?!\w)", normalized))
    pairs: dict[str, str] = {}
    for index, match in enumerate(matches):
        key = clean_text(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        value = clean_text(normalized[start:end].strip(" :-|"))
        if key and value:
            pairs.setdefault(key, value)
    return pairs


def _canonical_financial_value(text: str, labels: tuple[str, ...]) -> int | None:
    for label in labels:
        match = re.search(rf"(?i){re.escape(label)}\s*[:+]?\s*((?:CZK|Kč)?\s*\d[\d\s\u00a0\u202f.,]*)", text)
        if match:
            return parse_int_money(match.group(1))
    return None


def _extract_description(soup: BeautifulSoup, h1: Tag | None, characteristics: Tag | None) -> str:
    if h1 is None or characteristics is None:
        return ""
    blocks: list[str] = []
    for tag in h1.find_all_next(["p", "div", "section"]):
        if tag is characteristics or characteristics in tag.parents:
            break
        # Keep leaf content blocks to avoid duplicates.
        if tag.find(["p", "div", "section"], recursive=False):
            continue
        text = clean_text(tag.get_text(" ", strip=True))
        if len(text) < 40:
            continue
        lowered = text.lower()
        if any(marker in lowered for marker in CTA_OR_MARKETING):
            continue
        if any(label in lowered for labels in FINANCIAL_LABELS.values() for label in labels):
            continue
        if text == clean_text(h1.get_text(" ", strip=True)):
            continue
        blocks.append(text)

    # First pass can be empty on highly nested layouts. Fallback to text lines.
    if not blocks:
        all_text = soup.get_text("\n", strip=True)
        before = all_text.split(clean_text(characteristics.get_text(" ", strip=True)), 1)[0]
        after_title = before.split(clean_text(h1.get_text(" ", strip=True)), 1)[-1]
        for line in after_title.splitlines():
            text = clean_text(line)
            lowered = text.lower()
            if len(text) >= 40 and not any(marker in lowered for marker in CTA_OR_MARKETING):
                if not any(label in lowered for labels in FINANCIAL_LABELS.values() for label in labels):
                    blocks.append(text)

    return "\n\n".join(stable_unique(blocks))


def _extract_address(title: str) -> str:
    # English title usually ends with the address after "without real estate".
    for separator in (" without real estate ", " bez realitky ", " without RE "):
        if separator.lower() in title.lower():
            index = title.lower().rfind(separator.lower())
            return clean_text(title[index + len(separator) :])
    # Otherwise retain the tail after the area bullet.
    parts = [clean_text(part) for part in re.split(r"[•|]", title) if clean_text(part)]
    return parts[-1] if parts else ""


def _extract_amenities(section_text: str) -> list[str]:
    lines = [clean_text(line) for line in section_text.splitlines()]
    excluded = {"how far to…:", "how far to...:", "jak daleko…:", "jak daleko...:"}
    result = []
    for line in lines:
        if not line or line.lower() in excluded:
            continue
        if len(line) > 180:
            continue
        result.append(line)
    return stable_unique(result)


def _extract_image_urls(soup: BeautifulSoup, page_url: str) -> list[str]:
    urls: list[str] = []
    for meta in soup.select('meta[property="og:image"], meta[name="twitter:image"]'):
        content = meta.get("content")
        if isinstance(content, str):
            urls.append(absolute_url(page_url, content))
    for img in soup.find_all("img"):
        alt = clean_text(str(img.get("alt") or "")).lower()
        if any(bad in alt for bad in ("logo", "icon", "facebook", "instagram")):
            continue
        for attr in ("src", "data-src"):
            value = img.get(attr)
            if isinstance(value, str) and value and not value.startswith("data:"):
                urls.append(absolute_url(page_url, value))
        srcset = img.get("srcset")
        if isinstance(srcset, str):
            for item in srcset.split(","):
                value = item.strip().split(" ", 1)[0]
                if value:
                    urls.append(absolute_url(page_url, value))
    return stable_unique(urls)


def parse_detail_page(
    html: str,
    page_url: str,
    search_page: int,
    scraped_at_utc: str,
    fallback_status: str = "",
) -> Listing:
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.find("h1")
    title = clean_text(h1.get_text(" ", strip=True)) if isinstance(h1, Tag) else ""
    page_text = clean_text(soup.get_text(" ", strip=True))

    characteristics_heading = _find_heading(soup, SECTION_HEADINGS["characteristics"])
    amenities_heading = _find_heading(soup, SECTION_HEADINGS["amenities"])
    nearby_heading = _find_heading(soup, SECTION_HEADINGS["nearby"])

    characteristics_tags = _section_tags(characteristics_heading, SECTION_HEADINGS["amenities"])
    raw_characteristics = _section_text(characteristics_heading, SECTION_HEADINGS["amenities"])
    characteristics = _extract_generic_pairs(characteristics_tags)
    for key, value in _extract_known_pairs(raw_characteristics).items():
        characteristics.setdefault(key, value)

    raw_amenities = _section_text(amenities_heading, SECTION_HEADINGS["nearby"])
    raw_nearby = _section_text(nearby_heading, SIMILAR_HEADINGS)

    financial_values = {
        field: _canonical_financial_value(page_text, labels)
        for field, labels in FINANCIAL_LABELS.items()
    }

    status = fallback_status
    for candidate in STATUS_WORDS:
        if re.search(rf"(?i)(?<!\w){re.escape(candidate)}(?!\w)", page_text):
            status = candidate
            break
    if "no longer possible to respond" in page_text.lower() or "již není možné reagovat" in page_text.lower():
        status = status or "Inactive"

    return Listing(
        url=page_url,
        search_page=search_page,
        scraped_at_utc=scraped_at_utc,
        title=title,
        address=_extract_address(title),
        status=status,
        description=_extract_description(soup, h1 if isinstance(h1, Tag) else None, characteristics_heading),
        monthly_rent_czk=financial_values["monthly_rent_czk"],
        service_charges_czk=financial_values["service_charges_czk"],
        utility_charges_czk=financial_values["utility_charges_czk"],
        refundable_deposit_czk=financial_values["refundable_deposit_czk"],
        characteristics=characteristics,
        amenities=_extract_amenities(raw_amenities),
        nearby_lines=[clean_text(line) for line in raw_nearby.splitlines() if clean_text(line)],
        image_urls=_extract_image_urls(soup, page_url),
        raw_characteristics_text=raw_characteristics,
        raw_amenities_text=raw_amenities,
        raw_nearby_text=raw_nearby,
        raw_page_text=page_text,
    )
