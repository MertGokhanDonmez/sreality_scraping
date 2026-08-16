from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable

import httpx


class FetchError(RuntimeError):
    pass


@dataclass(slots=True)
class FetchConfig:
    timeout_seconds: float = 30.0
    retries: int = 3
    delay_seconds: float = 0.8
    jitter_seconds: float = 0.25
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 "
        "BezrealitkyExcelExporter/1.0"
    )


class HttpFetcher:
    def __init__(self, config: FetchConfig | None = None, sleep: Callable[[float], None] = time.sleep):
        self.config = config or FetchConfig()
        self._sleep = sleep
        self._client = httpx.Client(
            follow_redirects=True,
            http2=True,
            timeout=self.config.timeout_seconds,
            headers={
                "User-Agent": self.config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,cs;q=0.7",
                "Cache-Control": "no-cache",
            },
        )
        self._request_count = 0

    def __enter__(self) -> "HttpFetcher":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def get_text(self, url: str) -> str:
        if self._request_count:
            delay = self.config.delay_seconds + random.uniform(0, self.config.jitter_seconds)
            self._sleep(max(0, delay))

        last_error: Exception | None = None
        for attempt in range(1, self.config.retries + 1):
            try:
                response = self._client.get(url)
                response.raise_for_status()
                if "text/html" not in response.headers.get("content-type", ""):
                    raise FetchError(f"Unexpected content type for {url}: {response.headers.get('content-type')}")
                text = response.text
                if not text.strip():
                    raise FetchError(f"Empty response from {url}")
                self._request_count += 1
                return text
            except (httpx.HTTPError, FetchError) as exc:
                last_error = exc
                if attempt < self.config.retries:
                    self._sleep(min(2 ** (attempt - 1), 8))
        raise FetchError(f"Failed to fetch {url} after {self.config.retries} attempts: {last_error}")
