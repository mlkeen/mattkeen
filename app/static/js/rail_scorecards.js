(() => {
  'use strict';
  const app = document.getElementById('scorecards-app');
  if (!app) return;
  const el = id => document.getElementById(id);
  const controls = ['sc-period','sc-category','sc-sort','sc-min-riders','sc-order','sc-search'];
  const byId = Object.fromEntries(controls.map(id => [id, el(id)]));
  const groupNames = {acela:'Acela',state_supported:'State Supported',long_distance:'Long Distance',nec_other:'Other NEC',special:'Special / Unclassified'};
  const metricTitles = {ridership:'Ridership',yoy_pct:'Ridership growth',customer_otp_pct:'Customer OTP',cost_recovery_pct:'Cost recovery',avoidable_coverage_pct:'Avoidable expense coverage',revenue_per_rider:'Revenue per rider',revenue_per_passenger_mile:'Revenue per passenger-mile'};
  let data = [], shown = [], requestId = 0;
  const formatNumber = (x, digits=0) => x == null ? 'N/A' : Number(x).toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits});
  const formatPct = (x, signed=false) => x == null ? 'N/A' : `${signed && x > 0 ? '+' : ''}${formatNumber(x,1)}%`;
  const formatMoney = (x, digits=2) => x == null ? 'N/A' : `$${formatNumber(x,digits)}`;
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function applySearch(){
    const needle = byId['sc-search'].value.trim().toLowerCase();
    shown = data.filter(r => `${r.name} ${r.apt_code} ${groupNames[r.category] ?? ''}`.toLowerCase().includes(needle));
    render();
  }
  function render(){
    const ranking = byId['sc-sort'].value;
    el('sc-title').textContent = `${metricTitles[ranking]} · ${byId['sc-period'].value}`;
    el('scorecards-count').textContent = `${shown.length} displayed / ${data.length} eligible routes`;
    el('sc-coverage').textContent = `${data.filter(r => r[ranking] !== null).length} routes have a reported value for this metric`;
    const table = el('sc-rows');
    if (!shown.length) {table.innerHTML = '<tr><td colspan="10">No routes match these filters.</td></tr>';return;}
    table.innerHTML = shown.map((r,i) => {
      const revSrc = r.revenue_source ? `${r.revenue_source.workbook || ''} · ${r.revenue_source.sheet || ''} · row ${r.revenue_source.row || '?'}` : `Financial value: ${r.revenue_status}`;
      const tip = `Ridership: ${(r.ridership_source || {}).workbook || 'unknown'} · row ${(r.ridership_source || {}).row || '?'}; ${revSrc}`;
      const source = `<span class="sc-source" title="${escape(tip)}">${r.revenue_per_rider !== null ? 'Matched' : escape(r.revenue_status.replaceAll('_',' '))}</span>`;
      return `<tr><td>${r[ranking] == null ? '—' : i + 1}</td><td><a href="/projects/intercity-rail/routes/${encodeURIComponent(r.slug)}"><strong>${escape(r.name)}</strong></a><small>${escape(r.apt_code)}</small></td><td>${escape(groupNames[r.category] || r.category)}</td><td class="sc-num">${formatNumber(r.ridership)}</td><td class="sc-num">${formatPct(r.yoy_pct,true)}</td><td class="sc-num">${formatPct(r.customer_otp_pct)}</td><td class="sc-num">${formatPct(r.cost_recovery_pct)}</td><td class="sc-num">${formatMoney(r.revenue_per_rider)}</td><td class="sc-num">${formatMoney(r.revenue_per_passenger_mile,3)}</td><td>${source}</td></tr>`;
    }).join('');
  }
  async function load(){
    const id = ++requestId;
    el('sc-message').textContent = 'Loading reported route observations…';
    const args = new URLSearchParams({period:byId['sc-period'].value,category:byId['sc-category'].value,
      sort:byId['sc-sort'].value,direction:byId['sc-order'].value,minimum_riders:byId['sc-min-riders'].value});
    try {
      const response = await fetch(`/api/rail/scorecards?${args}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
      if (id !== requestId) return;
      const groupPanel = el('sc-group-summary');
      groupPanel.hidden = !payload.group_summary;
      if (payload.group_summary) {
        const g = payload.group_summary;
        el('sc-group-heading').textContent = g.label + ' · ' + payload.period;
        el('sc-group-riders').textContent = formatNumber(g.ridership);
        el('sc-group-revrider').textContent = formatMoney(g.revenue_per_rider);
        el('sc-group-revmile').textContent = formatMoney(g.revenue_per_passenger_mile,3);
        el('sc-group-note').textContent = g.note + ' (' + g.route_count + ' reporting routes in the selected quarter.)';
      }
      data = payload.rows;
      el('sc-message').textContent = '';
      applySearch();
    } catch(err) {
      if (id !== requestId) return;
      el('sc-group-summary').hidden = true;
      data = [];
      el('sc-message').textContent = `Unable to load scorecards: ${err.message}`;
      applySearch();
    }
  }
  const csvCell = v => `"${String(v ?? '').replaceAll('"','""')}"`;
  function download(){
    if (!shown.length) return;
    const columns = ['period','name','apt_code','category','ridership','yoy_pct','customer_otp_pct',
      'cost_recovery_pct','avoidable_coverage_pct','passenger_revenue','passenger_miles',
      'revenue_per_rider','revenue_per_passenger_mile','revenue_status'];
    const body = [columns.join(','),...shown.map(r => columns.map(k => csvCell(r[k])).join(','))].join('\r\n');
    const url = URL.createObjectURL(new Blob(['\uFEFF'+body],{type:'text/csv;charset=utf-8'}));
    const a = document.createElement('a');a.href=url;a.download=`fra_rail_scorecards_${byId['sc-period'].value.replaceAll(' ','_')}.csv`;
    document.body.appendChild(a);a.click();a.remove();setTimeout(() => URL.revokeObjectURL(url),1000);
  }
  controls.filter(id=>id!=='sc-search').forEach(id => byId[id].addEventListener('change',load));
  byId['sc-search'].addEventListener('input',applySearch);
  el('sc-export').addEventListener('click',download);
  load();
})();
