"""Validate FRA route-level customer OTP CSV and publish to Flask.

Do NOT average train-level C OTP to make a route-level result.
Run: .\\.venv\\Scripts\\python.exe scripts\\publish_customer_otp.py
"""
from __future__ import annotations

import argparse
import csv
import math
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "customer_otp_route.csv"
OUTPUT = ROOT / "app" / "data" / "fra_customer_otp_route.csv"


def validate(source):
    seen = set()
    periods = set()
    blanks = 0
    count = 0
    with source.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"fiscal_year", "fiscal_quarter", "service", "sub_service", "customer_otp", "source_workbook", "source_sheet", "source_excel_row"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing OTP fields: {sorted(missing)}")
        for line, row in enumerate(reader, start=2):
            count += 1
            try:
                fy, fq = int(row["fiscal_year"]), int(row["fiscal_quarter"])
                if fq not in (1,2,3,4) or fy < 2000:
                    raise ValueError("invalid fiscal period")
                service, subservice = row["service"].strip(), row["sub_service"].strip()
                if not service or not subservice:
                    raise ValueError("missing service/subservice")
                key = (fy, fq, service, subservice)
                if key in seen:
                    raise ValueError("duplicate fiscal quarter + service/subservice")
                seen.add(key)
                if not row["source_workbook"] or not row["source_sheet"] or not row["source_excel_row"]:
                    raise ValueError("missing source provenance")
                raw = row["customer_otp"].strip()
                if raw:
                    otp = float(raw)
                    if not math.isfinite(otp) or not 0 <= otp <= 1:
                        raise ValueError("customer OTP must be a proportion in [0,1]")
                else:
                    blanks += 1
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid OTP CSV row {line}: {exc}") from exc
            periods.add((fy, fq))
    if not seen:
        raise ValueError("No route-level OTP records found")
    return {"records": count, "quarters": len(periods), "blanks": blanks, "periods": sorted(periods)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=INPUT)
    parser.add_argument("--destination", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if not args.source.is_file():
        parser.error(f"Missing {args.source}. Run scripts/fra_etl.py first.")
    result = validate(args.source)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.destination.with_suffix(args.destination.suffix + ".tmp")
    try:
        with args.source.open("rb") as src, temporary.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        temporary.replace(args.destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Published {result['records']:,} route-level OTP rows across {result['quarters']} quarters")
    print(f"Missing OTP values (retained, not zero-filled): {result['blanks']}")
    print(f"Published CSV: {args.destination}")
    print("Restart Flask to refresh the data cache.")


if __name__ == "__main__":
    main()
