(() => {
  const root = document.getElementById('delay-explorer');
  if (!root) return;
  const overview = JSON.parse(root.dataset.overview);
  const service = document.getElementById('delay-service');
  if (!service) return;
  const period = document.getElementById('delay-quarter');
  const search = document.getElementById('delay-search');
  const message = document.getElementById('delay-message');
  const total = document.getElementById('delay-total');
  const name = document.getElementById('delay-name');
  const palette = ['#315d6b','#ad653f','#72835a','#80649a','#a98b47','#b06779'];
  let current = null, seq = 0;
  const causeList = document.getElementById('delay-cause-key');
  const causeSearch = document.getElementById('delay-cause-search');
  const sourceLink = document.getElementById('delay-code-source');
  let codes = {};
  const escapeHtml = value => String(value).replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
  const causeInfo = code => codes[code] || {label:'Unverified code',explanation:'No match in the FRA FY2024 Q4 glossary.',official_responsibility:'Unverified'};
  function drawCauseKey() {
    if (!causeList) return;
    const totals = current ? group(selected(current.causes), 'code') : [];
    const filter = (causeSearch?.value || '').trim().toLowerCase();
    const rows = totals.filter(([code]) => {
      const info = causeInfo(code);
      return [code, info.label, info.explanation, info.official_responsibility].some(value => value.toLowerCase().includes(filter));
    });
    causeList.innerHTML = rows.length ? rows.map(([code,minutes]) => {
      const info=causeInfo(code);
      return `<tr><td><strong>${escapeHtml(code)}</strong></td><td>${escapeHtml(info.label)}<small class="delay-code-note">${escapeHtml(info.explanation)}</small></td><td>${escapeHtml(info.official_responsibility)}</td><td class="delay-numeric">${fmt(minutes)}</td></tr>`;
    }).join('') : '<tr><td colspan="4">No matching delay causes for this selection.</td></tr>';
  }
  if (causeSearch) causeSearch.addEventListener('input', drawCauseKey);
  const fmt = n => Math.round(n).toLocaleString('en-US');
  const group = (rows, label) => {
    const result = new Map();
    for (const row of rows) result.set(row[label], (result.get(row[label]) || 0) + row.minutes);
    return [...result].sort((a,b) => b[1] - a[1]);
  };
  const selected = rows => period.value === 'all' ? rows : rows.filter(r => r.period === period.value);
  const chart = (id,traces,layout={}) => {
    const el = document.getElementById(id);
    if (!window.Plotly) { el.textContent='Chart library unavailable; check your connection.'; return; }
    Plotly.react(el,traces,{
      paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',
      font:{family:'IBM Plex Sans, sans-serif',size:12,color:'#20201e'},
      margin:{t:22,l:70,r:22,b:78},showlegend:true,hovermode:'closest',
      xaxis:{gridcolor:'#dedbd3'},yaxis:{gridcolor:'#dedbd3',rangemode:'tozero'},...layout
    },{displayModeBar:false,responsive:true});
  };
  const empty = () => ['delay-trend','delay-responsibility','delay-causes','delay-hosts'].forEach(id => {const el=document.getElementById(id);if(window.Plotly&&el.data)Plotly.purge(el);el.textContent='No reported observations for this selection.';});
  function render() {
    if (!current) {empty();drawCauseKey();return;}
    const trends = current.trends;
    const resp = selected(current.responsibilities);
    const causes = selected(current.causes);
    const hosts = selected(current.hosts);
    const sum = resp.reduce((n,r) => n+r.minutes,0);
    total.textContent = fmt(sum);
    name.textContent = current.service.label;
    message.textContent = `${period.value === 'all' ? 'All reported quarters' : period.value}: ${fmt(sum)} delay minutes. Figures can change with service volume; do not treat these as rate comparisons.`;
    const responsibilities = [...new Set(current.responsibilities.map(r=>r.responsibility))].sort();
    chart('delay-trend', responsibilities.map((label, i) => {
      const m = new Map(current.responsibilities.filter(r=>r.responsibility===label).map(r=>[r.period,r.minutes]));
      return {type:'bar',name:label,x:current.periods,y:current.periods.map(p=>m.has(p)?m.get(p):null),marker:{color:palette[i%palette.length]},hovertemplate:`%{x}<br>${label}: %{y:,.0f} minutes<extra></extra>`};
    }),{barmode:'stack',xaxis:{tickangle:-45,gridcolor:'#dedbd3'},yaxis:{title:'DELAY MINUTES',gridcolor:'#dedbd3',rangemode:'tozero'},legend:{orientation:'h',y:1.16,x:0}});
    const respSums = group(resp,'responsibility');
    chart('delay-responsibility',[{type:'bar',orientation:'h',x:respSums.map(x=>x[1]).reverse(),y:respSums.map(x=>x[0]).reverse(),marker:{color:'#315d6b'},hovertemplate:'%{y}: %{x:,.0f} minutes<extra></extra>'}],{margin:{l:135,r:15,t:22,b:55},showlegend:false,xaxis:{title:'DELAY MINUTES'},yaxis:{automargin:true}});
    const causeSums=group(causes,'code').slice(0,12).reverse();
    const causeLabels = causeSums.map(([code]) => `${code} — ${causeInfo(code).label}`);
    const causeDetail = causeSums.map(([code]) => `${code}: ${causeInfo(code).label}<br>${causeInfo(code).explanation}<br>FRA category: ${causeInfo(code).official_responsibility}`);
    chart('delay-causes',[{type:'bar',orientation:'h',x:causeSums.map(x=>x[1]),y:causeLabels,customdata:causeDetail,marker:{color:'#ad653f'},hovertemplate:'%{customdata}<br>%{x:,.0f} delay minutes<extra></extra>'}],{margin:{l:245,r:20,t:22,b:55},height:Math.max(380, causeSums.length*40),showlegend:false,xaxis:{title:'DELAY MINUTES'},yaxis:{automargin:true}});
    drawCauseKey();
    const hostSums=group(hosts,'host').slice(0,15).reverse();
    chart('delay-hosts',[{type:'bar',orientation:'h',x:hostSums.map(x=>x[1]),y:hostSums.map(x=>x[0]),marker:{color:'#72835a'},hovertemplate:'Host %{y}: %{x:,.0f} minutes<extra></extra>'}],{margin:{l:90,r:20,t:22,b:55},showlegend:false,xaxis:{title:'DELAY MINUTES'}});
  }
  service.addEventListener('change',async () => {
    const id=service.value, n=++seq;
    const group = document.getElementById('delay-category')?.value || 'all';
    const resolved = id || (group !== 'all' ? 'group:'+group : '');
    if (!resolved) {current=null;total.textContent='—';name.textContent='—';empty();drawCauseKey();return;}
    message.textContent='Loading delay breakdowns…';
    try {
      const response=await fetch('/api/rail/delays/'+encodeURIComponent(resolved));
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const json=await response.json();
      if(n===seq){
        current=json;
        const glossary = json.delay_code_dictionary || {};
        codes=glossary.definitions || {};
        if(sourceLink && glossary.source_url) {sourceLink.href=glossary.source_url; sourceLink.textContent=glossary.source_title || 'FRA delay-code dictionary';}
        render();
      }
    } catch(e) {if(n===seq){current=null;empty();message.textContent=`Could not load delay data: ${e.message}`;}}
  });
  period.addEventListener('change',render);
  search.addEventListener('input',() => {
    const q=search.value.trim().toLowerCase();
    [...service.options].forEach(o=>{if(o.value)o.hidden=!o.textContent.toLowerCase().includes(q) || (document.getElementById("delay-category").value!=="all" && o.dataset.category!==document.getElementById("delay-category").value);});
  });
  const preferred=[...service.options].find(o=>/downeaster/i.test(o.textContent));
  service.value=(preferred||service.options[1]||service.options[0]).value;
  if(service.value) service.dispatchEvent(new Event('change'));
})();
