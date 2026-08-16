from pathlib import Path

from bezrealitky_scraper.parser import parse_detail_page

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_english_detail_page_all_major_sections():
    listing = parse_detail_page(
        (FIXTURES / "detail_en.html").read_text(encoding="utf-8"),
        "https://www.bezrealitky.com/properties-flats-houses/903530-test",
        search_page=1,
        scraped_at_utc="2026-07-30T14:00:00+00:00",
        fallback_status="New",
    )
    assert listing.listing_id == "903530"
    assert listing.address == "Kostelecká, Prague - Čakovice"
    assert listing.monthly_rent_czk == 13000
    assert listing.service_charges_czk == 1500
    assert listing.utility_charges_czk == 500
    assert listing.refundable_deposit_czk == 20000
    assert listing.total_monthly_known_czk == 15000
    assert listing.characteristics["Building construction"] == "Brick"
    assert listing.characteristics["Usable area"] == "28 m²"
    assert listing.amenities == ["Parking", "Balcony 3 m²", "Lift"]
    assert "Nabízím k dlouhodobému" in listing.description
    assert "Communicate all private owners" not in listing.description
    assert listing.nearby_lines[:2] == ["Public transport Čakovice", "152 m (2 min)"]
    assert listing.image_urls[0].endswith("/media/photo-main.jpg")


def test_parse_czech_detail_page_and_missing_utility_charge():
    listing = parse_detail_page(
        (FIXTURES / "detail_cs.html").read_text(encoding="utf-8"),
        "https://www.bezrealitky.cz/nemovitosti-byty-domy/958496-test",
        search_page=2,
        scraped_at_utc="2026-07-30T14:00:00+00:00",
    )
    assert listing.listing_id == "958496"
    assert listing.monthly_rent_czk == 15000
    assert listing.service_charges_czk == 2000
    assert listing.utility_charges_czk is None
    assert listing.refundable_deposit_czk == 30000
    assert listing.characteristics["Užitná plocha"] == "42 m²"
    assert listing.amenities == ["Parkování", "Sklep 4 m²"]
    assert "útulný a světlý byt" in listing.description
