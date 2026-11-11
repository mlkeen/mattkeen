/* Route Comparison Lab: no averaging of FRA OTP fractions or hidden name joins. */
(() => {
  const root = document.getElementById('comparison-lab');
  if (!root) return;
  const initial = JSON.parse(root.dataset.initial);
  const checkboxes = [...document.querySelectorAll('#compare-checklist input[type="checkbox"]')];
  const search = document.getElementById('compare-search');
  const metric = document.getElementById('compare-metric');
  const chart = document.getElementById('compare-chart');
  const note = document.getElementById('compare-chart-note');
  const error = document.getElementById('compare-error');
  const table = document.getElementById('compare-summary');
  const counter = document.getElementById('compare-count');
  const palette = ['#315d6b', '#ad653f', '#72835a', '#80649a'];
  let current = initial;
  let sequence = 0;

  const selected = () => checkboxes.filter(c => c.checked).map(c => c.value);
  const fmtCount = n => n == null ? '—' : Math.round(n).toLocaleString('en-US');
  const signed = (n, suffix) => n == null ? '—' : `${n > 0 ? '+' : ''}${n.toFixed(1)}${suffix}`;
  const fmtOTP = n => n == null ? '—' : `${(100*n).toFixed(1)}%`;
  const safeText = (el, str) => { el.textContent = str; };

  function updateCheckboxes() {
    const count = selected().length;
    safeText(counter, `${count} of 4 selected`);
    checkboxes.forEach(c => { c.disabled = !c.checked && count >= 4; });
  }

  function commonBase(routes, periods) {
    return periods.find(p => routes.every(r => {
      const point = r.series.find(v => v.period === p);
      return point && Number.isFinite(point.ridership) && point.ridership > 0;
    }));
  }

  function draw() {
    const routes = current.routes;
    const mode = metric.value;
    const base = commonBase(routes, current.periods);
    const hasOTP = routes.some(r => r.otp);
    const descriptions = {
      ridership: 'Quarterly reported total ridership (marketing), passengers. Differences in service scale are visible.',
      indexed: base ? `Ridership indexed to ${base} = 100 for every selected service. All routes use the same quarter as the baseline.` : 'No shared quarter with positive ridership across all selected routes; indexed comparison is unavailable.',
      growth: 'Year-over-year percentage change in ridership, comparing each fiscal quarter with the same quarter in the previous year. Missing or nonpositive prior values are excluded.',
      otp: hasOTP ? 'FRA customer on-time percentage. Only exact whole-service matches are drawn; others are intentionally omitted.' : 'None of these ridership service names have an unambiguous exact whole-service OTP match in the available data.'
    };
    safeText(note, descriptions[mode]);
    if (!routes.length || (mode === 'indexed' && !base) || (mode === 'otp' && !hasOTP)) {
      if (window.Plotly && chart.data) Plotly.purge(chart);
      safeText(chart, mode === 'otp' ? 'No directly matched customer OTP series for these services. Try another service or use the independent OTP selector in the Rail Explorer.' : 'Select services with a shared positive-ridership quarter.');
      return;
    }
    if (!window.Plotly) {
      safeText(chart, 'Interactive chart unavailable. The comparison table remains available below.');
      return;
    }
    const traces = routes.flatMap((route, index) => {
      if (mode === 'otp' && !route.otp) return [];
      const byPeriod = new Map((mode === 'otp' ? route.otp.series : route.series).map(p => [p.period, p]));
      const baseValue = base ? byPeriod.get(base)?.ridership : null;
      const y = current.periods.map(p => {
        const value = byPeriod.get(p);
        if (!value) return null;
        if (mode === 'ridership') return value.ridership;
        if (mode === 'growth') return value.yoy_pct;
        if (mode === 'otp') return value.otp == null ? null : value.otp * 100;
        return baseValue > 0 && value.ridership != null ? 100 * value.ridership / baseValue : null;
      });
      return [{x: current.periods, y, name:route.name, mode:'lines+markers', type:'scatter',
        connectgaps:false, line:{color:palette[index], width:2.6}, marker:{size:6},
        hovertemplate:`<b>${route.name.replace(/&/g,'&amp;').replace(/</g,'&lt;')}</b><br>%{x}<br>%{y:${mode === 'ridership' ? ',.0f' : '.1f'}}${mode === 'ridership' || mode === 'indexed' ? '' : '%'}<extra></extra>`}];
    });
    const axisTitle = {ridership:'RIDERS', indexed:'INDEX (BASE = 100)', growth:'RIDERSHIP GROWTH (%)', otp:'CUSTOMER OTP (%)'}[mode];
    Plotly.react(chart, traces, {
      paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
      font:{family:'IBM Plex Sans, sans-serif', color:'#20201e', size:12},
      margin:{l:68,r:20,t:22,b:78}, showlegend:true,
      legend:{orientation:'h',y:1.13,x:0}, hovermode:'x unified',
      xaxis:{title:'FISCAL QUARTER',tickangle:-45,gridcolor:'#d6d2c8'},
      yaxis:{title:axisTitle,gridcolor:'#d6d2c8',rangemode:mode === 'ridership' || mode === 'otp' ? 'tozero':'normal', ...(mode === 'otp' ? {range:[0,100]} : {})}
    }, {displayModeBar:false,responsive:true});
  }

  function fillTable() {
    table.replaceChildren();
    current.routes.forEach(r => {
      const tr = document.createElement('tr');
      const values = [r.name,fmtCount(r.latest_ridership),signed(r.yoy_pct,'%'),r.otp ? fmtOTP(r.otp.latest_otp):'—',`${r.quarters_valid} / ${current.periods.length}`];
      values.forEach((value, i) => {
        const td = document.createElement('td');
        if (i === 0) {const strong=document.createElement('strong');strong.textContent=value;td.append(strong);}
        else td.textContent=value;
        tr.append(td);
      });
      const td = document.createElement('td'); const a = document.createElement('a');
      a.href='/projects/intercity-rail/routes/' + encodeURIComponent(r.slug); a.textContent='Inspect →';
      td.append(a);tr.append(td);table.append(tr);
    });
  }
  const render = () => {fillTable();draw();};
  async function reload() {
    updateCheckboxes();
    const slugs = selected();
    if (!slugs.length) {safeText(error,'Select at least one service.');return;}
    safeText(error,'');
    const requestId = ++sequence;
    try {
      const query = new URLSearchParams(); slugs.forEach(s => query.append('route',s));
      const response = await fetch('/api/rail/compare?' + query.toString());
      const json = await response.json();
      if (!response.ok) throw new Error(json.error || `HTTP ${response.status}`);
      if (requestId === sequence) {current = json;render();}
    } catch (e) {if (requestId === sequence) safeText(error,`Could not refresh comparison: ${e.message}`);}
  }
  checkboxes.forEach(c => c.addEventListener('change', reload));
  search.addEventListener('input', () => {
    const q=search.value.trim().toLowerCase();
    document.querySelectorAll('.compare-choice').forEach(el => {el.hidden=(!el.dataset.search.includes(q)) || (document.getElementById("compare-category").value!=="all" && el.dataset.category!==document.getElementById("compare-category").value);});
  });
  const pick=document.getElementById('compare-pick-visible');
  if(pick)pick.addEventListener('click',()=>{
    const visible=checkboxes.filter(c=>!c.closest('.compare-choice').hidden).slice(0,4);
    if(!visible.length){safeText(error,'No matching services in this group.');return;}
    checkboxes.forEach(c=>c.checked=visible.includes(c));reload();
  });
  metric.addEventListener('change',draw);
  updateCheckboxes();render();
})();
