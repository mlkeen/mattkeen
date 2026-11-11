/* Shared FRA category filters: blank route means group aggregate on supported pages. */
(() => {
  function update(filter) {
    const target=document.getElementById(filter.dataset.target) || document.querySelector(filter.dataset.target);
    if(!target)return;
    const group=filter.value;
    const textFilter=filter.dataset.search?document.getElementById(filter.dataset.search):null;
    const q=(textFilter?.value||'').trim().toLowerCase();
    const mode=filter.dataset.mode;
    const items=mode==='checklist'?[...target.querySelectorAll('.compare-choice')]:
      mode==='table'?[...document.querySelectorAll(filter.dataset.target)]:[...target.options];
    let shown=0;
    for(const item of items){
      const matchesGroup=group==='all'||item.dataset.category===group;
      const matchesText=!q||(mode==='checklist'?(item.dataset.search||''):mode==='table'?(item.dataset.routeName||''):item.textContent.toLowerCase()).includes(q);
      const visible=matchesGroup&&matchesText;
      if(mode==='table'||mode==='checklist')item.hidden=!visible;
      else if(item.value)item.hidden=!visible;
      if(visible)shown++;
    }
    if(filter.id==='reliability-category'){
      const highlight=document.getElementById('reliability-highlight');
      if(highlight){
        [...highlight.options].forEach(o=>{if(o.value!=='all')o.hidden=group!=='all'&&o.dataset.category!==group;});
        if(highlight.selectedOptions[0]?.hidden){highlight.value='all';highlight.dispatchEvent(new Event('change'));}
      }
    }
    if(mode==='table'){
      const count=document.getElementById('shown-route-count');if(count)count.textContent=String(shown);
    }
    if(mode==='options'){
      // Do not switch reporting units on typing a search query; switch on explicit group change only.
      if(filter.dataset.switchSelection==='yes'){
        if(['ridership-category','delay-category','econ-category'].includes(filter.id) && group!=='all') {
          target.value=''; target.dispatchEvent(new Event('change',{bubbles:true}));
          filter.dataset.switchSelection='no'; return;
        }
        if(['ridership-category','delay-category','econ-category'].includes(filter.id) && group==='all' && !target.value) {
          const preferred=[...target.options].find(o=>o.value && (filter.id==='econ-category'?o.value==='system':/downeaster/i.test(o.textContent)));
          const first=preferred||[...target.options].find(o=>o.value&&!o.hidden);
          if(first){target.value=first.value;target.dispatchEvent(new Event('change',{bubbles:true}));}
          filter.dataset.switchSelection='no';return;
        }
        const current=target.selectedOptions[0];
        if(current&&current.value&&current.hidden){
          const first=[...target.options].find(o=>o.value&&!o.hidden);
          if(first){target.value=first.value;target.dispatchEvent(new Event('change',{bubbles:true}));}
        }
      }
    }
    filter.dataset.switchSelection='no';
  }
  document.addEventListener('DOMContentLoaded',()=>{
    document.querySelectorAll('.service-category-filter').forEach(filter=>{
      const text=filter.dataset.search&&document.getElementById(filter.dataset.search);
      filter.addEventListener('change',()=>{filter.dataset.switchSelection='yes';update(filter);});
      if(text)text.addEventListener('input',()=>update(filter));
      update(filter);
    });
  });
})();
