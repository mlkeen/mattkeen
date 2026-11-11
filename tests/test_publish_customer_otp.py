import csv

import pytest
from scripts.publish_customer_otp import validate

FIELDS = ["fiscal_year", "fiscal_quarter", "service", "sub_service", "customer_otp", "source_workbook", "source_sheet", "source_excel_row"]


def rows():
    return [
        {"fiscal_year": "2022", "fiscal_quarter": "1", "service": "Downeaster", "sub_service": "Downeaster", "customer_otp": "0.77", "source_workbook": "FY22 Q1 Customer OTP.xlsx", "source_sheet": "Route Level C OTP", "source_excel_row": "17"},
        {"fiscal_year": "2022", "fiscal_quarter": "2", "service": "Downeaster", "sub_service": "Downeaster", "customer_otp": "0.81", "source_workbook": "FY22 Q2 Customer OTP.xlsx", "source_sheet": "Route Level C OTP", "source_excel_row": "19"},
    ]


def write(path, entries):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(entries)


def test_valid_publication_extract(tmp_path):
    path = tmp_path / "otp.csv"
    write(path, rows())
    assert validate(path) == {"records": 2, "quarters": 2, "blanks": 0, "periods": [(2022, 1), (2022, 2)]}


def test_missing_otp_is_retained_as_missing(tmp_path):
    path = tmp_path / "otp.csv"
    entries = rows()
    entries[0]["customer_otp"] = ""
    write(path, entries)
    assert validate(path)["blanks"] == 1


@pytest.mark.parametrize("bad", ["-0.01", "1.01", "inf", "nan", "eighty percent"])
def test_rejects_invalid_otp(tmp_path, bad):
    path = tmp_path / "otp.csv"
    entries = rows()
    entries[0]["customer_otp"] = bad
    write(path, entries)
    with pytest.raises(ValueError, match="Invalid OTP"):
        validate(path)


def test_duplicate_grain_rejected(tmp_path):
    path = tmp_path / "otp.csv"
    entries = rows()
    entries.append(entries[0].copy())
    write(path, entries)
    with pytest.raises(ValueError, match="duplicate"):
        validate(path)
