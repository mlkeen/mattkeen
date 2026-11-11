# mattkeen.com — Data Lab

Flask portfolio and interactive economic/transportation data exploration site.

## Live historical rail explorer

The Intercity Rail Explorer presents **FRA quarterly ridership for FY2021 Q4–FY2026 Q3**, sourced from the Financial Metrics workbooks' *Average & Total Ridership* sheets. The shipped `app/data/fra_ridership.csv` has been reconciled against the FRA system totals for all 20 quarters.

The new **customer on-time performance** panel uses the FRA *Route Level C OTP* data from the same historical workbook collection. **Important:** the actual 868-row OTP CSV is held in the user's local `data/processed/customer_otp_route.csv` and **is not bundled in this download**. Publish it locally using `scripts/publish_customer_otp.py` to include reliability data in deployed site assets. The site does not fabricate missing OTP values.

The original file `app/data/rail_routes.json` is a legacy illustrative prototype and is not used by the current ridership/OTP explorer routes.

See `RIDERSHIP_WEBSITE_SETUP.md` and `OTP_WEBSITE_SETUP.md` for detailed setup, source methodology, and refresh steps.

## Local setup (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-data.txt
.\.venv\Scripts\python.exe scripts\publish_customer_otp.py
.\.venv\Scripts\python.exe run.py
```

The publishing command requires the processed CSV generated previously by `scripts/fra_etl.py`. There is no need to rerun the full 179-workbook ETL if that CSV already exists.

Open `http://127.0.0.1:5000/projects/intercity-rail`.

## Refresh after adding FRA workbooks

```powershell
.\.venv\Scripts\python.exe scripts\fra_etl.py
.\.venv\Scripts\python.exe scripts\publish_ridership.py
.\.venv\Scripts\python.exe scripts\publish_customer_otp.py
.\.venv\Scripts\python.exe -m pytest -q
```

Restart Flask to reload the cached data. Do not commit `data/raw/fra/` or `data/processed/`. Commit the curated published CSVs in `app/data/` after validation.

## Technical approach

- Ridership: quarterly total riders (marketing) as source reports; no double-counting of aggregate system and route rows; no negative ridership adjustments plotted as counts.
- OTP: route-level passenger proportion (0–1) shown as percentage; percentage-point changes year over year; missing periods remain missing.
- No unweighted averaging of train-level or subservice OTP figures. A financial ridership route and operational OTP service are auto-linked only if the *service* and *subservice* names both match the ridership route name exactly, apart from case and whitespace.
- Separate route/subservice OTP selector lets users view operational reporting splits independently of financial route names.
- Published data retain source workbook, sheet, and original Excel row references.

## Tests and deployment

`requirements.txt` contains Flask, Gunicorn and pytest. The project includes tests for app endpoints, FRA ingestion, ridership publication, and OTP publication and service matching.

`wsgi.py` and `Procfile` support WSGI deployment (e.g. Railway); configure your own service/domain settings. Chart interactivity requires the Plotly CDN. Data tables and APIs remain readable without Plotly.
