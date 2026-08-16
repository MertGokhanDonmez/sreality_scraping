import os

import pytest

from bezrealitky_scraper.fetcher import FetchConfig, HttpFetcher
from bezrealitky_scraper.parser import parse_detail_page, parse_search_page

LIVE_URL = "https://www.bezrealitky.com/search?estateType=BYT&location=exact&offerType=PRONAJEM&priceTo=15000&region=486&roommate=false&currency=CZK"


@pytest.mark.live
@pytest.mark.skipif(os.getenv("RUN_LIVE_TESTS") != "1", reason="Set RUN_LIVE_TESTS=1 to run live HTTP checks")
def test_live_search_and_first_detail():
    with HttpFetcher(FetchConfig(delay_seconds=0.5)) as fetcher:
        search = parse_search_page(fetcher.get_text(LIVE_URL), LIVE_URL, 1)
        assert search.cards
        assert search.reported_count is None or search.reported_count >= len(search.cards)
        first = search.cards[0]
        listing = parse_detail_page(fetcher.get_text(first.url), first.url, 1, "live")
        assert listing.title
        assert listing.monthly_rent_czk is not None
        assert listing.characteristics
