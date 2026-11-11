# Rail Ridership Sketch Lab — homepage integration

This update promotes the Rail Ridership Sketch Lab to the **second featured project** on the Data Lab homepage, adds a persistent **Rail Forecast** navigation link, and displays county-data publication status accurately.

## Install

1. Back up your existing project at `C:\Users\Matt\Documents\mattkeen`.
2. Extract the contents of the update ZIP into that folder, merging `app/` and `scripts/` and replacing matching files. This ZIP does not overwrite your locally published county catalog or your raw Census files.
3. Restart Flask: ` .\.venv\Scripts\python.exe run.py `.
4. Visit `http://127.0.0.1:5000/` and refresh the browser; use the new **Rail Forecast** navigation link or the featured homepage card.

The project's direct URL is `http://127.0.0.1:5000/projects/rail-ridership-estimator`.

## Publish nationwide county inputs (if not already done)

Place `census_data_all_county.csv` and `2025_Gaz_counties_national.zip` in `data/raw/census/`, then run:

```powershell
.\.venv\Scripts\python.exe scripts\publish_counties.py --check-only
.\.venv\Scripts\python.exe scripts\publish_counties.py
```

Restart Flask after publishing. The homepage says **Demo** until the catalog has at least 3,000 usable county equivalents, then shows the actual count. The publisher requires local downloads but no Census API key.

## Interpretation

The county dataset supplies demographic and geographic inputs; ridership is still an **uncalibrated scenario**, not an empirically validated forecast. No NHTS or Amtrak OD calibration has been performed yet.
