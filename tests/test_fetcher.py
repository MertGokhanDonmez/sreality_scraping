import httpx
import pytest

from bezrealitky_scraper.fetcher import FetchConfig, FetchError, HttpFetcher


def test_fetcher_retries_then_succeeds(monkeypatch):
    calls = {"count": 0}

    def fake_get(_url):
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.ConnectError("temporary")
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text="<html>ok</html>", request=httpx.Request("GET", _url))

    sleeps = []
    fetcher = HttpFetcher(FetchConfig(retries=2, delay_seconds=0, jitter_seconds=0), sleep=sleeps.append)
    monkeypatch.setattr(fetcher._client, "get", fake_get)
    try:
        assert fetcher.get_text("https://example.test") == "<html>ok</html>"
    finally:
        fetcher.close()
    assert calls["count"] == 2
    assert sleeps == [1]


def test_fetcher_rejects_non_html(monkeypatch):
    response = httpx.Response(200, headers={"content-type": "application/json"}, text="{}", request=httpx.Request("GET", "https://example.test"))
    fetcher = HttpFetcher(FetchConfig(retries=1, delay_seconds=0, jitter_seconds=0), sleep=lambda _: None)
    monkeypatch.setattr(fetcher._client, "get", lambda _url: response)
    try:
        with pytest.raises(FetchError):
            fetcher.get_text("https://example.test")
    finally:
        fetcher.close()
