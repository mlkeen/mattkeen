# Station map: tile alignment and missing-marker fix

## What changed

* A local Leaflet geometry/positioning stylesheet loads **after** the remote Leaflet CSS. This prevents scattered tiles and invisible SVG circle markers if the CDN stylesheet fails to load or browser cache contains a bad response.
* The page-specific layout is retained from the previous layout fix.
* The map now remeasures after layout changes, on window load, and when resized.
* If OpenStreetMap's tile server fails repeatedly, the map tries CARTO's light basemap. Station markers are drawn independently of map tiles.
* If the Leaflet JavaScript CDN fails, a second CDN is attempted.
* Invalid coordinate responses and API errors produce readable status messages.
* The station table and summary values still use the existing Flask API; this patch does **not** change the data publisher or your FRA datasets.

## Install in Windows PowerShell

1. Back up your `C:\Users\Matt\Documents\mattkeen` project.
2. Extract the ZIP **into that project root**, merging directories and replacing matching files. You should see:

   - `app/templates/station_map.html`
   - `app/static/css/station_map_layout.css`
   - `app/static/css/leaflet_fallback.css` (new)
   - `app/static/js/station_map.js`

3. Stop Flask with Ctrl+C. Restart:

   ```powershell
   .\.venv\Scripts\python.exe run.py
   ```

4. Open `http://127.0.0.1:5000/projects/intercity-rail/stations` and press Ctrl+Shift+R.
5. Set **All available quarters** and **1+** minimum passengers for an initial check. The station status should report how many station locations were drawn.

## If markers still do not appear

Visit `http://127.0.0.1:5000/api/rail/stations` (should say `"available": true`).
On the map, read the status message under the legend. If it says `Station API returned HTTP ...`, copy the traceback from the PowerShell terminal. If it says no stations meet the filters, select a different service or reduce the minimum passenger filter.

If the map background remains plain but station circles display, the basemap tile requests are blocked by network filtering. The station data itself is loaded correctly.

## Validation scope

JavaScript syntax and template references were checked. The Python station loader was exercised with synthetic data. Actual user browser rendering and live tile requests cannot be verified from this environment.
