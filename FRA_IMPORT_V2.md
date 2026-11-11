# FRA historical importer — V2 (20-quarter collection)

## Source inventory reviewed

Based on `workbook_inventory(1).json`, the collection includes **179 workbooks** across **20 contiguous quarters** (FY2021 Q4–FY2026 Q3). It includes 20 each of financial, customer OTP, CSI, detailed delay, delay-per-10k, disputed-delay, and station workbooks; 19 host-runtime files; 17 public-benefits files; and 3 schedule-certification files.

Source-format checks against the JSON inventory found 298 recognized sheets across the seven continuous families plus host runtime and disputed delays. Ten header exceptions were located and explicitly handled in the script, including early host-runtime sheets with no date columns and FY2022 Q4 route OTP's `Route` header. Source Excel data are **not bundled**; the parser has only been tested on synthetic XLSX examples and the structural inventory, not all 179 original sheets.

## Installation on Windows

1. **Back up your working website folder** and extract this ZIP somewhere else. Copy `scripts/fra_etl.py` into your existing project's `scripts/` folder, replacing the earlier importer. Optionally copy `tests/test_fra_etl.py` and this guide as well.
2. Put all original `.xlsx` files in `data/raw/fra/`. You can use subfolders; the script searches recursively.
3. In VS Code PowerShell, from your website folder, install data requirements (if you haven't already):

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-data.txt
   ```

4. Run:

   ```powershell
   .\.venv\Scripts\python.exe scripts\fra_etl.py
   ```

5. Inspect `data/reports/fra_etl_report.json` and the CSVs written into `data/processed/`. **Please upload the report here for review.** It lists all parsed/skipped sheets, periods and warnings. Never assume all reports were accepted until the errors have been reviewed.

Optional local importer tests (without FRA data):

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_fra_etl.py
```

## Tables output

| Output | Reporting level |
| --- | --- |
| `ridership.csv` | Financial reporting route or aggregate, by quarter |
| `cost_recovery.csv` | Financial reporting route or aggregate, by quarter |
| `avoidable_expense.csv` | Financial reporting route or aggregate; separate yes/no state-payment basis |
| `fully_allocated_expense.csv` | Financial reporting route or aggregate; separate yes/no state-payment basis |
| `customer_otp_route.csv` | Service/subservice, by quarter (FY2021 Q4 not available) |
| `customer_otp_train.csv` | Service/subservice/train number, by quarter |
| `delay_by_code.csv` | Service/subservice/train/host/responsibility/delay code, by quarter |
| `delay_rates_by_host.csv` | Service/subservice/host/responsibility, by quarter |
| `station_performance.csv` | Service/subservice/train/station, by quarter |
| `host_runtime.csv` | Service/subservice/train/host, by quarter (19 quarters) |
| `disputed_delay_summary.csv` | Host railroad, by quarter |
| `csi_scores.csv` | Route, quarter, score category (e.g. adjusted versus on-time), Top-3/Top-4 threshold, survey component |

Other workbooks (public benefits and schedule certification) are **explicitly inventoried but not imported** in this version. The CSV catalog in the ZIP shows which are deferred.

## Data-integrity protections

- Financial aggregates (e.g. `APT_All_APT`, `APT_RT_NTS`) remain labelled `reporting_level=aggregate` so they are not summed with route-level rows. To analyze routes, filter `reporting_level == 'route'`.
- Train-mile denominators in the detailed delay-code table repeat across delay codes. **Do not sum `host_train_miles` in that table.** Use the published host-level delay-rate table for delay-per-10k calculations and comparisons. Do not average the published rates without appropriate train-mile weights.
- Route customer-OTP percentages are **not** constructed by averaging train-level percentages; proper passenger weights would be needed.
- CSI scores retain `basis`, `top_n`, and original metric field names. An `Adjusted Top 3` measure is not the same as `All Responses Top 3` or `Blue Sky Top 3`. Do not splice them as one time series without documentation and verification of measure definitions.
- `APT_Code` and original route/service/subservice fields are retained. The importer **does not automatically equate** operations subservices to financial reporting routes; that requires a reviewed crosswalk.
- Filenames and sheet/Excel row positions are recorded on exported rows. For early host-runtime workbooks without FY and quarter columns, `period_source='filename'` is set and the audit records the inference.
- Invalid values become missing rather than zero; impossible proportion values and mismatched delay-rate arithmetic generate validation errors.
- Original workbooks are never altered.

## Observed historical differences

- Filenames include `Financial REVISED.xlsx`, `Financial.xlsx`, and `Financial Metrics.xlsx`.
- FY2021 Q4 has train-level customer OTP only (`Train Level C OTP-for report`); route OTP begins FY2022 Q1.
- FY2022 Q4's route-level OTP workbook calls its subservice field `Route`.
- Older host-runtime workbook exports lack quarter columns through at least FY2024 Q1; later sheets include both period columns. Some also rename service columns to `Transportation Service Name` and `Transportation Sub Service Name`.
- CSI sheets use an older unlabeled-route format through FY2023 Q1, switch to a more standard format in FY2023 Q2, and use different category names in FY2026.

## Next milestone

Once the full source workbooks successfully pass validation, create an explicit route crosswalk and connect a **validated route-quarter dataset** to the Flask API. Only then retire the existing illustrative JSON data. This separation avoids accidentally publishing synthetic values as observed results.
