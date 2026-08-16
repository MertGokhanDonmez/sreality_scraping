from pathlib import Path
from zipfile import ZipFile

from bezrealitky_scraper.exporter import build_flat_rows, export_xlsx
from bezrealitky_scraper.models import Listing


def sample_listing() -> Listing:
    return Listing(
        url="https://www.bezrealitky.com/properties-flats-houses/903530-test",
        search_page=1,
        scraped_at_utc="2026-07-30T14:00:00+00:00",
        title="Flat to rent Studio • 28 m²",
        address="Kostelecká, Prague - Čakovice",
        status="New",
        description="Long owner description.",
        monthly_rent_czk=13000,
        service_charges_czk=1500,
        utility_charges_czk=500,
        refundable_deposit_czk=20000,
        characteristics={"Listing ID": "903530", "Usable area": "28 m²", "Floor": "2 of 3"},
        amenities=["Parking", "Balcony 3 m²"],
        nearby_lines=["Shop Lidl", "400 m (5 min)"],
        image_urls=["https://img.test/1.jpg", "https://img.test/2.jpg"],
        raw_page_text="raw",
    )


def test_build_flat_rows_has_dynamic_columns():
    headers, rows, characteristic_columns, amenity_columns = build_flat_rows([sample_listing()])
    assert "char__listing_id" in headers
    assert "amenity__parking" in headers
    assert rows[0][characteristic_columns["Usable area"]] == "28 m²"
    assert rows[0][amenity_columns["Balcony"]] == "3 m²"


def test_export_xlsx_creates_valid_workbook(tmp_path: Path):
    output = tmp_path / "export.xlsx"
    export_xlsx([sample_listing()], output, search_url="https://example.test/search", metadata={"scraped_listings": 1})
    assert output.exists()
    assert output.stat().st_size > 5000
    with ZipFile(output) as archive:
        names = set(archive.namelist())
        assert "xl/workbook.xml" in names
        assert "xl/worksheets/sheet1.xml" in names
        workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
        assert "Listings" in workbook_xml
        assert "Amenities" in workbook_xml
        assert "Run_Info" in workbook_xml
