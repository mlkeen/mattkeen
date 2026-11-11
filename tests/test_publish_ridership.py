import csv
from pathlib import Path

import pytest
from scripts.publish_ridership import validate


def write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["fiscal_year", "fiscal_quarter", "apt_code", "route", "reporting_level", "ridership", "source_workbook"])
        writer.writeheader()
        writer.writerows(rows)


def sample_rows():
    return [
        dict(fiscal_year=2025, fiscal_quarter=1, apt_code="APT_All_APT", route="System", reporting_level="aggregate", ridership=150, source_workbook="x.xlsx"),
        dict(fiscal_year=2025, fiscal_quarter=1, apt_code="APT_RT_01", route="Example", reporting_level="route", ridership=100, source_workbook="x.xlsx"),
        dict(fiscal_year=2025, fiscal_quarter=1, apt_code="APT_RT_02", route="Other", reporting_level="route", ridership=50, source_workbook="x.xlsx"),
    ]


def test_valid_data(tmp_path):
    path = tmp_path / "source.csv"
    write_rows(path, sample_rows())
    count, quarters, negatives = validate(path)
    assert (count, quarters, negatives) == (3, 1, [])


def test_duplicate_route_quarter_fails(tmp_path):
    path = tmp_path / "source.csv"
    rows = sample_rows()
    rows.append(rows[-1].copy())
    write_rows(path, rows)
    with pytest.raises(ValueError, match="Duplicate"):
        validate(path)


def test_unbalanced_totals_fail(tmp_path):
    path = tmp_path / "source.csv"
    rows = sample_rows()
    rows[-1]["ridership"] = 60
    write_rows(path, rows)
    with pytest.raises(ValueError, match="differs"):
        validate(path)
