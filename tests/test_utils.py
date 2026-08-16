from bezrealitky_scraper.utils import clean_text, parse_int_money, stable_unique, with_page


def test_clean_text_normalizes_spaces():
    assert clean_text("  CZK\u00a013,000\n ") == "CZK 13,000"


def test_parse_int_money_formats():
    assert parse_int_money("CZK 13,000") == 13000
    assert parse_int_money("15 000 Kč") == 15000
    assert parse_int_money("348,84 Kč") == 349
    assert parse_int_money(None) is None
    assert parse_int_money("no money") is None


def test_with_page_preserves_query_and_removes_page_one():
    url = "https://x.test/search?priceTo=15000&page=7&currency=CZK"
    assert with_page(url, 1) in {
        "https://x.test/search?priceTo=15000&currency=CZK",
        "https://x.test/search?currency=CZK&priceTo=15000",
    }
    assert "page=3" in with_page(url, 3)
    assert "priceTo=15000" in with_page(url, 3)


def test_stable_unique_keeps_order():
    assert stable_unique(["a", "b", "a", "", "c"]) == ["a", "b", "c"]
