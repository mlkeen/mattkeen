(() => {
  const root=document.getElementById('reliability-lab');if(!root)return;
  const all=[...document.querySelectorAll('#reliability-checklist input[type="checkbox"]')];
  const quarter=document.getElementById('reliability-quarter'),highlight=document.getElementById('reliability-highlight');
  const line=document.getElementById('reliability-regression'),chart=document.getElementById('reliability-chart');
  const status=document.getElementById('reliability-status'),note=document.getElementById('reliability-note');
  const count=document.getElementById('reliability-count');let active=null;let serial=0;
  const selected=()=>all.filter(x=>x.checked).map(x=>x.value);
  const fmt=x=>x==null?'—':x.toFixed(2);
  function draw(payload){
    active=payload;const ps=payload.points||[];const st=payload.stats;
    document.getElementById('reliability-n').textContent=ps.length.toLocaleString();
    document.getElementById('reliability-routes').textContent=payload.count_routes;
    document.getElementById('reliability-corr').textContent=st?fmt(st.correlation):'—';
    document.getElementById('reliability-r2').textContent=st?fmt(st.r_squared):'—';
    count.textContent=`${selected().length} services included`;
    note.textContent=ps.length?`${ps.length} matched route–quarter observations. ${st?'The line is a pooled descriptive regression; it is not causal.':'A regression requires three observations and variation in both measures.'}`:'No paired observations for this selection. Try all quarters or more services.';
    if(!window.Plotly){chart.textContent='Plotly has not loaded; the CSV export remains available.';return;}
    const emphasis=highlight.value;const dim=ps.filter(p=>emphasis!=='all'&&p.slug!==emphasis);
    const bright=ps.filter(p=>emphasis==='all'||p.slug===emphasis);
    const trace=(rows,color,opacity,name)=>({type:'scatter',mode:'markers',name,x:rows.map(p=>p.otp_change_pp),y:rows.map(p=>p.ridership_growth_pct),customdata:rows.map(p=>[p.name,p.period,p.otp,p.ridership]),marker:{color,opacity,size:9,line:{width:0.5,color:'#ffffff'}},hovertemplate:'<b>%{customdata[0]}</b> · %{customdata[1]}<br>OTP change: %{x:+.1f} pp<br>Ridership growth: %{y:+.1f}%<br>Customer OTP: %{customdata[2]:.1%}<br>Passengers: %{customdata[3]:,.0f}<extra></extra>'});
    let traces=[];if(dim.length)traces.push(trace(dim,'#afb5bc',0.38,'Other services'));if(bright.length)traces.push(trace(bright,'#315d6b',0.8,'Included observations'));
    if(line.checked&&st&&ps.length>=3){const xs=ps.map(p=>p.otp_change_pp);const low=Math.min(...xs),high=Math.max(...xs);traces.push({type:'scatter',mode:'lines',name:'Pooled OLS fit',x:[low,high],y:[st.intercept+st.slope*low,st.intercept+st.slope*high],line:{color:'#b66c46',width:2,dash:'dash'},hoverinfo:'skip'});}
    Plotly.react(chart,traces,{margin:{t:16,r:25,b:70,l:78},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',xaxis:{title:'Change in customer OTP (percentage points)',zeroline:true,gridcolor:'rgba(100,120,130,.13)'},yaxis:{title:'Year-over-year ridership growth (%)',zeroline:true,gridcolor:'rgba(100,120,130,.13)'},legend:{orientation:'h',y:-.33},hovermode:'closest',showlegend:traces.length>1},{responsive:true,displaylogo:false});
  }
  async function load(){const id=++serial;const routes=selected();count.textContent=`${routes.length} services included`;if(!routes.length){draw({points:[],count_routes:0,stats:null});status.textContent='Select at least one service.';return;}
    status.textContent='Updating chart…';const params=new URLSearchParams();routes.forEach(s=>params.append('route',s));params.set('period',quarter.value);
    try{const response=await fetch('/api/rail/reliability?'+params);const payload=await response.json();if(id!==serial)return;if(!response.ok)throw Error(payload.error||'Could not fetch observations');draw(payload);status.textContent='';}catch(err){if(id!==serial)return;status.textContent=err.message;}}
  let debounce;function schedule(){clearTimeout(debounce);debounce=setTimeout(load,120);}
  all.forEach(x=>x.addEventListener('change',schedule));quarter.addEventListener('change',load);highlight.addEventListener('change',()=>{if(active)draw(active);});line.addEventListener('change',()=>{if(active)draw(active);});
  document.getElementById('reliability-search').addEventListener('input',e=>{const q=e.target.value.toLowerCase().trim();document.querySelectorAll('#reliability-checklist .compare-choice').forEach(l=>{l.hidden=!l.dataset.search.includes(q) || (document.getElementById("reliability-category").value!=="all" && l.dataset.category!==document.getElementById("reliability-category").value);});});
  document.getElementById('reliability-select-all').addEventListener('click',()=>{all.forEach(x=>x.checked=!x.closest(".compare-choice").hidden);load();});document.getElementById('reliability-clear').addEventListener('click',()=>{all.forEach(x=>x.checked=false);load();});
  document.getElementById('reliability-export').addEventListener('click',()=>{if(!active||!active.points.length)return;const cols=['name','apt_code','category','period','otp_change_pp','ridership_growth_pct','otp','ridership','otp_source_workbook','ridership_source_workbook'];const escape=v=>'"'+String(v??'').replaceAll('"','""')+'"';const body=[cols.join(','),...active.points.map(p=>cols.map(c=>escape(p[c])).join(','))].join('\r\n');const link=document.createElement('a');const url=URL.createObjectURL(new Blob(['\ufeff'+body],{type:'text/csv;charset=utf-8'}));link.href=url;link.download='fra_reliability_vs_ridership.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  load();
})();
