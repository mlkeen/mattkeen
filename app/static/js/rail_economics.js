(() => {
  const root=document.getElementById('economics-lab');if(!root)return;
  const overview=JSON.parse(root.dataset.overview);
  const service=document.getElementById('econ-service');if(!service)return;
  const measure=document.getElementById('econ-measure'),payments=document.getElementById('econ-payments'),quarter=document.getElementById('econ-quarter');
  const title=document.getElementById('econ-title'),values=document.getElementById('econ-values'),quality=document.getElementById('econ-quality'),message=document.getElementById('econ-message');
  let data=null,seq=0;
  const num=v=>v===null||v===undefined?'Not reported':Number(v).toLocaleString('en-US',{maximumFractionDigits:2});
  const pct=v=>v===null||v===undefined?'Not available':(100*v).toLocaleString('en-US',{maximumFractionDigits:1})+'%';
  const labels={cost_recovery:'Operating cost recovery',avoidable_expense:'Avoidable expense coverage',fully_allocated_expense:'Fully allocated expense coverage'};
  const reasons={valid:'Valid',zero_expense:'Expense denominator is zero',negative_expense:'Expense denominator is negative',negative_revenue:'Negative revenue adjustment',missing_components:'Missing revenue or expense',incomplete_group:'One or more source routes has an invalid or missing financial component',missing_ratio:'Reported ratio is missing',ratio_mismatch:'Reported ratio differs from calculated ratio'};
  const dataRows=()=>data.observations.filter(r=>r.measure===measure.value&&(measure.value==='cost_recovery'||String(r.state_payments_included)===payments.value));
  function render(){
    if(!data)return;
    payments.disabled=measure.value==='cost_recovery';
    const rows=dataRows(),byPeriod=new Map(rows.map(r=>[r.period,r]));
    const x=data.periods,y=x.map(p=>{const r=byPeriod.get(p);return r&&r.status==='valid'?100*r.ratio:null;});
    title.textContent=`${labels[measure.value]} — ${data.label}`;
    const el=document.getElementById('econ-chart');
    if(window.Plotly){Plotly.react(el,[{type:'scatter',mode:'lines+markers',name:'Expense coverage',x,y,connectgaps:false,line:{color:'#315d6b',width:3},marker:{size:7},hovertemplate:'%{x}: %{y:.1f}%<extra></extra>'}],{paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{family:'IBM Plex Sans, sans-serif',size:12,color:'#20201e'},showlegend:false,margin:{t:20,l:70,r:30,b:70},xaxis:{tickangle:-45,gridcolor:'#dedbd3'},yaxis:{title:'REVENUE / EXPENSE (%)',gridcolor:'#dedbd3',rangemode:'tozero'},shapes:[{type:'line',xref:'paper',x0:0,x1:1,yref:'y',y0:100,y1:100,line:{color:'#ad653f',dash:'dot',width:1.5}}]},{displayModeBar:false,responsive:true});}
    else el.textContent='Chart library unavailable; check your connection.';
    const p=quarter.value==='latest'?x[x.length-1]:quarter.value;
    const r=byPeriod.get(p);
    values.replaceChildren();quality.replaceChildren();
    function item(parent,a,b){const p=document.createElement('p');const strong=document.createElement('strong');strong.textContent=a+': ';p.append(strong,document.createTextNode(b));parent.append(p);}
    if(!r){item(values,'Quarter',p);item(values,'Status','Not reported for this measure and reporting unit');item(quality,'Status','No source record');}
    else{
      item(values,'Quarter',p);
      item(values,'Revenue',num(r.numerator));item(values,'Expense',num(r.denominator));
      item(values,'Reported ratio',pct(r.ratio_source));item(values,'Charted ratio',pct(r.ratio));
      item(quality,'Status',reasons[r.status]||r.status);
      item(quality,'Workbook',r.source_workbook||'Unknown');item(quality,'Worksheet',r.source_sheet||'Unknown');item(quality,'Excel row',r.source_excel_row||'Unknown');
    }
    const flagged=rows.filter(r=>r.status!=='valid');
    message.textContent=`${rows.filter(r=>r.status==='valid').length} chartable quarterly observations; ${flagged.length} flagged (shown as gaps). Route ratios are preserved; group ratios are calculated from component totals and require complete valid observations.`;
  }
  async function fetchData(){const current=++seq;message.textContent='Loading financial observations…';try{const response=await fetch('/api/rail/economics/detail?service='+encodeURIComponent(service.value || (document.getElementById('econ-category')?.value !== 'all' ? 'group:'+document.getElementById('econ-category').value : 'system')));if(!response.ok)throw new Error('HTTP '+response.status);const result=await response.json();if(current===seq){data=result;render();}}catch(error){if(current===seq){data=null;message.textContent='Unable to load financial observations: '+error.message;}}}
  service.addEventListener('change',fetchData);
  [measure,payments,quarter].forEach(e=>e.addEventListener('change',render));
  fetchData();
})();
