from __future__ import annotations

import json
import re
from pathlib import Path

import xlsxwriter

from .models import Listing
from .utils import clean_text, slugify_column

FIXED_HEADERS = [
    "listing_id",
    "title",
    "address",
    "status",
    "monthly_rent_czk",
    "service_charges_czk",
    "utility_charges_czk",
    "total_monthly_known_czk",
    "refundable_deposit_czk",
    "search_page",
    "scraped_at_utc",
    "description",
    "amenities_all",
    "nearby_all",
    "image_count",
    "image_urls_all",
    "listing_url",
]


def _amenity_parts(value: str) -> tuple[str, str]:
    match = re.match(r"^(.*?)(\s+\d+(?:[.,]\d+)?\s*(?:m²|m2))$", clean_text(value), re.I)
    if match:
        return clean_text(match.group(1)), clean_text(match.group(2))
    return clean_text(value), "Yes"


def _unique_header(prefix: str, label: str, used: set[str]) -> str:
    base = f"{prefix}{slugify_column(label)}"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def build_flat_rows(listings: list[Listing]) -> tuple[list[str], list[dict[str, object]], dict[str, str], dict[str, str]]:
    characteristic_labels = sorted({key for listing in listings for key in listing.characteristics})
    amenity_labels = sorted({_amenity_parts(item)[0] for listing in listings for item in listing.amenities})

    used = set(FIXED_HEADERS)
    characteristic_columns = {
        label: _unique_header("char__", label, used) for label in characteristic_labels
    }
    amenity_columns = {
        label: _unique_header("amenity__", label, used) for label in amenity_labels
    }
    headers = FIXED_HEADERS + list(characteristic_columns.values()) + list(amenity_columns.values())

    rows: list[dict[str, object]] = []
    for listing in listings:
        row: dict[str, object] = {
            "listing_id": listing.listing_id,
            "title": listing.title,
            "address": listing.address,
            "status": listing.status,
            "monthly_rent_czk": listing.monthly_rent_czk,
            "service_charges_czk": listing.service_charges_czk,
            "utility_charges_czk": listing.utility_charges_czk,
            "total_monthly_known_czk": listing.total_monthly_known_czk,
            "refundable_deposit_czk": listing.refundable_deposit_czk,
            "search_page": listing.search_page,
            "scraped_at_utc": listing.scraped_at_utc,
            "description": listing.description,
            "amenities_all": " | ".join(listing.amenities),
            "nearby_all": " | ".join(listing.nearby_lines),
            "image_count": len(listing.image_urls),
            "image_urls_all": "\n".join(listing.image_urls),
            "listing_url": listing.url,
        }
        for label, column in characteristic_columns.items():
            row[column] = listing.characteristics.get(label, "")
        amenity_values = {_amenity_parts(item)[0]: _amenity_parts(item)[1] for item in listing.amenities}
        for label, column in amenity_columns.items():
            row[column] = amenity_values.get(label, "")
        rows.append(row)
    return headers, rows, characteristic_columns, amenity_columns


def _set_widths(worksheet, headers: list[str], rows: list[dict[str, object]]) -> None:
    for col, header in enumerate(headers):
        if header == "description":
            width = 55
        elif header in {"nearby_all", "image_urls_all"}:
            width = 38
        elif header in {"title", "address", "amenities_all"}:
            width = 32
        elif header == "listing_url":
            width = 24
        else:
            max_len = max([len(header)] + [len(str(row.get(header, "") or "")) for row in rows[:200]])
            width = min(max(max_len + 2, 11), 28)
        worksheet.set_column(col, col, width)


def export_xlsx(
    listings: list[Listing],
    output_path: str | Path,
    *,
    search_url: str,
    metadata: dict[str, int | None] | None = None,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = metadata or {}

    headers, rows, characteristic_columns, amenity_columns = build_flat_rows(listings)

    workbook = xlsxwriter.Workbook(output)
    workbook.set_properties(
        {
            "title": "Bezrealitky search export",
            "subject": search_url,
            "author": "Bezrealitky Excel Scraper",
            "comments": "Public listing data exported from the supplied search URL.",
        }
    )
    header_fmt = workbook.add_format(
        {"bold": True, "font_color": "white", "bg_color": "#1F4E78", "border": 1, "valign": "vcenter"}
    )
    text_fmt = workbook.add_format({"valign": "top"})
    wrap_fmt = workbook.add_format({"valign": "top", "text_wrap": True})
    money_fmt = workbook.add_format({"num_format": '#,##0 "CZK"', "valign": "top"})
    url_fmt = workbook.get_default_url_format()

    ws = workbook.add_worksheet("Listings")
    ws.freeze_panes(1, 4)
    ws.set_row(0, 26)
    for col, header in enumerate(headers):
        ws.write(0, col, header, header_fmt)

    money_headers = {
        "monthly_rent_czk",
        "service_charges_czk",
        "utility_charges_czk",
        "total_monthly_known_czk",
        "refundable_deposit_czk",
    }
    wrap_headers = {"description", "amenities_all", "nearby_all", "image_urls_all"}

    for row_index, row in enumerate(rows, start=1):
        for col_index, header in enumerate(headers):
            value = row.get(header, "")
            if header == "listing_url" and value:
                ws.write_url(row_index, col_index, str(value), url_fmt, "Open listing")
            elif header in money_headers and isinstance(value, (int, float)):
                ws.write_number(row_index, col_index, value, money_fmt)
            elif header in wrap_headers:
                ws.write(row_index, col_index, value, wrap_fmt)
            else:
                ws.write(row_index, col_index, value, text_fmt)
        ws.set_row(row_index, 48)

    _set_widths(ws, headers, rows)
    if rows:
        ws.add_table(0, 0, len(rows), len(headers) - 1, {
            "name": "BezrealitkyListings",
            "columns": [{"header": header} for header in headers],
            "style": "Table Style Medium 2",
        })
        total_col = headers.index("total_monthly_known_czk")
        ws.conditional_format(1, total_col, len(rows), total_col, {"type": "3_color_scale"})
    else:
        ws.autofilter(0, 0, 0, len(headers) - 1)

    amenities_ws = workbook.add_worksheet("Amenities")
    amenity_headers = ["listing_id", "title", "amenity", "value", "listing_url"]
    for col, header in enumerate(amenity_headers):
        amenities_ws.write(0, col, header, header_fmt)
    amenity_row = 1
    for listing in listings:
        for amenity in listing.amenities:
            name, value = _amenity_parts(amenity)
            amenities_ws.write_row(amenity_row, 0, [listing.listing_id, listing.title, name, value], text_fmt)
            amenities_ws.write_url(amenity_row, 4, listing.url, url_fmt, "Open listing")
            amenity_row += 1
    amenities_ws.freeze_panes(1, 0)
    amenities_ws.autofilter(0, 0, max(amenity_row - 1, 1), len(amenity_headers) - 1)
    amenities_ws.set_column(0, 0, 14)
    amenities_ws.set_column(1, 1, 40)
    amenities_ws.set_column(2, 3, 24)
    amenities_ws.set_column(4, 4, 18)

    nearby_ws = workbook.add_worksheet("Nearby")
    nearby_headers = ["listing_id", "title", "line_order", "nearby_text", "listing_url"]
    for col, header in enumerate(nearby_headers):
        nearby_ws.write(0, col, header, header_fmt)
    nearby_row = 1
    for listing in listings:
        for order, line in enumerate(listing.nearby_lines, start=1):
            nearby_ws.write_row(nearby_row, 0, [listing.listing_id, listing.title, order, line], text_fmt)
            nearby_ws.write_url(nearby_row, 4, listing.url, url_fmt, "Open listing")
            nearby_row += 1
    nearby_ws.freeze_panes(1, 0)
    nearby_ws.autofilter(0, 0, max(nearby_row - 1, 1), len(nearby_headers) - 1)
    nearby_ws.set_column(0, 0, 14)
    nearby_ws.set_column(1, 1, 40)
    nearby_ws.set_column(2, 2, 12)
    nearby_ws.set_column(3, 3, 50)
    nearby_ws.set_column(4, 4, 18)

    images_ws = workbook.add_worksheet("Images")
    image_headers = ["listing_id", "title", "image_order", "image_url", "listing_url"]
    for col, header in enumerate(image_headers):
        images_ws.write(0, col, header, header_fmt)
    image_row = 1
    for listing in listings:
        for order, image_url in enumerate(listing.image_urls, start=1):
            images_ws.write_row(image_row, 0, [listing.listing_id, listing.title, order], text_fmt)
            images_ws.write_url(image_row, 3, image_url, url_fmt, image_url)
            images_ws.write_url(image_row, 4, listing.url, url_fmt, "Open listing")
            image_row += 1
    images_ws.freeze_panes(1, 0)
    images_ws.autofilter(0, 0, max(image_row - 1, 1), len(image_headers) - 1)
    images_ws.set_column(0, 0, 14)
    images_ws.set_column(1, 1, 40)
    images_ws.set_column(2, 2, 12)
    images_ws.set_column(3, 3, 70)
    images_ws.set_column(4, 4, 18)

    raw_ws = workbook.add_worksheet("Raw")
    raw_headers = [
        "listing_id",
        "listing_url",
        "characteristics_json",
        "amenities_json",
        "nearby_json",
        "raw_characteristics_text",
        "raw_amenities_text",
        "raw_nearby_text",
        "raw_page_text",
    ]
    for col, header in enumerate(raw_headers):
        raw_ws.write(0, col, header, header_fmt)
    for row_index, listing in enumerate(listings, start=1):
        values = [
            listing.listing_id,
            listing.url,
            json.dumps(listing.characteristics, ensure_ascii=False, sort_keys=True),
            json.dumps(listing.amenities, ensure_ascii=False),
            json.dumps(listing.nearby_lines, ensure_ascii=False),
            listing.raw_characteristics_text,
            listing.raw_amenities_text,
            listing.raw_nearby_text,
            listing.raw_page_text,
        ]
        for col_index, value in enumerate(values):
            if col_index == 1:
                raw_ws.write_url(row_index, col_index, str(value), url_fmt, "Open listing")
            else:
                raw_ws.write(row_index, col_index, value, wrap_fmt)
        raw_ws.set_row(row_index, 80)
    raw_ws.freeze_panes(1, 0)
    raw_ws.set_column(0, 0, 14)
    raw_ws.set_column(1, 1, 20)
    raw_ws.set_column(2, 8, 55)

    info_ws = workbook.add_worksheet("Run_Info")
    info_ws.write_row(0, 0, ["key", "value"], header_fmt)
    info_rows: list[tuple[str, object]] = [
        ("search_url", search_url),
        ("listing_rows", len(listings)),
        ("dynamic_characteristic_columns", len(characteristic_columns)),
        ("dynamic_amenity_columns", len(amenity_columns)),
    ] + sorted(metadata.items())
    for row_index, (key, value) in enumerate(info_rows, start=1):
        info_ws.write(row_index, 0, key, text_fmt)
        if key == "search_url":
            info_ws.write_url(row_index, 1, str(value), url_fmt, str(value))
        else:
            info_ws.write(row_index, 1, value, text_fmt)
    info_ws.set_column(0, 0, 34)
    info_ws.set_column(1, 1, 100)

    workbook.close()
    return output
