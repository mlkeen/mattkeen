const INK = '#20201e';
const MUTED = '#66635d';
const ACCENT = '#315d6b';
const OTP_COLOR = '#ad653f';
const LINE = '#d6d2c8';

function baseLayout(compact=false) {
  return {
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    font: {family: 'IBM Plex Sans, sans-serif', color: INK, size: 12},
    margin: compact ? {l:50,r:10,t:12,b:57} : {l:70,r:28,t:30,b:78},
    showlegend: false,
    xaxis: {gridcolor: LINE, title: 'FISCAL QUARTER', tickangle: -45},
    yaxis: {gridcolor: LINE, tickformat: ',.0f', rangemode:'tozero', title:'RIDERS'},
    hovermode: 'x unified'
  };
}

function drawRidership(el, series, compact=false) {
  if (!el) return;
  if (typeof Plotly === 'undefined') {
    el.innerHTML = '<p class="chart-fallback">Interactive chart unavailable. The ridership tables remain accessible below.</p>';
    return;
  }
  Plotly.react(el, [{
    x: series.map(row => row.period),
    y: series.map(row => row.ridership),
    mode: 'lines+markers', type:'scatter', connectgaps:false,
    line: {color: ACCENT, width:2.5}, marker: {color: ACCENT, size:compact?5:7},
    hovertemplate: '<b>%{x}</b><br>Ridership: %{y:,.0f}<extra></extra>'
  }], baseLayout(compact), {displayModeBar:false,responsive:true});
}

function drawOTP(el, detail) {
  if (!el) return;
  if (!detail || !detail.series) {
    if (typeof Plotly !== 'undefined' && el.data) Plotly.purge(el);
    el.innerHTML = '<p class="chart-fallback">No directly matched OTP series selected. Choose a service/subservice above to view the FRA route-level observations.</p>';
    return;
  }
  if (typeof Plotly === 'undefined') {
    el.innerHTML = '<p class="chart-fallback">Interactive chart unavailable. Source records remain accessible via the route details and API.</p>';
    return;
  }
  const layout = baseLayout();
  layout.yaxis = {gridcolor: LINE, title: 'CUSTOMER OTP (%)', ticksuffix: '%', range: [0,100], dtick:20};
  Plotly.react(el, [{
    x: detail.series.map(row => row.period),
    y: detail.series.map(row => row.otp == null ? null : row.otp * 100),
    mode: 'lines+markers', type: 'scatter', connectgaps:false,
    line: {color: OTP_COLOR, width:2.5}, marker: {color: OTP_COLOR, size:7},
    hovertemplate: '<b>%{x}</b><br>Customer OTP: %{y:.1f}%<extra></extra>'
  }], layout, {displayModeBar:false,responsive:true});
}

function formatCount(n) { return n == null ? 'Not reported' : Math.round(n).toLocaleString('en-US'); }
function formatYoY(n) { return n == null ? 'N/A' : (n>0?'+':'') + n.toFixed(1) + '%'; }
function formatPp(n) { return n == null ? 'N/A' : (n>0?'+':'') + n.toFixed(1) + ' pp'; }
function formatOTP(n) { return n == null ? 'N/A' : (n*100).toFixed(1) + '%'; }

function renderOTP(detail, noteText) {
  const name = document.getElementById('otp-selected-name');
  if (!name) return;
  name.textContent = detail ? detail.label : 'Choose a reported subservice';
  document.getElementById('otp-selected-coverage').textContent = detail ? detail.quarters_valid + ' quarters with reported percentages' : 'No series selected';
  document.getElementById('otp-selected-latest').textContent = detail ? formatOTP(detail.latest_otp) : 'N/A';
  document.getElementById('otp-selected-yoy').textContent = detail ? formatPp(detail.yoy_pp) : 'N/A';
  document.getElementById('otp-latest-label').textContent = detail ? detail.latest_period + ' CUSTOMER OTP' : 'LATEST CUSTOMER OTP';
  document.getElementById('otp-selection-note').textContent = noteText || 'No unambiguous one-to-one OTP match for the ridership service. Select an OTP subservice independently; its series must not be interpreted as the ridership route overall.';
  drawOTP(document.getElementById('rail-otp-trend'), detail);
}

function renderSelectedRoute(route) {
  drawRidership(document.getElementById('rail-ridership-trend'), route.series);
  document.getElementById('selected-route-name').textContent = route.name;
  document.getElementById('selected-route-code').textContent = (route.is_group ? 'SERVICE GROUP AGGREGATE' : 'FRA code ' + route.apt_code);
  document.getElementById('selected-route-latest').textContent = formatCount(route.latest_ridership);
  document.getElementById('selected-route-yoy').textContent = formatYoY(route.yoy_pct);
  const detailLink = document.getElementById('selected-detail-link');
  detailLink.hidden = !!route.is_group;
  if (!route.is_group) detailLink.href = '/projects/intercity-rail/routes/' + encodeURIComponent(route.slug);
  const notes = [];
  if (route.other_names_same_code.length) notes.push('FRA also used this code for ' + route.other_names_same_code.join(', ') + '; histories are kept separate.');
  if (route.issues.length) notes.push(...route.issues);
  document.getElementById('selected-route-note').textContent = notes.join(' ');
  const otpSelect = document.getElementById('otp-route-select');
  if (otpSelect) {
    otpSelect.value = route.otp ? route.otp.slug : '';
    renderOTP(route.otp, route.otp ? 'Matched exactly to the selected ridership service. No aggregation across OTP subservices.' : null);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.site-nav');
  if (toggle && nav) toggle.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  const hero = document.getElementById('hero-ridership');
  if (hero) drawRidership(hero, JSON.parse(hero.dataset.series), true);
  const routeChart = document.getElementById('route-ridership-trend');
  if (routeChart) drawRidership(routeChart, JSON.parse(routeChart.dataset.route).series);
  const detailOTP = document.getElementById('route-otp-trend');
  if (detailOTP) drawOTP(detailOTP, JSON.parse(detailOTP.dataset.otp));
  const selected = document.getElementById('rail-ridership-trend');
  if (selected) drawRidership(selected, JSON.parse(selected.dataset.route).series);
  const selectedOTP = document.getElementById('rail-otp-trend');
  if (selectedOTP) drawOTP(selectedOTP, JSON.parse(selectedOTP.dataset.otp));

  const routeSelect = document.getElementById('ridership-route-select');
  if (routeSelect) {
    routeSelect.addEventListener('change', async () => {
      const group = document.getElementById('ridership-category')?.value || 'all';
      const slug = routeSelect.value || (group !== 'all' ? 'group:' + group : '');
      if (!slug) return;
      const note = document.getElementById('selected-route-note');
      routeSelect.disabled = true;
      try {
        const response = await fetch('/api/rail/routes/' + encodeURIComponent(slug));
        if (!response.ok) throw new Error('HTTP ' + response.status);
        if (routeSelect.value === slug) renderSelectedRoute(await response.json());
      } catch (error) {
        if (note) note.textContent = 'Could not load this service. Please try again.';
      } finally { routeSelect.disabled = false; }
    });
  }

  const otpSelect = document.getElementById('otp-route-select');
  if (otpSelect) {
    otpSelect.addEventListener('change', async () => {
      const slug = otpSelect.value;
      if (!slug) { renderOTP(null); return; }
      otpSelect.disabled = true;
      try {
        const response = await fetch('/api/rail/otp/routes/' + encodeURIComponent(slug));
        if (!response.ok) throw new Error('HTTP ' + response.status);
        if (otpSelect.value === slug) {
          const detail = await response.json();
          const ridershipLabel = document.getElementById('selected-route-name')?.textContent || '';
          const sameName = detail.service.trim().toLowerCase() === ridershipLabel.trim().toLowerCase() && detail.sub_service.trim().toLowerCase() === ridershipLabel.trim().toLowerCase();
          renderOTP(detail, sameName ? 'Matched exactly to selected ridership service.' : 'Independent FRA OTP service/subservice selection; this series is not necessarily equivalent to the selected ridership route.');
        }
      } catch (error) {
        document.getElementById('otp-selection-note').textContent = 'Could not load the OTP series. Please try again.';
      } finally { otpSelect.disabled = false; }
    });
  }

  const search = document.getElementById('route-search');
  if (search) search.addEventListener('input', () => {
    const query = search.value.trim().toLowerCase();
    let shown = 0;
    document.querySelectorAll('.route-table tbody tr').forEach(tr => {
      tr.hidden = !tr.dataset.routeName.includes(query) || (document.getElementById("route-table-category")?.value !== "all" && tr.dataset.category !== document.getElementById("route-table-category")?.value);
      if (!tr.hidden) shown += 1;
    });
    document.getElementById('shown-route-count').textContent = shown.toString();
  });
});
