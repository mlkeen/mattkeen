(()=>{
'use strict';
const form=document.getElementById('bca-form');if(!form)return;
const defaults=JSON.parse(document.getElementById('bca-defaults').textContent);
const el=id=>document.getElementById(id);
const money=n=>!Number.isFinite(n)?'—':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n);
const compact=n=>!Number.isFinite(n)?'—':new Intl.NumberFormat('en-US',{notation:'compact',maximumFractionDigits:2}).format(n);
const ratio=n=>n==null||!Number.isFinite(n)?'N/A':n.toFixed(2);
let latest=null;
function inputs(){const result={};new FormData(form).forEach((v,k)=>{result[k]=k==='name'?v:Number(v);});return result;}
function save(name,content,mime){const blob=new Blob([content],{type:mime});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function render(a){latest=a;el('bca-project-name').textContent=a.inputs.name||'Untitled transit project';el('bca-npv').textContent=money(a.npv);el('bca-bcr').textContent=ratio(a.bcr);el('bca-pvb').textContent=money(a.pv_benefits);el('bca-pvc').textContent=money(a.pv_costs);el('bca-window').textContent=`Base year ${a.inputs.base_year} · ${a.inputs.construction_years} years construction · ${a.inputs.operating_years} operating years · ${a.inputs.discount_rate}% real discount rate`;
 const keys=[['existing_time','Existing riders: time'],['new_time','New riders: time (half-rule)'],['avoided_auto','Avoided driving resource costs'],['safety','Safety'],['air_quality','Air quality'],['other','Other'],['residual','Residual value']];
 const max=Math.max(1,...Object.values(a.pv_categories));const breakdown=el('bca-breakdown');breakdown.replaceChildren();keys.forEach(([key,title])=>{const v=a.pv_categories[key];const line=document.createElement('div');line.className='bca-barline';const label=document.createElement('span');label.textContent=title;const track=document.createElement('div');track.className='bca-track';const fill=document.createElement('div');fill.className='bca-fill';fill.style.width=(100*v/max)+'%';track.appendChild(fill);const value=document.createElement('strong');value.textContent=compact(v);line.append(label,track,value);breakdown.appendChild(line);});
 const ss=el('bca-scenarios');ss.replaceChildren();a.scenarios.forEach(s=>{const tr=document.createElement('tr');[s.label,money(s.npv),ratio(s.bcr)].forEach(x=>{const td=document.createElement('td');td.textContent=x;tr.appendChild(td);});ss.appendChild(tr);});
 const yy=el('bca-years');yy.replaceChildren();a.years.forEach(r=>{const tr=document.createElement('tr');[r.year,r.phase,money(r.benefits),money(r.costs),money(r.net),money(r.pv_net)].forEach(x=>{const td=document.createElement('td');td.textContent=x;tr.appendChild(td);});yy.appendChild(tr);});
 const assumptions=el('bca-assumptions');assumptions.replaceChildren();a.assumptions.forEach(v=>{const li=document.createElement('li');li.textContent=v;assumptions.appendChild(li);});
 if(typeof Plotly!=='undefined'){Plotly.react('bca-annual-chart',[{x:a.years.map(r=>r.year),y:a.years.map(r=>r.benefits),name:'Benefits',type:'bar',marker:{color:'#376b6d'}},{x:a.years.map(r=>r.year),y:a.years.map(r=>r.costs),name:'Costs',type:'bar',marker:{color:'#bb8d54'}}],{barmode:'group',margin:{t:12,r:12,l:55,b:42},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',legend:{orientation:'h',y:1.17},xaxis:{title:'Year',type:'category',tickangle:-45,nticks:10},yaxis:{title:'Real dollars',tickformat:'~s'},font:{family:'IBM Plex Sans, Arial'}},{responsive:true,displayModeBar:false});}else{el('bca-annual-chart').textContent='Chart library not available. Annual data are shown in the table below.';}
}
async function calculate(){const error=el('bca-error');error.hidden=true;try{const response=await fetch('/api/transit-bca/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(inputs())});const a=await response.json();if(!response.ok)throw new Error(a.error||'Unable to calculate');render(a);}catch(err){error.textContent=String(err.message||err);error.hidden=false;}}
form.addEventListener('submit',e=>{e.preventDefault();calculate();});
form.addEventListener('change',()=>calculate());
el('bca-reset').addEventListener('click',()=>{for(const [k,v] of Object.entries(defaults)){const input=form.elements.namedItem(k);if(input)input.value=v;}calculate();});
el('bca-json').addEventListener('click',()=>{if(latest)save('transit_bca_assumptions.json',JSON.stringify({inputs:latest.inputs,methodology:latest.assumptions},null,2),'application/json');});
el('bca-csv').addEventListener('click',()=>{if(!latest)return;const rows=latest.years;const columns=Object.keys(rows[0]);const content=[columns.join(','),...rows.map(r=>columns.map(k=>JSON.stringify(r[k]??'')).join(','))].join('\r\n');save('transit_bca_annual_results.csv',content,'text/csv');});
calculate();
})();
