/* Station map: Leaflet layout, basemap fallback, and validated FRA station markers. */
(() => {
  'use strict';
  const root = document.getElementById('station-map-explorer');
  if (!root || !document.getElementById('station-map')) return;
  const status = document.getElementById('station-status');
  const say = message => { if (status) status.textContent = message; };

  function start() {
    if (!window.L) { say('Unable to load the mapping library. Check your internet connection or browser blocker.'); return; }
    const group = document.getElementById('station-category');
    const service = document.getElementById('station-service');
    const period = document.getElementById('station-period');
    const minimum = document.getElementById('station-minimum');
    const tbody = document.getElementById('station-table-body');
    const formatter = new Intl.NumberFormat('en-US');
    const percent = v => v == null ? 'N/A' : Number(v).toFixed(1) + '%';
    const shade = p => p == null ? '#888' : p < 20 ? '#2a9d8f' : p < 40 ? '#e9c46a' : p < 60 ? '#e76f51' : '#a3303a';
    const map = L.map('station-map', { scrollWheelZoom: false, preferCanvas: false, zoomControl: true }).setView([39, -98], 4);
    const dots = L.featureGroup().addTo(map);

    // CDN map-tile requests can fail independently of the station API.
    // Try a second provider while keeping our locally bundled Leaflet geometry CSS.
    let tileLayer = null;
    let provider = 0;
    let tileFailures = 0;
    let tileSuccesses = 0;
    const tileSources = [
      {url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png', credit:'&copy; OpenStreetMap contributors'},
      {url:'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png', credit:'&copy; OpenStreetMap contributors &copy; CARTO'}
    ];
    function loadTiles(n) {
      if (tileLayer) map.removeLayer(tileLayer);
      provider = n; tileFailures = 0; tileSuccesses = 0;
      tileLayer = L.tileLayer(tileSources[n].url, {
        maxZoom: 18, attribution: tileSources[n].credit, crossOrigin: true, updateWhenIdle: true
      });
      tileLayer.on('tileload', () => { tileSuccesses++; });
      tileLayer.on('tileerror', () => {
        tileFailures++;
        if (provider === 0 && tileFailures >= 4 && tileSuccesses === 0) {
          loadTiles(1);
          say('Primary basemap unavailable; trying an alternate map provider.');
        } else if (provider === 1 && tileFailures >= 4 && tileSuccesses === 0) {
          say('Map tiles are blocked or unavailable. Station locations should still appear on the plain map background.');
        }
      });
      tileLayer.addTo(map);
    }
    loadTiles(0);
    let frame = 0;
    function resize() { cancelAnimationFrame(frame); frame = requestAnimationFrame(() => map.invalidateSize({pan:false,debounceMoveend:true})); }
    // Leaflet needs correct dimensions both after initial paint and after layout changes.
    resize(); window.addEventListener('load', resize); window.addEventListener('resize', resize);
    if (window.ResizeObserver) new ResizeObserver(resize).observe(document.getElementById('station-map'));

    const visibleOptions = () => Array.from(service.options).filter(o => !o.value || group.value === 'all' || o.dataset.category === group.value);
    function updateOptions() {
      const allowed = new Set(visibleOptions().map(o => o.value));
      Array.from(service.options).forEach(o => o.hidden = !allowed.has(o.value));
      service.value = group.value !== 'all' ? '' : (allowed.has(service.value) && service.value ? service.value : (visibleOptions().find(o=>o.value)?.value || ''));
      load();
    }
    let generation = 0;
    async function load() {
      const current = ++generation;
      dots.clearLayers(); tbody.replaceChildren();
      ['station-count','station-detraining','station-late'].forEach(id => document.getElementById(id).textContent = '—');
      if (!service.value && group.value === 'all') { say('Choose a service group or a specific service.'); return; }
      say('Loading station observations…');
      try {
        const query = new URLSearchParams({service:service.value || 'group:'+group.value,period:period.value,min_customers:minimum.value});
        const response = await fetch('/api/rail/stations/detail?' + query.toString(), {cache:'no-store'});
        if (!response.ok) throw new Error('Station API returned HTTP ' + response.status);
        const payload = await response.json();
        if (current !== generation) return;
        if (!Array.isArray(payload.stations)) throw new Error('Unexpected response: stations array missing');
        let valid = 0, skipped = 0;
        for (const s of payload.stations) {
          const lat = Number(s.lat), lon = Number(s.lon);
          if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) {skipped++; continue;}
          const p = s.late_pct;
          const marker = L.circleMarker([lat,lon], {
            radius:Math.min(18,Math.max(6,4 + Math.sqrt(Math.max(0,Number(s.detraining)||0))/18)),
            color:'#253344',weight:1.5,fillColor:shade(p),fillOpacity:.87,opacity:1,interactive:true
          }).addTo(dots);
          const popup = document.createElement('div');
          const heading = document.createElement('strong');
          heading.textContent = (s.station_name || s.station_code) + ' (' + s.station_code + ')';
          const detail = document.createElement('p');
          detail.textContent = formatter.format(s.late) + ' of ' + formatter.format(s.detraining) + ' detraining passengers arrived late (' + percent(p) + ').';
          popup.append(heading,detail); marker.bindPopup(popup);
          const tr = document.createElement('tr');
          const cell0 = document.createElement('td');
          const jump = document.createElement('button'); jump.type='button'; jump.className='station-row-button';
          jump.textContent = (s.station_name || s.station_code) + ' (' + s.station_code + ')';
          jump.addEventListener('click',() => {resize();map.setView([lat,lon],Math.max(8,map.getZoom()));marker.openPopup();});
          cell0.appendChild(jump); tr.appendChild(cell0);
          [formatter.format(s.detraining),formatter.format(s.late),percent(p),s.avg_minutes_late == null ? 'N/A' : Number(s.avg_minutes_late).toFixed(1)].forEach(value => {
            const td=document.createElement('td');td.textContent=value;tr.appendChild(td);
          });
          tbody.appendChild(tr); valid++;
        }
        document.getElementById('station-count').textContent = formatter.format(valid);
        document.getElementById('station-detraining').textContent = formatter.format(payload.detraining_passengers || 0);
        document.getElementById('station-late').textContent = payload.detraining_passengers ? percent(100*payload.late_passengers/payload.detraining_passengers) : 'N/A';
        resize();
        if (valid) {
          const bounds = dots.getBounds();
          if (bounds.isValid()) map.fitBounds(bounds.pad(.16),{maxZoom:10,animate:false});
          resize();
          say(valid + ' station locations shown.' + (skipped ? ' ' + skipped + ' invalid coordinates omitted.' : ''));
        } else say(payload.stations.length ? 'Station data loaded but coordinates were invalid.' : 'No stations meet the current filters. Try 1+ passengers and All available quarters.');
      } catch(e) {
        if (current !== generation) return;
        say('Station map unavailable: ' + e.message + '. Check /api/rail/stations and your Flask terminal.');
      }
    }
    group.addEventListener('change', updateOptions);
    service.addEventListener('change',load);
    period.addEventListener('change',load);
    minimum.addEventListener('change',load);
    const downeaster = Array.from(service.options).find(o => /downeaster/i.test(o.textContent));
    if (downeaster) service.value = downeaster.value;
    load();
  }
  if (window.L) {start();return;}
  // If unpkg's script was blocked, try a second library CDN.
  say('Loading map library from backup provider…');
  const script=document.createElement('script');
  script.src='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js';
  script.onload=start;
  script.onerror=()=>say('Leaflet failed to load from both providers. Check network restrictions or browser content blockers.');
  document.head.appendChild(script);
})();
