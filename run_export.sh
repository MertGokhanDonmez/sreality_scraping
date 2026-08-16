#!/usr/bin/env bash
set -euo pipefail
python -m bezrealitky_scraper.cli \
  --url "https://www.bezrealitky.com/search?estateType=BYT&location=exact&offerType=PRONAJEM&priceTo=15000&region=486&roommate=false&currency=CZK" \
  --output "bezrealitky_prague_under_15000.xlsx"
