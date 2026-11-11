# Station map layout fix

This patch only changes the station map page template, adds a page-specific stylesheet, and updates the map JavaScript to recalculate Leaflet dimensions. It does not change the data publisher, Flask routes, or any processed FRA files.

## Install
1. Back up your existing `mattkeen` folder.
2. Extract this ZIP into `C:\Users\Matt\Documents\mattkeen`, merging folders and replacing `app/templates/station_map.html` and `app/static/js/station_map.js`. A new file, `app/static/css/station_map_layout.css`, will be added.
3. Restart Flask: `.\.venv\Scripts\python.exe run.py`
4. Open `http://127.0.0.1:5000/projects/intercity-rail/stations` and hard refresh with Ctrl+Shift+R.

The updated layout has four evenly sized filters, three aligned KPI cells, a full-width Leaflet map, a clean legend, and a horizontally scrollable table for small screens.

If map tiles remain offset, check browser Console for errors loading Leaflet CSS/JS or OpenStreetMap tiles; these require internet access.
