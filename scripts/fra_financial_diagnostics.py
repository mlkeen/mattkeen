"""Inspect financial exceptions in FRA ETL V2 output CSVs.

Place this file in the Flask project's scripts/ directory, then run:
    python scripts/fra_financial_diagnostics.py

Reads data/processed/{cost_recovery,avoidable_expense,fully_allocated_expense}.csv
and writes data/reports/fra_financial_exceptions.csv. Does not alter input.
No extra dependencies are required.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS = (
    ("cost_recovery", "cost_recovery", "operating_revenue", "allocated_expense"),
    ("avoidable_expense", "avoidable_expense_coverage", "passenger_revenue", "avoidable_expense"),
    ("fully_allocated_expense", "allocated_expense_coverage", "passenger_revenue", "allocated_expense"),
)
FIELDS = (
    "table", "fiscal_year", "fiscal_quarter", "apt_code", "route",
    "reporting_level", "state_payments_included", "ratio_field",
    "reported_ratio", "numerator_field", "numerator", "denominator_field",
    "denominator", "calculated_ratio", "flags", "source_workbook",
    "source_sheet", "source_excel_row",
)


def number(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except ValueError:
        return None


def inspect(data_dir: Path, output_path: Path) -> tuple[int, dict[str, int]]:
    exceptions = []
    negative_ratios = {}
    missing = []
    for table, ratio_col, numerator_col, denominator_col in SPECS:
        path = data_dir / f"{table}.csv"
        if not path.is_file():
            missing.append(str(path))
            continue
        count_negative = 0
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            required = {ratio_col, numerator_col, denominator_col}
            if not required <= set(reader.fieldnames or []):
                raise ValueError(f"{path.name} lacks columns: {sorted(required - set(reader.fieldnames or []))}")
            for row in reader:
                ratio = number(row[ratio_col])
                numerator = number(row[numerator_col])
                denominator = number(row[denominator_col])
                flags = []
                if ratio is not None and ratio < 0:
                    flags.append("negative_reported_ratio")
                    count_negative += 1
                if numerator is not None and numerator < 0:
                    flags.append("negative_numerator")
                if denominator is not None and denominator <= 0:
                    flags.append("nonpositive_denominator")
                calculated = (
                    numerator / denominator
                    if numerator is not None and denominator is not None and denominator != 0
                    else None
                )
                if calculated is not None and ratio is not None:
                    if not math.isclose(calculated, ratio, rel_tol=1e-5, abs_tol=1e-5):
                        flags.append("ratio_disagrees_with_inputs")
                if not flags:
                    continue
                exceptions.append({
                    "table": table,
                    "fiscal_year": row.get("fiscal_year", ""),
                    "fiscal_quarter": row.get("fiscal_quarter", ""),
                    "apt_code": row.get("apt_code", ""),
                    "route": row.get("route", ""),
                    "reporting_level": row.get("reporting_level", ""),
                    "state_payments_included": row.get("state_payments_included", ""),
                    "ratio_field": ratio_col,
                    "reported_ratio": row[ratio_col],
                    "numerator_field": numerator_col,
                    "numerator": row[numerator_col],
                    "denominator_field": denominator_col,
                    "denominator": row[denominator_col],
                    "calculated_ratio": "" if calculated is None else calculated,
                    "flags": ";".join(flags),
                    "source_workbook": row.get("source_workbook", ""),
                    "source_sheet": row.get("source_sheet", ""),
                    "source_excel_row": row.get("source_excel_row", ""),
                })
        negative_ratios[table] = count_negative
    if missing:
        raise FileNotFoundError("Missing processed CSVs. Run fra_etl.py first:\n" + "\n".join(missing))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(exceptions)
    return len(exceptions), negative_ratios


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "processed")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "reports" / "fra_financial_exceptions.csv")
    args = parser.parse_args()
    total, negatives = inspect(args.data, args.out)
    print(f"Wrote {total:,} financial exception rows to {args.out}")
    for table, count in negatives.items():
        print(f"  {table}: {count} negative ratios")
    print("Review source_workbook and source_excel_row before changing any values.")


if __name__ == "__main__":
    main()
