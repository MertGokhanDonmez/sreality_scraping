from pathlib import Path

from bezrealitky_scraper.scraper import scrape_search

FIXTURES = Path(__file__).parent / "fixtures"


class FakeFetcher:
    def __init__(self, responses: dict[str, str]):
        self.responses = responses
        self.calls: list[str] = []

    def get_text(self, url: str) -> str:
        self.calls.append(url)
        try:
            return self.responses[url]
        except KeyError as exc:
            raise AssertionError(f"Unexpected URL: {url}") from exc


def test_scrape_search_deduplicates_and_follows_pages():
    base = "https://www.bezrealitky.com/search?priceTo=15000"
    page2 = "https://www.bezrealitky.com/search?priceTo=15000&page=2"
    detail1 = "https://www.bezrealitky.com/properties-flats-houses/903530-nabidka-pronajem-bytu-kostelecka-praha"
    detail2 = "https://www.bezrealitky.com/properties-flats-houses/903531-nabidka-pronajem-bytu-utulna-praha"
    detail3 = "https://www.bezrealitky.com/properties-flats-houses/903532-nabidka-pronajem-bytu-third"
    search1 = (FIXTURES / "search_page_1.html").read_text(encoding="utf-8").replace("?page=4&priceTo=15000", "?page=2&priceTo=15000")
    search2 = (FIXTURES / "search_page_2.html").read_text(encoding="utf-8")
    detail = (FIXTURES / "detail_en.html").read_text(encoding="utf-8")
    fetcher = FakeFetcher({base: search1, page2: search2, detail1: detail, detail2: detail, detail3: detail})

    listings, metadata = scrape_search(base, fetcher, max_pages=2)
    assert len(listings) == 3
    assert metadata["scraped_pages"] == 2
    assert metadata["scraped_listings"] == 3
    assert fetcher.calls[:2] == [base, page2]


def test_scrape_search_respects_max_listings():
    base = "https://www.bezrealitky.com/search?priceTo=15000"
    detail1 = "https://www.bezrealitky.com/properties-flats-houses/903530-nabidka-pronajem-bytu-kostelecka-praha"
    search1 = (FIXTURES / "search_page_1.html").read_text(encoding="utf-8")
    detail = (FIXTURES / "detail_en.html").read_text(encoding="utf-8")
    fetcher = FakeFetcher({base: search1, detail1: detail})
    listings, metadata = scrape_search(base, fetcher, max_pages=1, max_listings=1)
    assert len(listings) == 1
    assert metadata["scraped_listings"] == 1
