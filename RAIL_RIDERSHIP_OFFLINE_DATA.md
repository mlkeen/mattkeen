# Rail Ridership Sketch Lab: offline Census downloads

This update changes `scripts/publish_counties.py` to **use only downloaded local files**. It does not request a Census API key or contact Census servers while running. The first download still requires internet access in your browser.

## Step 1 — Download two official files

Save the files to `C:\Users\Matt\Documents\mattkeen\data\raw\census\`.

**A. ACS 2024 5-year county demographics (JSON)**

Open this URL in your browser (copy the entire line, including the `&` separators):

`https://api.census.gov/data/2024/acs/acs5?get=NAME,B01003_001E,B19013_001E&for=county:*&in=state:*`

Save the JSON response (not the webpage HTML) as **`acs_counties.json`**. In Chrome, open the URL and press `Ctrl+S`; ensure the file is JSON/text rather than HTML and remove any appended `.txt`. This is a one-time download; the local publishing script makes no API calls.

**B. 2025 national county Gazetteer (ZIP)**

https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_counties_national.zip

Save as **`2025_Gaz_counties_national.zip`**, without extracting it.

The ACS values are population (`B01003_001E`) and median household income (`B19013_001E`). County FIPS is the join key; the Gazetteer supplies representative county coordinates. This does not supply NHTS trip rates or Amtrak calibration.

## Step 2 — Check and publish using PowerShell

From `C:\Users\Matt\Documents\mattkeen`:

```powershell
.\.venv\Scripts\python.exe scripts\publish_counties.py --check-only
.\.venv\Scripts\python.exe scripts\publish_counties.py
.\.venv\Scripts\python.exe run.py
```

Open `http://127.0.0.1:5000/projects/rail-ridership-estimator`.

The script requires at least 3,000 valid matching county-equivalent records and refuses to overwrite the existing catalog otherwise. It reports unmatched FIPS and invalid observations; missing/suppressed income is preserved as 0 to indicate unavailable rather than dropping the county. The published CSV is `app/data/county_rail_inputs.csv`.

If your downloads are in a different location:

```powershell
.\.venv\Scripts\python.exe scripts\publish_counties.py --acs-json 'C:\Users\Matt\Downloads\acs_counties.json' --gazetteer-zip 'C:\Users\Matt\Downloads\2025_Gaz_counties_national.zip'
```

## Scope and limits

Using real county demographic inputs **does not calibrate** the ridership model: its travel production and mode-choice coefficients remain illustrative. County representative coordinates are not station sites, and centroid distances are not rail-network distances. For a calibrated model, next integrate 2022 NHTS and observed corridor/OD data as permitted, and check market-area treatment.

Sources: [2024 ACS 5-year datasets](https://www.census.gov/data/developers/data-sets/acs-5year.html); [2025 Gazetteer county files](https://www.census.gov/geographies/reference-files/2025/geo/gazetter-file.html).
