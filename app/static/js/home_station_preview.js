/* Homepage FRA station preview. Uses the same validated endpoint as the full map. */
(() => {
  'use strict';
  const node = document.getElementById('home-station-map');
  const configNode = document.getElementById('home-station-config');
  const state = document.getElementById('home-station-state');
  if (!node || !configNode) return;
  const say = (message) => { state.hidden = false; state.textContent = message; };
  const hideMessage = () => { state.hidden = true; };
  const shade = p => p == null ? '#888888' : p < 20 ? '#2a9d8f' : p < 40 ? '#e9c46a' : p < 60 ? '#e76f51' : '#a3303a';
  let config;
  try { config = JSON.parse(configNode.textContent); }
  catch (_) { say('Station configuration is unavailable. Open the full map instead.'); return; }
  const services = Array.isArray(config.services) ? config.services : [];
  const wanted = services.find(s => /acela/i.test(s.label || '')) || services[0];
  if (!wanted) { say('No station service is available. Publish the station data first.'); return; }
  const periods = Array.isArray(config.periods) ? config.periods : [];
  const latest = periods.length ? periods[periods.length - 1] : 'all';
  const label = wanted.label || 'Selected service';
  document.getElementById('home-station-title').textContent = label + ' station reliability';
  document.getElementById('home-station-period').textContent = latest === 'all' ? 'All reported quarters' : 'FY' + latest;
  function start() {
    if (!window.L) { say('The mapping library did not load. Open the full station map.'); return; }
    const map = L.map(node, {scrollWheelZoom:false,zoomControl:false,dragging:false,doubleClickZoom:false,boxZoom:false,keyboard:false,touchZoom:false}).setView([40,-97],4);
    let sourceIndex = 0, errors = 0, loaded = 0, tileLayer = null;
    const sources = [
      {url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',attribution:'&copy; OpenStreetMap contributors'},
      {url:'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',attribution:'&copy; OpenStreetMap contributors &copy; CARTO'}
    ];
    function tiles(index) {
      if (tileLayer) map.removeLayer(tileLayer);
      sourceIndex=index;errors=0;loaded=0;
      tileLayer=L.tileLayer(sources[index].url,{maxZoom:18,attribution:sources[index].attribution});
      tileLayer.on('tileload',()=>{loaded++;});
      tileLayer.on('tileerror',()=>{errors++;if(sourceIndex===0 && errors>=4 && !loaded)tiles(1);});
      tileLayer.addTo(map);
    }
    tiles(0);
    const points=L.featureGroup().addTo(map);
    let frame;
    const resize=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>map.invalidateSize({pan:false}));};
    window.addEventListener('resize',resize);
    window.addEventListener('load',resize);
    if(window.ResizeObserver) new ResizeObserver(resize).observe(node);
    async function load(period) {
      const params=new URLSearchParams({service:wanted.id,period,min_customers:'1'});
      try {
        const response=await fetch('/api/rail/stations/detail?'+params.toString(),{cache:'no-store'});
        if(!response.ok)throw new Error('HTTP '+response.status);
        const data=await response.json();
        if(!Array.isArray(data.stations))throw new Error('missing station observations');
        let count=0;
        for(const s of data.stations){
          // Guard null coordinates: Number(null) = 0, which is not a real location.
          if(s.lat==null||s.lon==null||s.lat===''||s.lon==='')continue;
          const lat=Number(s.lat),lon=Number(s.lon);
          if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)continue;
          const n=Math.max(0,Number(s.detraining)||0);
          const circle=L.circleMarker([lat,lon],{radius:Math.min(11,Math.max(5,4+Math.sqrt(n)/28)),color:'#253344',weight:1.1,fillColor:shade(s.late_pct),fillOpacity:.9});
          circle.bindTooltip((s.station_name||s.station_code)+': '+(s.late_pct==null?'N/A':Number(s.late_pct).toFixed(1)+'%')+' arriving late');
          circle.addTo(points);count++;
        }
        if(!count && period!=='all')return load('all');
        if(!count) { say('No mappable station observations are available for this service.'); return; }
        const bounds=points.getBounds();
        if(bounds.isValid())map.fitBounds(bounds.pad(.17),{maxZoom:9,animate:false});
        resize();hideMessage();
      }catch(e){say('Station preview could not load ('+e.message+'). Open the full station map to investigate.');}
    }
    load(latest);
  }
  if(window.L){start();return;}
  say('Loading station map…');
  const backup=document.createElement('script');
  backup.src='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js';
  backup.onload=start;
  backup.onerror=()=>say('The map library could not be loaded. Open the full station map.');
  document.head.appendChild(backup);
})();
