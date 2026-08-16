from pathlib import Path

from bezrealitky_scraper.parser import parse_search_page

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_search_page_excludes_similar_offers():
    html = (FIXTURES / "search_page_1.html").read_text(encoding="utf-8")
    result = parse_search_page(html, "https://www.bezrealitky.com/search?priceTo=15000", 1)
    assert [card.url for card in result.cards] == [
        "https://www.bezrealitky.com/properties-flats-houses/903530-nabidka-pronajem-bytu-kostelecka-praha",
        "https://www.bezrealitky.com/properties-flats-houses/903531-nabidka-pronajem-bytu-utulna-praha",
    ]
    assert result.cards[0].status == "New"
    assert result.page_count == 4
    assert result.reported_count == 3


def test_parse_search_page_absolute_links_and_no_pagination():
    html = (FIXTURES / "search_page_2.html").read_text(encoding="utf-8")
    result = parse_search_page(html, "https://www.bezrealitky.com/search?page=2", 2)
    assert len(result.cards) == 1
    assert result.cards[0].status == "Reserved"
    assert result.page_count == 1
