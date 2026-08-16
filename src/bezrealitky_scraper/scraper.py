from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from .fetcher import HttpFetcher
from .models import Listing, SearchCard
from .parser import parse_detail_page, parse_search_page
from .utils import with_page

ProgressCallback = Callable[[str], None]


def scrape_search(
    search_url: str,
    fetcher: HttpFetcher,
    *,
    max_pages: int | None = None,
    max_listings: int | None = None,
    progress: ProgressCallback | None = None,
) -> tuple[list[Listing], dict[str, int | None]]:
    progress = progress or (lambda _message: None)

    first_html = fetcher.get_text(with_page(search_url, 1))
    first = parse_search_page(first_html, with_page(search_url, 1), 1)
    total_pages = first.page_count
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    all_cards: list[SearchCard] = list(first.cards)
    progress(f"Search page 1/{total_pages}: {len(first.cards)} listing links")

    for page in range(2, total_pages + 1):
        url = with_page(search_url, page)
        parsed = parse_search_page(fetcher.get_text(url), url, page)
        all_cards.extend(parsed.cards)
        progress(f"Search page {page}/{total_pages}: {len(parsed.cards)} listing links")

    deduped: list[SearchCard] = []
    seen: set[str] = set()
    for card in all_cards:
        if card.url not in seen:
            seen.add(card.url)
            deduped.append(card)

    if max_listings is not None:
        deduped = deduped[:max_listings]

    scraped_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    listings: list[Listing] = []
    for index, card in enumerate(deduped, start=1):
        progress(f"Detail {index}/{len(deduped)}: {card.url}")
        html = fetcher.get_text(card.url)
        listing = parse_detail_page(
            html,
            card.url,
            card.search_page,
            scraped_at,
            fallback_status=card.status,
        )
        if not listing.title:
            raise RuntimeError(f"No listing title found at {card.url}; site markup may have changed")
        listings.append(listing)

    metadata: dict[str, int | None] = {
        "reported_count": first.reported_count,
        "discovered_pages": first.page_count,
        "scraped_pages": total_pages,
        "discovered_unique_links": len(seen),
        "scraped_listings": len(listings),
    }
    return listings, metadata
