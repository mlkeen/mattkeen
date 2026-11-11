# County CSV integration — offline

This update modifies only `scripts/publish_counties.py`. It supports the uploaded `census_data_all_county.csv` without requiring a Census API key.

1. Copy `census_data_all_county.csv` into `data/raw/census/` under your `mattkeen` project.
2. Download the official [2025 Census county Gazetteer ZIP](https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_counties_national.zip) to that **same** folder, retaining the exact filename `2025_Gaz_counties_national.zip`. The CSV lacks coordinates, so this second file is necessary.
3. Merge the `scripts/` directory from this update into your project.
4. Run from the project root:

```powershell
.\.venv\Scripts\python.exe scripts\publish_counties.py --check-only
.\.venv\Scripts\python.exe scripts\publish_counties.py
.\.venv\Scripts\python.exe run.py
```

The output is `app/data/county_rail_inputs.csv`. Check-only never modifies files; publication refuses to replace the existing catalog if fewer than 3,000 county-equivalent records validate.

The downloaded county CSV is an ACS-derived third-party compilation. Median household income missing values are recorded as 0 by the existing catalog schema, to mean unavailable (not actual zero income). The 2025 Gazetteer supplies county representative coordinates, **not actual station positions or rail network distances**. The resulting ridership numbers are still uncalibrated illustration.
