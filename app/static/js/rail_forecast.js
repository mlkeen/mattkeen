(() => {
  const el=id=>document.getElementById(id);
  let counties=[], stops=[], lastResult=null, demo=false;
  const fmt=n=>Number(n).toLocaleString('en-US',{maximumFractionDigits:0});
  const digits=n=>Number(n).toLocaleString('en-US',{maximumFractionDigits:1});
  const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function selected() {return stops.map(f=>counties.find(c=>c.fips===f)).filter(Boolean)}
  function refreshStops(){
    el('rf-stopcount').textContent=`${stops.length} / 12`;
    el('rf-stops').innerHTML=selected().map((c,i)=>`<li><span class="rf-stop-name"><b>${i+1}.</b> ${escape(c.name)}, ${escape(c.state)}</span><span class="rf-stop-actions"><button title="Move earlier" data-action="up" data-i="${i}" ${i===0?'disabled':''}>↑</button><button title="Move later" data-action="down" data-i="${i}" ${i===stops.length-1?'disabled':''}>↓</button><button title="Remove stop" data-action="remove" data-i="${i}">×</button></span></li>`).join('')||'<li>Select at least two counties.</li>';
    drawMap();
  }
  function drawMap(){
    if(!window.Plotly){el('rf-map').textContent='Map requires Plotly. Check the network or disable content blockers.';return}
    const cs=selected();
    Plotly.react('rf-map',[{type:'scattergeo',mode:'lines+markers+text',lon:cs.map(c=>c.lon),lat:cs.map(c=>c.lat),text:cs.map((c,i)=>String(i+1)),textposition:'top center',marker:{size:11,color:'#bd643c',line:{width:2,color:'white'}},line:{color:'#315e71',width:3},customdata:cs.map(c=>[c.name,c.state,c.population]),hovertemplate:'%{customdata[0]}, %{customdata[1]}<br>County population: %{customdata[2]:,}<extra></extra>'}],{geo:{scope:'usa',projection:{type:'albers usa'},showland:true,landcolor:'#eaf0ee',showlakes:true,lakecolor:'#fff',subunitcolor:'#c1ccd0',showsubunits:true,bgcolor:'rgba(0,0,0,0)'},margin:{l:5,r:5,t:5,b:5},paper_bgcolor:'rgba(0,0,0,0)',showlegend:false},{responsive:true,displayModeBar:false});
  }
  function search(){
    const q=el('rf-search').value.trim().toLowerCase();
    if(q.length<2){el('rf-results').innerHTML='<p class="rf-help" style="padding:8px">Type at least two characters to search.</p>';return}
    const matches=counties.filter(c=>`${c.name} ${c.state} ${c.fips}`.toLowerCase().includes(q)&&!stops.includes(c.fips)).slice(0,15);
    el('rf-results').innerHTML=matches.map(c=>`<button class="rf-result" data-fips="${c.fips}">${escape(c.name)}, ${escape(c.state)} <small>(${fmt(c.population)})</small></button>`).join('')||'<p class="rf-help" style="padding:8px">No matching counties.</p>';
  }
  function calcPayload(){return {stops,
    round_trips:+el('rf-freq').value,rail_speed:+el('rf-speed').value,fare_per_mile:+el('rf-fare').value,
    rail_detour:+el('rf-detour').value,base_trip_rate:+el('rf-rate').value,distance_exponent:+el('rf-exponent').value,
    rail_intercept:+el('rf-intercept').value,rail_sensitivity:+el('rf-sensitivity').value,
    frequency_elasticity:+el('rf-elasticity').value,access_hours:+el('rf-access').value,value_of_time:+el('rf-vot').value,
    road_speed:+el('rf-road-speed').value,road_detour:+el('rf-road-detour').value,auto_cost_mile:+el('rf-auto-cost').value,
    market_factor:+el('rf-market').value}}
  async function estimate(){
    el('rf-error').textContent=''; if(stops.length<2){el('rf-error').textContent='Choose at least two stops.';return}
    el('rf-estimate').disabled=true;
    try{
      const r=await fetch('/api/rail-forecast/estimate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(calcPayload())});
      const d=await r.json(); if(!r.ok)throw Error(d.error||'Estimate failed');lastResult=d;
      el('rf-rides').textContent=fmt(d.annual_ridership);el('rf-pm').textContent=fmt(d.annual_passenger_miles);el('rf-miles').textContent=`${fmt(d.route_miles)} mi`;
      el('rf-outcome-note').textContent=(demo?'DEMONSTRATION CENSUS INPUTS. ':'')+(d.nhts?`2022 NHTS weighted long-distance annualized rate ${digits(d.nhts.long_distance_trips_per_person_annualized)} trips/person; reported Amtrak uses/person ${digits(d.nhts.amtrak_uses_per_person_past_year)}. `:'')+(d.calibration?`FY${d.calibration.fiscal_year} Amtrak total-ridership scaling: ${d.calibration.reference_routes} reference routes; leave-one-route-out median absolute error ${d.calibration.median_loo_error_pct}%. `:'')+d.warning;
      el('rf-download').disabled=false;
      el('rf-od-body').innerHTML=d.od.slice().sort((a,b)=>b.annual_rides-a.annual_rides).map(o=>`<tr><td>${escape(o.origin)}</td><td>${escape(o.destination)}</td><td>${digits(o.distance_miles)}</td><td>${(o.rail_share*100).toFixed(1)}%</td><td>${fmt(o.annual_rides)}</td></tr>`).join('');
      if(window.Plotly){
        Plotly.react('rf-load-chart',[{type:'bar',orientation:'h',y:d.segments.map(s=>`${s.from} → ${s.to}`).reverse(),x:d.segments.map(s=>s.annual_passenger_trips).reverse(),marker:{color:'#386d80'},hovertemplate:'%{y}<br>%{x:,} annual trips<extra></extra>'}],{height:Math.max(200,d.segments.length*48+70),margin:{l:170,r:25,t:15,b:55},xaxis:{title:'Annual passenger journeys on segment'},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)'},{responsive:true,displayModeBar:false});
      }
    }catch(err){el('rf-error').textContent=err.message}finally{el('rf-estimate').disabled=false}
  }
  function csvExport(){if(!lastResult)return;const columns=['origin_fips','destination_fips','origin','destination','distance_miles','rail_time_hours','auto_time_hours','rail_share','annual_rides'];const esc=s=>'"'+String(s??'').replace(/"/g,'""')+'"';const csv=[columns.join(','),...lastResult.od.map(r=>columns.map(c=>esc(r[c])).join(','))].join('\r\n');const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=(lastResult.calibration?'rail_corridor_empirically_scaled_od.csv':'rail_corridor_illustrative_od.csv');a.click();URL.revokeObjectURL(url)}
  fetch('/api/rail-forecast/calibration').then(r=>r.ok?r.json():null).then(d=>{
    if(!d)return;
    const rows=d.training_routes||[];
    const heading=`<p><b>FY${escape(d.fiscal_year)} route totals:</b> ${fmt(d.reference_routes)} reference corridors · ${digits(d.median_absolute_percentage_error_loo)}% median absolute leave-one-corridor-out error.</p>`;
    const table=`<div class="rf-table-wrap"><table class="rf-table"><thead><tr><th>Reference corridor</th><th>Observed annual rides</th><th>Leave-out prediction</th><th>Absolute % error</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${escape(r.route)}</td><td>${fmt(r.observed)}</td><td>${fmt(r.leave_one_out_prediction)}</td><td>${digits(r.absolute_percentage_error_loo)}%</td></tr>`).join('')}</tbody></table></div>`;
    el('rf-calibration-details').innerHTML=heading+table+'<p>Model fitted to observed route totals only. Representative county sequences are manually selected; frequencies, fares, times and OD shares are assumptions. Errors are cross-validation diagnostics, not confidence bounds for a new corridor.</p>';
  }).catch(()=>{});
  el('rf-search').addEventListener('input',search);
  el('rf-results').addEventListener('click',e=>{const b=e.target.closest('[data-fips]');if(b&&stops.length<12){stops.push(b.dataset.fips);refreshStops();search()}});
  el('rf-stops').addEventListener('click',e=>{const b=e.target.closest('button[data-action]');if(!b)return;let i=+b.dataset.i;if(b.dataset.action==='remove')stops.splice(i,1);if(b.dataset.action==='up'&&i>0)[stops[i-1],stops[i]]=[stops[i],stops[i-1]];if(b.dataset.action==='down'&&i<stops.length-1)[stops[i+1],stops[i]]=[stops[i],stops[i+1]];refreshStops()});
  el('rf-estimate').addEventListener('click',estimate);el('rf-download').addEventListener('click',csvExport);
  fetch('/api/rail-forecast/nhts').then(r=>r.ok?r.json():null).then(d=>{
    if(d){
      el('rf-rate').value=Number(d.annualized_long_distance_trips_per_person).toFixed(3);
      el('rf-nhts-status').textContent=`2022 NHTS V2.1 published: ${fmt(d.counts.weight_valid)} weighted person records; ${digits(d.annualized_long_distance_trips_per_person)} annualized trips of 50+ miles/person; ${Number(d.amtrak_uses_per_person_past_year).toFixed(3)} Amtrak uses/person/year. National benchmarks only, not OD or mode-choice calibration.`;
    }
  }).catch(()=>{}).finally(()=>{
  fetch('/api/rail-forecast/counties').then(r=>r.json()).then(d=>{
    counties=d.counties||[];demo=counties.some(c=>String(c.source).includes('SYNTHETIC'));
    el('rf-source-badge').textContent=demo?'DEMO INPUTS — RUN CENSUS PUBLISHER':`${fmt(counties.length)} Census counties`;
    if(counties.length){stops=['25025','44007','09009','36061','42101'].filter(f=>counties.some(c=>c.fips===f)); if(stops.length<2)stops=counties.slice(0,3).map(c=>c.fips);refreshStops();search();estimate()}
  }).catch(err=>{el('rf-error').textContent='Could not load county data: '+err.message});
  });
})();
