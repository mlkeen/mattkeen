"""Validate and publish the ridership ETL output for the Flask web app.

Run after scripts/fra_etl.py. Unlike raw/processed files, the compact
published CSV is tracked with the app for deployment. Requires stdlib only.
"""
import argparse
import csv
import math
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "ridership.csv"
OUTPUT = ROOT / "app" / "data" / "fra_ridership.csv"


def validate(source):
    records = defaultdict(list)
    aggregate = {}
    seen_keys = set()
    negatives = []
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"fiscal_year", "fiscal_quarter", "apt_code", "route", "reporting_level", "ridership", "source_workbook"}
        absent = required.difference(reader.fieldnames or ())
        if absent:
            raise ValueError(f"Missing required columns: {', '.join(sorted(absent))}")
        for index, row in enumerate(reader, start=2):
            try:
                fy, quarter = int(row["fiscal_year"]), int(row["fiscal_quarter"])
                value = float(row["ridership"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Row {index}: invalid fiscal period or ridership") from exc
            if quarter not in (1, 2, 3, 4) or not math.isfinite(value):
                raise ValueError(f"Row {index}: invalid quarter or nonfinite ridership")
            key = (fy, quarter, row["apt_code"])
            if key in seen_keys:
                raise ValueError(f"Duplicate period and APT code: {key}")
            seen_keys.add(key)
            period = (fy, quarter)
            if row["reporting_level"] == "route":
                records[period].append(value)
                if value < 0:
                    negatives.append((period, row["route"], value))
            elif row["reporting_level"] == "aggregate" and row["apt_code"] == "APT_All_APT":
                aggregate[period] = value
    if not records:
        raise ValueError("No route observations found")
    if set(records) != set(aggregate):
        raise ValueError(f"System totals missing or extra for quarters: {set(records) ^ set(aggregate)}")
    for period in sorted(records):
        difference = sum(records[period]) - aggregate[period]
        if abs(difference) > 0.02:
            raise ValueError(f"FY{period[0]} Q{period[1]}: route sum differs from system total by {difference:,.2f}")
    return len(seen_keys), len(records), negatives


def main():
    parser = argparse.ArgumentParser(description="Validate and publish FRA ridership CSV for Flask")
    parser.add_argument("--source", type=Path, default=INPUT, help="ETL output CSV (default data/processed/ridership.csv)")
    parser.add_argument("--destination", type=Path, default=OUTPUT, help="Published CSV for app")
    args = parser.parse_args()
    if not args.source.is_file():
        parser.error(f"Processed ridership CSV not found: {args.source}. Run scripts/fra_etl.py first.")
    count, quarters, negatives = validate(args.source)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.destination.with_suffix(args.destination.suffix + ".tmp")
    try:
        with args.source.open("rb") as src, temporary.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        temporary.replace(args.destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Published {count:,} records spanning {quarters} fiscal quarters to {args.destination}")
    if negatives:
        print(f"Flagged {len(negatives)} negative route adjustments (kept intact in source, excluded from charts):")
        for (year, quarter), name, value in negatives:
            print(f"  FY{year} Q{quarter} / {name}: {value:,.0f}")
    print("Restart Flask to reload the published data.")


if __name__ == "__main__":
    main()
