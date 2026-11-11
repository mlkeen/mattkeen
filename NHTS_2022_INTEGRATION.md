# 2022 NHTS V2.1 — Ridership Sketch Lab integration

This patch uses **downloaded** 2022 National Household Travel Survey microdata. No API key or connection is used when publishing. It does not bundle the actual survey records: download the official public-use **2022 Survey Data, CSV V2.1** archive from https://nhts.ornl.gov/downloads (see also https://nhts.ornl.gov/documentation for the Codebook V2.1). This is the **survey CSV**, not the distinct passive OD data product.

## Install

Merge this patch into the `mattkeen` Flask project. Preserve `app/data/county_rail_inputs.csv`, all existing calibration files, and the FRA data.

Save the official survey ZIP as:

    data/raw/nhts/2022_nhts_csv.zip

The filename is arbitrary if you use `--source`; keep the ZIP intact. The importer finds the *long-distance person* CSV by its fields even when it has an unfamiliar filename or is inside a ZIP subfolder.

From the project root, in PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts\publish_nhts_2022.py --source data\raw\nhts\2022_nhts_csv.zip --check-only
.\.venv\Scripts\python.exe scripts\publish_nhts_2022.py --source data\raw\nhts\2022_nhts_csv.zip
.\.venv\Scripts\python.exe scripts\calibrate_rail_forecast.py --check-only
.\.venv\Scripts\python.exe scripts\calibrate_rail_forecast.py
.\.venv\Scripts\python.exe run.py
```

**Important:** The calibration script needs the nationwide real county catalog and pre-existing `data/raw/fra/fy2025_amtrak_route_ridership.csv`. If either is absent, publishing the NHTS profile still works, but the model will display **NHTS-informed, not Amtrak-calibrated**. Run the Census county publisher and prepare your FRA reference totals as documented in `RAIL_FORECAST_EMPIRICAL_SETUP.md` first.

View `/projects/rail-ridership-estimator`. The `/api/rail-forecast/nhts` endpoint returns the published survey profile and `/api/rail-forecast/calibration` supplies the calibration diagnostics. When not published, the NHTS endpoint returns 404 with an explanation; **no synthetic survey statistics are displayed**.

## Statistical definition

The 2022 NHTS V2.1 long-distance file has **one record per person**, *not one record per long-distance trip*. The importer uses the person weight `WTPERFIN` to calculate:

- Weighted average `LONGDIST`: 50+ mile trips reported over previous 30 days, annualized by multiplying by 12 for a **rough benchmark**.
- Weighted average `LD_AMT`: number of Amtrak uses in the prior year, and weighted percentage reporting at least one such use.
- Weighted share with `MAINMODE=13` (Amtrak) among respondents with a valid most-recent-long-distance-trip mode. **Descriptive only; never applied as an annual rail market share.**

The estimated annualized long-distance frequency replaces the **default** `base_trip_rate` in the gravity model. After this changes, the existing Amtrak calibration file is considered stale, so the calibration procedure must be rerun. Its resulting multiplicative demand factor reconciles the revised baseline with *FY2025 observed Amtrak route totals*, and existing leave-one-route-out diagnostics remain visible.

The application allows users to override the default trip-production benchmark in Advanced Demand Assumptions. This is a scenario; it is not re-estimated using NHTS or Amtrak.

### Remaining important limitations

The national survey does **not** contain a complete county-pair OD matrix, local station catchment sizes, rail-service generalized costs, or enough independent route-level records to identify rail choice elasticities. The gravity shape and competition parameters remain assumptions. The 30-day lookback can be affected by seasons/recall and annualization is approximate. Survey replicate-weight variance estimates are **not** provided by this release. FY2025 Amtrak activity is observed in a different period from the 2022 survey, and the route cross-validation set consists of hand-selected corridor county proxies. Do not treat the results as a grant-ready, validated demand forecast.

## Technical validation

`pytest tests/test_nhts_2022.py tests/test_rail_forecast.py tests/test_empirical_calibration.py` passes with synthetic, *labeled test fixtures*. The official 2022 file could not be downloaded in the build environment; you must run the importer on the official ZIP before real survey values are available. Python compilation and JavaScript syntax are also checked. Full local Flask/browser validation is still needed.
