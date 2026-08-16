from pathlib import Path

from bezrealitky_scraper import cli
from bezrealitky_scraper.models import Listing


class DummyFetcher:
    def __init__(self, _config):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return None


def test_cli_writes_xlsx(monkeypatch, tmp_path: Path):
    listing = Listing(
        url="https://example.test/1",
        search_page=1,
        scraped_at_utc="2026-07-30T14:00:00+00:00",
        title="Test listing",
        characteristics={"Listing ID": "1"},
    )
    monkeypatch.setattr(cli, "HttpFetcher", DummyFetcher)
    monkeypatch.setattr(cli, "scrape_search", lambda *args, **kwargs: ([listing], {"scraped_listings": 1}))
    output = tmp_path / "result"
    assert cli.main(["--url", "https://example.test/search", "--output", str(output)]) == 0
    assert output.with_suffix(".xlsx").exists()
