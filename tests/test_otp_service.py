"""Integration tests use a deliberately tiny representative OTP extract.

The user's actual 868-row OTP data are local, not bundled in this release.
"""
import csv

import pytest
from app import create_app
from app import otp_service

FIELDS = ["fiscal_year", "fiscal_quarter", "service", "sub_service", "customer_otp", "source_workbook", "source_sheet", "source_excel_row"]


@pytest.fixture()
def otp_fixture(tmp_path, monkeypatch):
    source = tmp_path / "published_otp.csv"
    rows = [
        (2022, 1, "Downeaster", "Downeaster", "0.7"),
        (2025, 3, "Downeaster", "Downeaster", "0.6"),
        (2026, 3, "Downeaster", "Downeaster", "0.8"),
        (2026, 3, "Northeast Regional", "On Spine Northeast Regional", "0.9"),
        (2026, 3, "Northeast Regional", "Richmond / Newport News / Norfolk", "0.4"),
    ]
    with source.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        for year, quarter, service, subservice, value in rows:
            writer.writerow({"fiscal_year":year,"fiscal_quarter":quarter,"service":service,"sub_service":subservice,"customer_otp":value,"source_workbook": "synthetic.xlsx", "source_sheet":"Route Level C OTP", "source_excel_row": 4})
    monkeypatch.setattr(otp_service, "PUBLISHED_OTP", source)
    otp_service._load.cache_clear()
    yield
    otp_service._load.cache_clear()


def test_exact_match_and_auditable_gap(otp_fixture):
    r = otp_service.get_otp_match("Downeaster")
    assert r is not None
    assert r["latest_otp"] == pytest.approx(.8)
    assert r["yoy_pp"] == pytest.approx(20)
    assert r["quarters_valid"] == 3
    assert r["series"][0]["period"] == "FY2021 Q4"
    assert r["series"][0]["otp"] is None
    assert r["series"][0]["status"] == "not_reported"
    assert r["series"][-1]["source_workbook"] == "synthetic.xlsx"
    assert len(r["series"]) == 20


def test_no_unweighted_aggregation_or_fake_route_mapping(otp_fixture):
    assert otp_service.get_otp_match("Northeast Regional") is None
    assert otp_service.get_otp_match("On Spine Northeast Regional") is None
    services = otp_service.get_otp_overview()["services"]
    assert len(services) == 3


def test_route_page_and_otp_api(otp_fixture):
    app = create_app({"TESTING":True})
    client = app.test_client()
    payload = client.get("/api/rail/routes/downeaster").get_json()
    assert payload["otp"]["latest_otp"] == pytest.approx(.8)
    assert client.get("/api/rail/routes/northeast-regional").get_json()["otp"] is None
    assert client.get("/api/rail/otp/routes").get_json()["available"] is True
    url = "/api/rail/otp/routes/" + payload["otp"]["slug"]
    assert client.get(url).get_json()["series"][-1]["otp"] == pytest.approx(.8)
    assert b"Customer OTP observations" in client.get("/projects/intercity-rail/routes/downeaster").data
    assert b"otp-route-select" in client.get("/projects/intercity-rail").data
