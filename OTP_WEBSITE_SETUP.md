# FRA Customer On-Time Performance — website update

This update adds route-level **Customer On-Time Performance (C OTP)** to the existing ridership explorer. It uses the ETL output that is **already on your Windows computer**. No source OTP percentages are included in this ZIP because only the ETL report and ridership CSV were shared with ChatGPT.

## Install in your existing Windows project

1. Back up or commit `C:\Users\Matt\Documents\mattkeen`.
2. Extract the **site update** ZIP somewhere else. Copy its `app/`, `scripts/publish_customer_otp.py`, `tests/`, and `OTP_WEBSITE_SETUP.md` into your existing `mattkeen` folder, **merging**, not deleting directories. Do not overwrite `scripts/fra_etl.py` or `data/raw/fra/`.
3. In the VS Code PowerShell terminal, at project root, publish the existing OTP extract:

   ```powershell
   .\.venv\Scripts\python.exe scripts\publish_customer_otp.py
   ```

   Expect **868 route-level C OTP rows across 19 reported fiscal quarters**, per the last ETL report. The command rejects invalid fractions, duplicate keys, and missing provenance. It leaves the processed and raw files unchanged and publishes `app/data/fra_customer_otp_route.csv` for deployment.
4. Stop Flask with Ctrl+C, then restart:

   ```powershell
   .\.venv\Scripts\python.exe run.py
   ```

5. Open `http://127.0.0.1:5000/projects/intercity-rail` and scroll to **Customer On-Time Performance**. Select Downeaster, then try Northeast Regional, which is split into separate OTP subservices rather than given a fabricated overall rate.
6. Run the tests in your existing environment:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q tests\test_app.py tests\test_otp_service.py tests\test_publish_customer_otp.py
   ```

## How the site handles comparability

- C OTP is a **passenger on-time percentage**, read from `data/processed/customer_otp_route.csv` and shown as percent. Changes from the same quarter of the previous fiscal year use **percentage points**.
- The original financial ridership route names and C OTP service/subservice names are **not assumed to be one and the same**. Automatic matching requires the OTP service name **and** subservice name to equal the named ridership route (apart from case and whitespace). For subdivided services, select the source OTP subservice independently in the reliability panel.
- Route-level C OTP isn't available in the FY2021 Q4 workbook. The trend starts with a missing point, **not 0%**.
- We **never average** train-level C OTP rates or multiple subservices to construct a route rate because passenger weights are unavailable.
- No means are used across quarters; the charts show original quarterly values. Values outside 0–1 are rejected.
- Every OTP observation retains workbook, source worksheet, and Excel row provenance.
- If your local processed OTP CSV is present but hasn't been published, the app can preview it during local development; the publish command copies a validated static version for GitHub/Railway deployment.
- No artificial OTP numbers are shipped or displayed. Without a source file, the ridership website remains usable and the OTP panel explains how to publish.

## New routes and APIs

- `/projects/intercity-rail` — independent OTP selector and chart alongside ridership.
- `/projects/intercity-rail/routes/downeaster` — ridership trend, matched OTP trend (if available), and separate audit tables.
- `/api/rail/routes/downeaster` — ridership route with optional `otp` object (null when unmatched).
- `/api/rail/otp/routes` — available reported OTP services/subservices.
- `/api/rail/otp/routes/<slug>` — original quarterly OTP records for one operational service/subservice.

## After a new FRA quarter is imported

```powershell
.\.venv\Scripts\python.exe scripts\fra_etl.py
.\.venv\Scripts\python.exe scripts\publish_ridership.py
.\.venv\Scripts\python.exe scripts\publish_customer_otp.py
```

Restart Flask. Public deployment reads the validated, versioned CSVs in `app/data/`. The original spreadsheet directory stays outside Git.

## Testing limitations

The actual 868-row OTP extract has not been uploaded for independent validation here. The publisher, loader, and page code can be tested with synthetic representative data, but the exact route/subservice names and numeric results must be checked in the real CSV on your machine. This release does not modify the historical ETL script.
