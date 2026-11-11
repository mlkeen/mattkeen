# Station Performance Map

## Install

Use the site-update ZIP; back up the current project, then merge its `app` and
`scripts` folders into `C:\Users\Matt\Documents\mattkeen`. Keep existing
`data/processed` and `data/raw/fra` files.

Run from project root:

```powershell
.\.venv\Scripts\python.exe scripts\publish_station_map.py
.\.venv\Scripts\python.exe run.py
```

Open `http://127.0.0.1:5000/projects/intercity-rail/stations`.

The first publisher run requires Internet to fetch the USDOT/BTS NTAD station
coordinates. The downloaded GeoJSON is cached at
`data/raw/fra/amtrak_station_coordinates.geojson`. Subsequent runs use the cache.
To use your own validated location crosswalk instead:

```powershell
.\.venv\Scripts\python.exe scripts\publish_station_map.py --coordinates data/station_coordinates.csv
```

The CSV columns must be `station_code,lat,lon` (optional `station_name`).
The publisher only maps *exact three-letter station-code matches*. All other
codes are listed in `data/reports/station_map_report.json` rather than guessed.
Station placement from the 2026 station location snapshot may not represent
historical station relocations or temporary facilities.

If you replace the published JSON while Flask is running, restart Flask to clear
its in-process station data cache.

## Measures

Late share = 100 × sum(late detraining passengers) / sum(detraining passengers).
Invalid counts are excluded. Average late minutes is a *passenger-weighted*
average using only records where a nonnegative valid average is available; the
API returns coverage for this weighted average.

The service dropdown uses exact FRA service/subservice values and the imported
`service_line` for category labels. It does not infer route-wide metrics from
train-level OTP. Group filters limit choices; they are not combined results.

Source: https://catalog.data.gov/dataset/amtrak-stations
ArcGIS endpoint:
https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/NTAD_Amtrak_Stations/FeatureServer/0

The source station layer is current to Oct 8, 2026 and may include bus terminals.
The FRA performance file determines which codes appear on the map.
