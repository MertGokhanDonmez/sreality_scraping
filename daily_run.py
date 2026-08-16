#!/usr/bin/env python3
"""Cron entry point: scrape Bezrealitky, keep only what's new since the last run,
write it to an .xlsx file and email that file.

State (which listings were already seen) is kept in state/seen_listings.json.
- No state file yet -> this is the first run: the full current result set is
  treated as the baseline and emailed in full.
- State file present -> only listings not seen in any previous run are emailed.

State is only updated after the email is sent successfully, so a failed send
does not lose any listings - they simply show up again as "new" next time.

Configuration is read from environment variables (see .env.example):
  SEARCH_URL          Bezrealitky search-result URL to scrape
  GMAIL_ADDRESS        Gmail account used to send the mail
  GMAIL_APP_PASSWORD   Gmail App Password for that account
  MAIL_TO              Recipient address (defaults to GMAIL_ADDRESS)
"""
from __future__ import annotations

import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from bezrealitky_scraper.exporter import export_xlsx  # noqa: E402
from bezrealitky_scraper.fetcher import FetchConfig, HttpFetcher  # noqa: E402
from bezrealitky_scraper.models import Listing  # noqa: E402
from bezrealitky_scraper.scraper import scrape_search  # noqa: E402

STATE_DIR = ROOT / "state"
STATE_FILE = STATE_DIR / "seen_listings.json"
OUTPUT_DIR = ROOT / "output"

DEFAULT_URL = (
    "https://www.bezrealitky.com/search?estateType=BYT&location=exact&offerType=PRONAJEM"
    "&priceTo=15000&region=486&roommate=false&currency=CZK"
)


def listing_key(listing: Listing) -> str:
    return listing.listing_id or listing.url


def load_previous_keys() -> set[str] | None:
    if not STATE_FILE.exists():
        return None
    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return set(data.get("keys", []))


def save_state(keys: set[str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(
            {"keys": sorted(keys), "updated_at_utc": datetime.now(timezone.utc).isoformat()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def send_email(subject: str, body: str, attachment_path: Path) -> None:
    sender = os.environ["GMAIL_ADDRESS"].strip()
    # Google's App Password screen shows the value grouped with spaces (and copy/paste
    # sometimes carries a non-breaking space, \xa0, instead of a plain one) - strip all
    # whitespace so a straight copy/paste from that screen still works.
    password = "".join(os.environ["GMAIL_APP_PASSWORD"].split())
    recipient = os.environ.get("MAIL_TO", sender).strip()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)
    msg.add_attachment(
        attachment_path.read_bytes(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=attachment_path.name,
    )

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(sender, password)
        smtp.send_message(msg)


def main() -> int:
    search_url = os.environ.get("SEARCH_URL", DEFAULT_URL)
    today = datetime.now().strftime("%Y-%m-%d")

    config = FetchConfig()
    with HttpFetcher(config) as fetcher:
        listings, metadata = scrape_search(
            search_url,
            fetcher,
            progress=lambda message: print(message, flush=True),
        )

    current_keys = {listing_key(listing) for listing in listings}
    previous_keys = load_previous_keys()

    if previous_keys is None:
        to_send = listings
        subject = f"Bezrealitky - ilk calisma - {len(to_send)} ilan - {today}"
        summary = f"Ilk calisma: mevcut {len(to_send)} ilanin tamami baz alindi ve eklendi."
    else:
        to_send = [listing for listing in listings if listing_key(listing) not in previous_keys]
        subject = f"Bezrealitky - {len(to_send)} yeni ilan - {today}"
        summary = (
            f"Bugun {len(to_send)} yeni ilan bulundu "
            f"(taramada toplam {len(listings)} aktif ilan vardi)."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"bezrealitky_{today}.xlsx"
    export_xlsx(to_send, output_path, search_url=search_url, metadata=metadata)

    send_email(subject, summary, output_path)
    save_state(current_keys)

    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
