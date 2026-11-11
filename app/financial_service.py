"""Read pre-published FRA financial observations; excludes flagged ratios from charts."""
import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from .service_categories import category_for_apt, CATEGORY_LABELS

DATA=Path(__file__).resolve().parent/'data/fra_financials.json'

@lru_cache(maxsize=1)
def _load():
    if not DATA.is_file():return {'available':False,'periods':[],'services':[],'records':[],'source':None,'status_counts':{}}
    raw=json.loads(DATA.read_text(encoding='utf-8'))
    if raw.get('version')!=1:raise ValueError('Unsupported financial publication version')
    groups={}
    for r in raw['records']:
        if r['level']=='route':groups[(r['apt_code'],r['route'])]=None
    catalog=[]
    for code,name in sorted(groups,key=lambda k:(k[1].casefold(),k[0])):
        catalog.append({'id':code+'|'+name,'code':code,'name':name,'category':category_for_apt(code,name)})
    return {'available':True,'periods':raw['periods'],'services':catalog,'records':raw['records'],
        'source':raw['source'],'status_counts':raw['status_counts']}

def overview():
    d=_load();return {key:d[key] for key in ('available','periods','services','source','status_counts')}

def detail(identifier):
    d=_load()
    if not d['available']:return None
    group = identifier.removeprefix('group:') if identifier.startswith('group:') else None
    if group is not None:
        if group not in CATEGORY_LABELS:return None
        matched = [r for r in d['records'] if r['level']=='route' and category_for_apt(r['apt_code'],r['route'])==group]
        if not matched:return None
        buckets=defaultdict(list)
        for r in matched:
            buckets[(r['period'],r['measure'],str(r['state_payments_included']))].append(r)
        rows=[]
        for (period,measure,payments),components in sorted(buckets.items()):
            good=all(r['status']=='valid' and r['numerator'] is not None and r['denominator'] is not None and r['denominator']>0 and r['numerator']>=0 for r in components)
            numerator=sum(r['numerator'] for r in components) if good else None
            denominator=sum(r['denominator'] for r in components) if good else None
            ratio=numerator/denominator if good and denominator else None
            rows.append({'period':period,'measure':measure,'state_payments_included':components[0]['state_payments_included'],
                         'numerator':numerator,'denominator':denominator,'ratio':ratio,'ratio_source':None,
                         'status':'valid' if good else 'incomplete_group','source_workbook':'Multiple FRA workbooks',
                         'source_sheet':'Multiple source rows','source_excel_row':None,
                         'reporting_units':len(components)})
        return {'id':identifier,'label':CATEGORY_LABELS[group]+' — all routes',
                'periods':d['periods'],'observations':rows,
                'notes':'Group ratios are sum of eligible component revenues divided by sum of corresponding expenses; NOT an average of percentages. Any flagged component produces a gap for that quarter and measure. Financial routes only; no system totals.'}
    if identifier=='system':
        rows=[r for r in d['records'] if r['apt_code']=='APT_All_APT' and r['level']=='aggregate']
        label='Amtrak system total'
    else:
        matching=[s for s in d['services'] if s['id']==identifier]
        if not matching:return None
        svc=matching[0];rows=[r for r in d['records'] if r['level']=='route' and r['apt_code']==svc['code'] and r['route']==svc['name']]
        label=svc['name']
    return {'id':identifier,'label':label,'periods':d['periods'],'observations':rows,
        'notes':'Ratios represent revenue / expense; 100% is 1.0. Financial rows with nonpositive expense, negative revenue or arithmetic mismatch are flagged and not plotted. State-payment treatments remain distinct.'}
