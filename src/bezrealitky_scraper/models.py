from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class SearchCard:
    url: str
    search_page: int
    title: str = ""
    status: str = ""
    summary_text: str = ""


@dataclass(slots=True)
class Listing:
    url: str
    search_page: int
    scraped_at_utc: str
    title: str = ""
    address: str = ""
    status: str = ""
    description: str = ""
    monthly_rent_czk: int | None = None
    service_charges_czk: int | None = None
    utility_charges_czk: int | None = None
    refundable_deposit_czk: int | None = None
    characteristics: dict[str, str] = field(default_factory=dict)
    amenities: list[str] = field(default_factory=list)
    nearby_lines: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    raw_characteristics_text: str = ""
    raw_amenities_text: str = ""
    raw_nearby_text: str = ""
    raw_page_text: str = ""

    @property
    def listing_id(self) -> str:
        for key in ("Listing ID", "Číslo inzerátu"):
            if value := self.characteristics.get(key):
                return value
        return ""

    @property
    def total_monthly_known_czk(self) -> int | None:
        values = [
            self.monthly_rent_czk,
            self.service_charges_czk,
            self.utility_charges_czk,
        ]
        present = [value for value in values if value is not None]
        return sum(present) if present else None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["listing_id"] = self.listing_id
        result["total_monthly_known_czk"] = self.total_monthly_known_czk
        return result
