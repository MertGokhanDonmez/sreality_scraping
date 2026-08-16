from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .exporter import export_xlsx
from .fetcher import FetchConfig, HttpFetcher
from .scraper import scrape_search

DEFAULT_URL = (
    "https://www.bezrealitky.com/search?estateType=BYT&location=exact&offerType=PRONAJEM"
    "&priceTo=15000&region=486&roommate=false&currency=CZK"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export every public listing from a Bezrealitky search URL to an Excel workbook."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Bezrealitky search-result URL")
    parser.add_argument("--output", default="bezrealitky_listings.xlsx", help="Output .xlsx path")
    parser.add_argument("--delay", type=float, default=0.8, help="Delay between requests in seconds")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    parser.add_argument("--retries", type=int, default=3, help="Retries per page")
    parser.add_argument("--max-pages", type=int, default=None, help="Optional test limit")
    parser.add_argument("--max-listings", type=int, default=None, help="Optional test limit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    if output.suffix.lower() != ".xlsx":
        output = output.with_suffix(".xlsx")

    config = FetchConfig(
        timeout_seconds=args.timeout,
        retries=max(args.retries, 1),
        delay_seconds=max(args.delay, 0),
    )
    try:
        with HttpFetcher(config) as fetcher:
            listings, metadata = scrape_search(
                args.url,
                fetcher,
                max_pages=args.max_pages,
                max_listings=args.max_listings,
                progress=lambda message: print(message, flush=True),
            )
        export_xlsx(listings, output, search_url=args.url, metadata=metadata)
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Saved {len(listings)} listings to {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
