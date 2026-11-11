r"""Inventory FRA Excel workbooks without modifying or combining their contents.

Run from project root:
  .\.venv\Scripts\python.exe scripts/inspect_fra.py
Outputs: data/reports/workbook_inventory.json, data/reports/sheet_inventory.csv

This is intentionally a discovery tool, NOT a production ETL transform.
"""
import csv
import json
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "fra"
REPORTS = ROOT / "data" / "reports"
ACCEPT = {".xlsx", ".xlsm", ".xls"}
MAX_PREVIEW_ROWS = 12
MAX_PREVIEW_COLS = 18
HEADER_SCAN_ROWS = 24


def safe_value(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)[:240]


def safe_unique(values):
    return [safe_value(v) for v in values]


def candidate_headers(frame):
    """Suggest potential header rows; these are hints, not ground truth."""
    scored = []
    for index, row in frame.head(HEADER_SCAN_ROWS).iterrows():
        values = [str(v).strip() for v in row.tolist() if pd.notna(v) and str(v).strip()]
        if not values:
            continue
        nonnumeric = sum(not str(x).replace(',', '').replace('.', '').isdigit() for x in values)
        unique = len(set(v.casefold() for v in values))
        score = (len(values), nonnumeric, unique)
        scored.append({"excel_row": int(index) + 1, "nonempty_cells": len(values),
                       "text_cells": nonnumeric, "distinct_cells": unique,
                       "sample": values[:8], "_score": score})
    for row in sorted(scored, key=lambda r: r["_score"], reverse=True)[:3]:
        row.pop("_score")
        yield row


def inventory_sheet(book, sheet):
    # Header=None preserves rows above a data table and avoids guessing column labels.
    frame = pd.read_excel(book, sheet_name=sheet, header=None, nrows=40, dtype=object)
    preview = []
    for _, row in frame.iloc[:MAX_PREVIEW_ROWS, :MAX_PREVIEW_COLS].iterrows():
        preview.append(safe_unique(row.tolist()))
    return {
        "sheet_name": sheet,
        "sampled_rows": len(frame),
        "sampled_columns": len(frame.columns),
        "header_candidates": list(candidate_headers(frame)),
        "top_left_preview": preview,
        "note": "Only the first 40 rows are sampled; dimensions are NOT whole-sheet counts.",
    }


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    paths = sorted(p for p in RAW.iterdir() if p.is_file() and
                   p.suffix.lower() in ACCEPT and not p.name.startswith('~$'))
    if not paths:
        raise SystemExit(f"No Excel files found in {RAW}. Copy your FRA files there first.")
    inventories = []
    for path in paths:
        record = {"file": path.name, "size_bytes": path.stat().st_size, "sheets": []}
        print(f"Inspecting {path.name}")
        try:
            with pd.ExcelFile(path) as book:
                for sheet in book.sheet_names:
                    try:
                        record["sheets"].append(inventory_sheet(book, sheet))
                    except Exception as exc:
                        record["sheets"].append({"sheet_name": sheet, "error": str(exc)})
        except Exception as exc:
            record["error"] = str(exc)
        inventories.append(record)
    json_path = REPORTS / "workbook_inventory.json"
    json_path.write_text(json.dumps({"workbooks": inventories}, indent=2, ensure_ascii=False), encoding="utf-8")
    csv_path = REPORTS / "sheet_inventory.csv"
    with csv_path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['workbook','sheet','sampled_rows','sampled_columns','header_row_candidates','error'])
        for wb in inventories:
            if not wb['sheets']:
                writer.writerow([wb['file'],'','','','', wb.get('error','')])
            for sheet in wb['sheets']:
                writer.writerow([wb['file'],sheet['sheet_name'],sheet.get('sampled_rows',''),
                                 sheet.get('sampled_columns',''),
                                 '; '.join(str(x['excel_row']) for x in sheet.get('header_candidates',[])),
                                 sheet.get('error','')])
    print(f"\nInventoried {len(paths)} workbook(s).")
    print(f"Report: {json_path}")
    print(f"Summary: {csv_path}")
    print('No files were changed and no rail metrics were calculated.')


if __name__ == '__main__':
    main()
