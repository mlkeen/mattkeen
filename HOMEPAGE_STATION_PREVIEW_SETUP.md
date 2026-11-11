# Homepage Station Map Preview

The homepage hero now previews the latest-quarter station lateness for the Downeaster (or another available service if it is absent). It draws actual station dots using the same published data endpoint as the full Station Performance Map, and links to the full interactive explorer. It does not invent coordinates or rates.

## Install

Extract the update ZIP over the existing project, merging folders. Restart Flask and hard refresh your browser (Ctrl+Shift+R). No ETL rerun is necessary if you already published station data.

If no published station data are found, the preview displays a clear message and the link to the full map remains usable. The station publisher is `python scripts/publish_station_map.py`. The page uses Leaflet JS/CSS and online map tile services.

## Files changed

- `app/routes.py`: supplies station catalog to homepage
- `app/templates/index.html`: replaces squeezed ridership chart with map preview
- `app/static/js/home_station_preview.js`: renders sample service/quarter from real FRA station API
- `app/static/css/home_station_preview.css`: responsive sizing
- `app/static/css/home_station_leaflet.css`: scoped offline-safe Leaflet geometry fallback

## Test

Visit `/` and `/projects/intercity-rail/stations`. Verify station dots, basemap alignment, and that the preview CTA reaches the full map. The preview is purposely a noninteractive teaser (tooltips enabled; map panning disabled). The full map remains interactive.
