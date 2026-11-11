# FRA ridership website update (v1)

This package updates the **working Flask Data Lab site** to use actual FRA Total Ridership (Mktg) data for FY2021 Q4–FY2026 Q3. It does **not** change `scripts/fra_etl.py` or any raw spreadsheet files. It does not yet publish reliability, delay, or financial-ratio charts.

## Install on Windows (PowerShell)

1. **Back up** your existing `C:\Users\Matt\Documents\mattkeen` folder or make a Git commit.
2. Unzip the upgrade package to another folder. Copy the `app` folder **into** your existing `mattkeen` folder, selecting **replace** for files with the same names. Also copy `scripts/publish_ridership.py` and `tests/test_app.py` / `tests/test_publish_ridership.py`. Do **not** replace the entire existing project folder: that would risk losing `data/raw/fra` and `data/processed` files.
3. The new website's data lives in `app/data/fra_ridership.csv` and is included in the ZIP. That means the website will work immediately, without re-running the expensive ETL.
4. In VS Code, open PowerShell at the project root. Stop the running Flask server with `Ctrl+C` and start it again:

   ```powershell
   .\.venv\Scripts\python.exe run.py
   ```

5. Visit `http://127.0.0.1:5000/` and `http://127.0.0.1:5000/projects/intercity-rail`.
6. Check the **Downeaster** by default, change the selector to another reported service, and click **Inspect quarterly records**.

The page uses Plotly from a CDN; Internet access is required to render the interactive chart. The tabular data still load if Plotly is blocked.

## Refresh when new FRA quarters become available

```powershell
.\.venv\Scripts\python.exe scripts\fra_etl.py
.\.venv\Scripts\python.exe scripts\publish_ridership.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_app.py tests\test_publish_ridership.py
```

Restart Flask so its cached CSV reader sees the new published data. The published copy in `app/data/fra_ridership.csv` is intentionally under version control; the raw and processed data directories remain ignored by Git. **Warning:** `tests/test_app.py` includes fixed assertions for the current 2026 Q3 upload; those assertions will need updating after new quarters arrive.

## URLs

- `/` – real 20-quarter system-wide ridership chart
- `/projects/intercity-rail` – interactive route selection and searchable route table
- `/projects/intercity-rail/routes/downeaster` – audit trail and chart for a service
- `/api/rail/routes` – compact list of named service series
- `/api/rail/routes/downeaster` – 20-quarter observations for a selected service
- `/api/rail/ridership/system` – reported system totals by quarter

## Critical data-handling decisions

- Source: financial metrics' **Average & Total Ridership** worksheet / **Total Ridership (Mktg)**. Fiscal quarters are labeled FY#### Q#; this is not calendar-quarter reporting or annual ridership.
- We use only `reporting_level=route` for the service list. System totals come from *one* `APT_All_APT` aggregate row each quarter; `APT_RT_NTS` also reports the system total and must not be added.
- FRA has reused APT codes for `San Joaquin`/`Gold Runner`, `Great River Hiawatha`/`Borealis`, and `Gulf Coast Limited`/`Mardi Gras Service`. These are **separate** named series unless we later establish a verified service-level crosswalk.
- An exceptional **negative FY2025 Q4 Berkshire Flyer** ridership record (-1,112) is flagged; the chart leaves a gap and the audit table retains the original value. The full source is unchanged.
- Zeros are **reported zeros**, not missing values. A service that has no row for a quarter gets a gap, not zero.
- The imported ridership values can be fractional due to accounting adjustments; charts and tables round for readability, while APIs preserve precision.
- Year-over-year is `current quarterly ridership / same fiscal quarter previous year - 1`; it is N/A if either quarter is not available, the current value is negative, or the baseline is zero or negative.
- This first website version makes no claims about OTP, delay rates or finances. Those tables remain available for separate validation and future additions.

## Deployment note

The published CSV (`app/data/fra_ridership.csv`, about 160 KB) can go into GitHub and Railway with the app. Do not commit the raw workbook directory. The `publish_ridership.py` script validates unique keys and checks every quarter's route totals against the system aggregate (tolerance 0.02 riders) before updating the published file.
