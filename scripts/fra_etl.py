"""FRA historical XLSX -> auditable, typed CSV data tables.

Usage: python scripts/fra_etl.py [--raw PATH] [--out PATH] [--reports PATH]

Original workbooks are read-only.  The script recognizes the FY21 Q4--FY26 Q3
workbook families in the supplied FRA inventory.  Unknown files/sheets, schema
changes, period mismatches, and duplicate data keys are reported, not guessed.
No cross-family service-name joins or rate aggregations are performed here.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PERIOD_RE = re.compile(r"\bFY\s*(20\d{2}|\d{2})\s*Q\s*([1-4])\b", re.I)

# Underlying values are proportions (0..1), not percent units (0..100).
FAMILY_SHEETS = {
    "financial": {
        "Average & Total Ridership": "ridership",
        "Cost Recovery": "cost_recovery",
        "Avoidable Op Exp by Psgr Rev": "avoidable_expense",
        "FullyAllocated Exp by PsgrRev": "fully_allocated_expense",
    },
    "otp": {
        "Route Level C OTP": "customer_otp_route",
        "Train Level C OTP": "customer_otp_train",
        "Train Level C OTP-for report": "customer_otp_train",
    },
    "delay_detail": {"DelayandMileage": "delay_by_code"},
    "delay_rate": {"DelayandMileage": "delay_rates_by_host"},
    "station": {"Station Performance": "station_performance"},
    "host_runtime": {"Host Summary": "host_runtime"},
    "disputed": {"Summary": "disputed_delay_summary"},
}

# Expected source column names are normalized to stable snake-case fields.
ALIASES = {
    "fy": "fiscal_year", "fiscal year": "fiscal_year",
    "quarter": "fiscal_quarter", "fiscal quarter": "fiscal_quarter",
    "apt code": "apt_code", "route": "route", "service": "service",
    "service name": "service", "transportation service name": "service",
    "sub service": "sub_service", "sub service name": "sub_service",
    "transportation sub service name": "sub_service",
    "service line": "service_line", "business line name": "service_line",
    "train number": "train_number", "host railroad name": "host_railroad",
    "host railroad": "host_railroad", "host code": "host_code",
    "host railroad code": "host_code", "delay responsibility": "responsibility",
    "delay code": "delay_code", "delay minutes": "delay_minutes",
    "host railroad train miles": "host_train_miles", "train miles": "train_miles",
    "delay per 10k train miles": "delay_per_10k_train_miles",
    "passenger miles": "passenger_miles", "average ridership": "average_ridership",
    "total ridership mktg": "ridership", "adjusted operating revenue": "operating_revenue",
    "fully allocated adjusted operating expense": "allocated_expense",
    "fully allocated adj operating expense": "allocated_expense",
    "avoidable operating expense": "avoidable_expense",
    "cost recovery": "cost_recovery",
    "adjusted with state operating payments": "state_payments_included",
    "passenger revenue": "passenger_revenue",
    "avoidable operating exp covered by passenger revenue": "avoidable_expense_coverage",
    "fully allocated adj operating exp covered by passenger revenue": "allocated_expense_coverage",
    "c otp": "customer_otp", "arrival station code": "station_code",
    "arrival station name": "station_name",
    "total detraining customers": "detraining_customers",
    "late detraining customers": "late_detraining_customers",
    "avg min late lt cs": "avg_minutes_late_late_customers",
    "disputed delay minutes": "disputed_delay_minutes",
    "unresolved disputed delay minutes": "unresolved_disputed_delay_minutes",
    "average actual run time minutes": "mean_actual_runtime_min",
    "median actual run time minutes": "median_actual_runtime_min",
    "average scheduled run time minutes": "mean_scheduled_runtime_min",
    "average actual run time minutes 1 2": "mean_actual_runtime_min",
    "median actual run time minutes 1 2": "median_actual_runtime_min",
    "average scheduled run time minutes 1": "mean_scheduled_runtime_min",
}

REQUIRED = {
    "ridership": {"fiscal_year", "fiscal_quarter", "apt_code", "route", "ridership", "passenger_miles", "train_miles"},
    "cost_recovery": {"fiscal_year", "fiscal_quarter", "apt_code", "route", "operating_revenue", "allocated_expense", "cost_recovery"},
    "avoidable_expense": {"fiscal_year", "fiscal_quarter", "apt_code", "route", "state_payments_included", "avoidable_expense", "passenger_revenue"},
    "fully_allocated_expense": {"fiscal_year", "fiscal_quarter", "apt_code", "route", "state_payments_included", "allocated_expense", "passenger_revenue"},
    "customer_otp_route": {"fiscal_year", "fiscal_quarter", "service", "sub_service", "customer_otp"},
    "customer_otp_train": {"fiscal_year", "fiscal_quarter", "service", "sub_service", "train_number", "customer_otp"},
    "delay_by_code": {"fiscal_year", "fiscal_quarter", "service", "sub_service", "train_number", "host_code", "responsibility", "delay_code", "delay_minutes", "host_train_miles"},
    "delay_rates_by_host": {"fiscal_year", "fiscal_quarter", "service", "sub_service", "host_code", "responsibility", "delay_minutes", "train_miles", "delay_per_10k_train_miles"},
    "station_performance": {"fiscal_year", "fiscal_quarter", "service", "sub_service", "train_number", "station_code", "detraining_customers", "late_detraining_customers"},
    "host_runtime": {"fiscal_year", "fiscal_quarter", "service", "sub_service", "train_number", "host_code"},
    "disputed_delay_summary": {"host_railroad", "disputed_delay_minutes", "unresolved_disputed_delay_minutes"},
}
NUMERIC = {
    "customer_otp", "ridership", "passenger_miles", "train_miles", "average_ridership",
    "operating_revenue", "allocated_expense", "avoidable_expense", "passenger_revenue",
    "cost_recovery", "avoidable_expense_coverage", "allocated_expense_coverage",
    "delay_minutes", "host_train_miles", "delay_per_10k_train_miles",
    "detraining_customers", "late_detraining_customers", "avg_minutes_late_late_customers",
    "disputed_delay_minutes", "unresolved_disputed_delay_minutes",
    "mean_actual_runtime_min", "median_actual_runtime_min", "mean_scheduled_runtime_min",
}
KEYS = {
    "ridership": ["fiscal_year", "fiscal_quarter", "apt_code"],
    "cost_recovery": ["fiscal_year", "fiscal_quarter", "apt_code"],
    "avoidable_expense": ["fiscal_year", "fiscal_quarter", "apt_code", "state_payments_included"],
    "fully_allocated_expense": ["fiscal_year", "fiscal_quarter", "apt_code", "state_payments_included"],
    "customer_otp_route": ["fiscal_year", "fiscal_quarter", "service", "sub_service"],
    "customer_otp_train": ["fiscal_year", "fiscal_quarter", "service", "sub_service", "train_number"],
    "delay_rates_by_host": ["fiscal_year", "fiscal_quarter", "service", "sub_service", "host_code", "responsibility"],
    "station_performance": ["fiscal_year", "fiscal_quarter", "service", "sub_service", "train_number", "station_code"],
    "csi_scores": ["fiscal_year", "fiscal_quarter", "route", "top_n", "basis", "metric"],
}


def colnorm(text: object) -> str:
    # Strip footnote numbers/superscripts and punctuation from headers.
    s = str(text).strip().lower().replace("¹", "").replace("²", "").replace("³", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()


def period_from_name(name: str) -> tuple[int, int] | None:
    match = PERIOD_RE.search(name)
    if not match:
        return None
    y = int(match.group(1))
    return (2000 + y if y < 100 else y, int(match.group(2)))


def classify(name: str) -> str | None:
    name = name.lower()
    if "public benefit" in name:
        return "public_benefits"
    if "schedule certification" in name:
        return "schedule_certification"
    if "csi" in name:
        return "csi"
    if "disput" in name and "delay" in name:
        return "disputed"
    if "delay" in name and "10k" in name.replace(" ", ""):
        return "delay_rate"
    if "delay" in name:
        return "delay_detail"
    if "financial" in name:
        return "financial"
    if "otp" in name:
        return "otp"
    if "station performance" in name:
        return "station"
    if "host" in name and "run" in name.replace(" ", ""):
        return "host_runtime"
    return None


def find_header(sheet: pd.DataFrame, required: set[str]) -> int | None:
    for index, row in sheet.head(12).iterrows():
        keys = {ALIASES.get(colnorm(v), colnorm(v)) for v in row if pd.notna(v)}
        if required <= keys:
            return int(index)
    return None


def parse_period(value: object) -> int | None:
    if pd.isna(value):
        return None
    found = re.search(r"([1-4])", str(value))
    return int(found.group(1)) if found else None


def clean_table(path: Path, sheet: str, table: str, period: tuple[int, int], issues: list[dict]) -> pd.DataFrame:
    preview = pd.read_excel(path, sheet_name=sheet, header=None, nrows=12, engine="openpyxl")
    header = find_header(preview, REQUIRED[table])
    period_from_filename = False
    otp_route_as_subservice = False
    # Historical host-runtime exports have no FY or quarter fields.
    if header is None and table == "host_runtime":
        header = find_header(preview, REQUIRED[table] - {"fiscal_year", "fiscal_quarter"})
        period_from_filename = header is not None
    # FY22 Q4 route OTP uses "Route" rather than "Sub Service" as its label.
    if header is None and table == "customer_otp_route":
        header = find_header(preview, (REQUIRED[table] - {"sub_service"}) | {"route"})
        otp_route_as_subservice = header is not None
    if header is None:
        raise ValueError(f"Cannot find header with {sorted(REQUIRED[table])}")
    df = pd.read_excel(path, sheet_name=sheet, header=header, engine="openpyxl")
    columns = [ALIASES.get(colnorm(c), colnorm(c)) for c in df.columns]
    if len(set(columns)) != len(columns):
        raise ValueError("After normalizing, duplicate column names exist")
    df.columns = columns
    if otp_route_as_subservice and "route" in df:
        df = df.rename(columns={"route": "sub_service"})
        issues.append({"level": "info", "file": path.name, "sheet": sheet,
                       "message": "Mapped source 'Route' to 'sub_service' for historical customer OTP"})
    df = df.dropna(how="all").copy()
    if period_from_filename:
        df["fiscal_year"], df["fiscal_quarter"] = period
        df["period_source"] = "filename"
        issues.append({"level": "info", "file": path.name, "sheet": sheet,
                       "message": "FY/quarter missing in host-runtime sheet; inferred from filename"})
    if table == "disputed_delay_summary":
        # There is no FY column on the original summary. Use the workbook's filename.
        df["fiscal_year"], df["fiscal_quarter"] = period
        df = df[~df["host_railroad"].astype(str).str.contains(r"total|may identify", case=False, na=False)]
    else:
        years = pd.to_numeric(df["fiscal_year"], errors="coerce")
        quarters = df["fiscal_quarter"].map(parse_period)
        valid = years.between(2000, 2100) & quarters.notna()
        dropped = int((~valid).sum())
        if dropped:
            issues.append({"level": "info", "file": path.name, "sheet": sheet,
                           "message": f"Excluded {dropped} non-data/footer rows with invalid periods"})
        df = df.loc[valid].copy()
        df["fiscal_year"] = years.loc[valid].astype(int)
        df["fiscal_quarter"] = quarters.loc[valid].astype(int)
        mismatches = df[(df["fiscal_year"] != period[0]) | (df["fiscal_quarter"] != period[1])]
        if len(mismatches):
            issues.append({"level": "error", "file": path.name, "sheet": sheet,
                           "message": f"{len(mismatches)} rows mismatch FY/Q from filename; excluded"})
            df = df.drop(index=mismatches.index)
    if "apt_code" in df:
        df["reporting_level"] = df["apt_code"].apply(
            lambda v: "route" if re.fullmatch(r"APT_RT_\d+", str(v).strip(), re.I)
            else "aggregate")
    if "train_number" in df:
        df["train_number"] = df["train_number"].astype("string").str.replace(r"\.0$", "", regex=True)
    if "state_payments_included" in df:
        df["state_payments_included"] = df["state_payments_included"].astype(str).str.strip().str.lower().map(
            {"yes": True, "no": False})
    for col in sorted(NUMERIC & set(df.columns)):
        orig = df[col]
        numeric = pd.to_numeric(orig, errors="coerce")
        invalid = int(((orig.notna()) & orig.astype(str).str.strip().ne("") & numeric.isna()).sum())
        if invalid:
            issues.append({"level": "warning", "file": path.name, "sheet": sheet,
                           "message": f"{invalid} nonnumeric entries in {col}; kept as missing"})
        df[col] = numeric
    for proportion in ("customer_otp", "cost_recovery", "avoidable_expense_coverage", "allocated_expense_coverage"):
        if proportion in df:
            # Cost recovery can legitimately be above 1, but cannot be negative.
            bad = (~df[proportion].between(0, 1) if proportion == "customer_otp" else (df[proportion] < 0)) & df[proportion].notna()
            if bad.any():
                issues.append({"level": "error", "file": path.name, "sheet": sheet,
                               "message": f"{bad.sum()} invalid {proportion} values"})
    if table == "delay_rates_by_host":
        expected = 10000 * df["delay_minutes"] / df["train_miles"].replace(0, float("nan"))
        bad = ((expected - df["delay_per_10k_train_miles"]).abs() > 0.05).fillna(False)
        if bad.any():
            issues.append({"level": "error", "file": path.name, "sheet": sheet,
                           "message": f"{bad.sum()} delay-rate arithmetic mismatches"})
    if table == "delay_by_code":
        # Train miles are repeated across delay codes. Denominator must be deduplicated.
        df["host_train_miles_repeated"] = True
    if table == "station_performance":
        bad = (df["late_detraining_customers"] > df["detraining_customers"]).fillna(False)
        if bad.any():
            issues.append({"level": "error", "file": path.name, "sheet": sheet,
                           "message": f"{bad.sum()} rows have more late than total detraining passengers"})
    return with_provenance(df, path, sheet, table, header + 2)


def with_provenance(df: pd.DataFrame, path: Path, sheet: str, table: str, first_excel_row: int) -> pd.DataFrame:
    df = df.copy()
    df["source_workbook"] = path.name
    df["source_sheet"] = sheet
    df["source_excel_row"] = df.index + first_excel_row
    df["table_family"] = table
    return df.reset_index(drop=True)


CSI_METRICS = [
    "Overall Service", "Amtrak Personnel", "Information Given", "On-Board Comfort",
    "On-Board Cleanliness", "On-Board Food Service",
]


def parse_csi(path: Path, sheet: str, period: tuple[int, int], issues: list[dict]) -> pd.DataFrame:
    match = re.search(r"(?:top\s*([34])|top([34]))", sheet, re.I)
    if not match:
        raise ValueError(f"Unknown CSI sheet: {sheet}")
    top_n = int(next(g for g in match.groups() if g))
    sheet_lower = sheet.lower()
    if "raw" in sheet_lower or "query" in sheet_lower:
        raise ValueError("CSI query/raw sheet is not the published metric output")
    if "all responses" in sheet_lower:
        basis = "all_responses"
    elif "blue sky" in sheet_lower:
        basis = "blue_sky"
    elif "on-time" in sheet_lower:
        basis = "on_time"
    elif "non-adjusted" in sheet_lower or "unadjusted" in sheet_lower:
        basis = "unadjusted"
    elif "adjusted" in sheet_lower:
        basis = "adjusted"
    else:
        raise ValueError(f"CSI basis unknown: {sheet}")
    preview = pd.read_excel(path, sheet_name=sheet, header=None, nrows=8, engine="openpyxl")
    # FY21 Q4--FY23 Q1: unlabelled route number and route name first; metric columns at end.
    if period <= (2023, 1):
        df = pd.read_excel(path, sheet_name=sheet, header=None, skiprows=2, engine="openpyxl")
        if df.shape[1] < 9:
            raise ValueError("Early CSI sheet has fewer than expected columns")
        data = pd.DataFrame({"route": df.iloc[:, 1], "fiscal_year": period[0],
                             "fiscal_quarter": period[1], "top_n": top_n, "basis": basis,
                             "source_excel_row": df.index + 3})
        for i, label in enumerate(CSI_METRICS):
            data[colnorm(label).replace(" ", "_")] = df.iloc[:, df.shape[1] - 6 + i].values
    else:
        header = find_header(preview, {"route", "fiscal year quarter", "overall service"})
        if header is None:
            raise ValueError("Modern CSI sheet header not recognized")
        raw = pd.read_excel(path, sheet_name=sheet, header=header, engine="openpyxl")
        raw.columns = [colnorm(c).replace(" ", "_") for c in raw.columns]
        if "fiscal_year_quarter" not in raw:
            raise ValueError("CSI reporting period column missing")
        # Crucial: sheet labels distinguish adjusted, unadjusted, on-time,
        # all-responses and Blue Sky; they are NOT assumed interchangeable.
        fyq = raw["fiscal_year_quarter"].astype(str).str.extract(
            r"FY\s*(\d{2,4})\s*Q\s*([1-4])", flags=re.I)
        years = pd.to_numeric(fyq[0], errors="coerce").map(
            lambda n: (n+2000 if n < 100 else n) if pd.notna(n) else n)
        quarters = pd.to_numeric(fyq[1], errors="coerce")
        matched = (years == period[0]) & (quarters == period[1])
        invalid = int((raw["route"].notna() & ~matched).sum())
        if invalid:
            issues.append({"level": "error", "file": path.name, "sheet": sheet,
                           "message": f"{invalid} CSI rows with invalid/mismatched periods excluded"})
        data = raw.loc[matched, :].copy()
        data["fiscal_year"], data["fiscal_quarter"] = period
        data["top_n"], data["basis"] = top_n, basis
        data["source_excel_row"] = data.index + header + 2
    # Long-form preserves the source's exact metric label for comparability review.
    value_columns = [c for c in data.columns if c in {
        "overall_service", "amtrak_personnel", "on_board_personnel", "information_given",
        "on_board_comfort", "on_board_cleanliness", "on_board_food_service"}]
    if len(value_columns) != 6:
        raise ValueError(f"Expected six CSI metrics, found {value_columns}")
    data = data.loc[data["route"].notna() & data["route"].astype(str).str.strip().ne("")].copy()
    data["route"] = data["route"].astype(str).str.strip()
    melted = data.melt(id_vars=["route", "fiscal_year", "fiscal_quarter", "top_n", "basis", "source_excel_row"],
                       value_vars=value_columns, var_name="metric", value_name="score")
    orig = melted["score"]
    melted["score"] = pd.to_numeric(orig, errors="coerce")
    bad_numeric = int((orig.notna() & melted["score"].isna()).sum())
    if bad_numeric:
        issues.append({"level": "warning", "file": path.name, "sheet": sheet,
                       "message": f"{bad_numeric} CSI score values are not numeric"})
    bad_range = melted["score"].notna() & ~melted["score"].between(0, 1)
    if bad_range.any():
        issues.append({"level": "error", "file": path.name, "sheet": sheet,
                       "message": f"{bad_range.sum()} CSI scores outside [0,1]"})
    melted["source_workbook"] = path.name
    melted["source_sheet"] = sheet
    melted["table_family"] = "csi_scores"
    return melted


def recognized_csi_sheets(names: list[str]) -> list[str]:
    result = []
    for s in names:
        low = s.lower()
        if "top" in low and re.search(r"top\s*[34]", low) and "raw" not in low and "query" not in low:
            result.append(s)
    return result


def compile_inventory_report(raw: Path, files: list[Path], records: list[dict], issues: list[dict], output: dict[str, pd.DataFrame]) -> dict:
    periods = sorted({r["period"] for r in records if r.get("period")})
    period_coverage: dict[str, dict[str, int]] = defaultdict(dict)
    for r in records:
        if r.get("status") == "parsed":
            period_coverage[r["period"]][r["table"]] = period_coverage[r["period"]].get(r["table"], 0) + r["rows"]
    return {
        "raw_directory": str(raw), "workbook_count": len(files), "periods": periods,
        "parsed_sheets": sum(r["status"] == "parsed" for r in records),
        "skipped_sheets": sum(r["status"] == "skipped" for r in records),
        "issue_counts": dict(Counter(x["level"] for x in issues)),
        "output_row_counts": {k: len(v) for k, v in output.items()},
        "period_coverage": dict(period_coverage),
        "files_and_sheets": records,
        "issues": issues,
        "notes": [
            "Financial system totals and route rows coexist: filter reporting_level='route' for route analysis.",
            "Delay by code repeats host_train_miles across delay codes: never sum it without deduplicating by train/host/quarter.",
            "Customer OTP train-level percentages cannot be averaged to obtain route OTP without passenger weights.",
            "CSI adjusted/unadjusted/on-time/blue-sky/all-responses categories are distinct measures.",
            "Unknown and public-benefit workbooks are inventoried but not imported in this version.",
            "No route/subservice names are collapsed or automatically cross-joined.",
        ],
    }


def run(raw: Path, out: Path, reports: Path) -> dict:
    files = sorted(p for p in raw.rglob("*.xlsx") if not p.name.startswith("~$"))
    if not files:
        raise FileNotFoundError(f"No .xlsx workbooks found in {raw}")
    out.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    issues: list[dict] = []
    records: list[dict] = []
    tables: dict[str, list[pd.DataFrame]] = defaultdict(list)
    selections = {}
    for path in files:
        period = period_from_name(path.name)
        family = classify(path.name)
        if period is None or family is None:
            issues.append({"level": "warning", "file": path.name, "message": "Unrecognized filename or period; skipped"})
            records.append({"file": path.name, "status": "skipped", "reason": "Unrecognized filename or period"})
            continue
        if family in ("public_benefits", "schedule_certification"):
            records.append({"file": path.name, "period": f"{period[0]} Q{period[1]}",
                            "family": family, "status": "skipped", "reason": "Import not yet defined"})
            continue
        # Favor explicitly revised workbook when multiple versions cover the same metric/period.
        key = (family, period)
        priority = 1 if "revised" in path.name.lower() else 0
        if key in selections:
            prev, prev_priority = selections[key]
            if priority > prev_priority:
                issues.append({"level": "warning", "file": path.name,
                               "message": f"Revised workbook supersedes {prev.name}"})
                selections[key] = (path, priority)
            else:
                issues.append({"level": "warning", "file": path.name,
                               "message": f"Duplicate {family} for FY{period[0]} Q{period[1]}: skipped; selected {prev.name}"})
        else:
            selections[key] = (path, priority)
    for (family, period), (path, priority) in sorted(selections.items(), key=lambda x: (x[0][1], x[0][0])):
        try:
            xl = pd.ExcelFile(path, engine="openpyxl")
        except Exception as exc:
            issues.append({"level": "error", "file": path.name, "message": f"Failed to open Excel file: {exc}"})
            continue
        if family == "csi":
            sheets = [(s, "csi_scores") for s in recognized_csi_sheets(xl.sheet_names)]
        else:
            sheets = [(s, output_name) for s, output_name in FAMILY_SHEETS[family].items() if s in xl.sheet_names]
        if family != "csi":
            missing_sheets = [s for s in FAMILY_SHEETS[family] if s not in xl.sheet_names]
            # The first quarter in the collection contains train-level OTP only.
            if family == "otp" and period == (2021, 4):
                missing_sheets = [s for s in missing_sheets if s != "Route Level C OTP"]
            for missing in missing_sheets:
                issues.append({"level": "warning", "file": path.name,
                               "message": f"Expected sheet not found: {missing}"})
        elif len(sheets) < 4:
            issues.append({"level": "warning", "file": path.name,
                           "message": f"Only {len(sheets)} of four expected CSI score categories recognized"})
        if not sheets:
            issues.append({"level": "error", "file": path.name,
                           "message": f"No recognized {family} sheet found: {xl.sheet_names}"})
        for sheet, table in sheets:
            try:
                df = (parse_csi(path, sheet, period, issues) if table == "csi_scores" else
                      clean_table(path, sheet, table, period, issues))
                if df.empty:
                    issues.append({"level": "warning", "file": path.name, "sheet": sheet, "message": "No valid rows found"})
                tables[table].append(df)
                records.append({"file": path.name, "period": f"{period[0]} Q{period[1]}",
                                "family": family, "sheet": sheet, "table": table, "rows": len(df), "status": "parsed"})
            except Exception as exc:
                issues.append({"level": "error", "file": path.name, "sheet": sheet, "message": str(exc)})
                records.append({"file": path.name, "period": f"{period[0]} Q{period[1]}",
                                "family": family, "sheet": sheet, "table": table, "status": "skipped", "reason": str(exc)})
        xl.close()
    final = {}
    for name, frames in sorted(tables.items()):
        df = pd.concat(frames, ignore_index=True, sort=False)
        keys = KEYS.get(name)
        if keys and set(keys) <= set(df.columns):
            duplicate = int(df.duplicated(subset=keys, keep=False).sum())
            if duplicate:
                issues.append({"level": "warning", "table": name,
                               "message": f"{duplicate} rows share a supposed unique key {keys}; retained for review"})
        if {"fiscal_year", "fiscal_quarter"} <= set(df.columns):
            df = df.sort_values(["fiscal_year", "fiscal_quarter"], kind="stable")
        df.to_csv(out / f"{name}.csv", index=False, encoding="utf-8-sig")
        final[name] = df
    report = compile_inventory_report(raw, files, records, issues, final)
    (reports / "fra_etl_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Workbooks found: {len(files)} | Parsed sheets: {report['parsed_sheets']} | Errors: {report['issue_counts'].get('error', 0)}")
    for name, count in report["output_row_counts"].items():
        print(f"  {name}: {count:,} rows")
    print(f"Report: {reports / 'fra_etl_report.json'}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=ROOT / "data/raw/fra")
    parser.add_argument("--out", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--reports", type=Path, default=ROOT / "data/reports")
    args = parser.parse_args()
    try:
        run(args.raw, args.out, args.reports)
    except FileNotFoundError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
