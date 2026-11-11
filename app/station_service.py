"""Serve published FRA station map observations, never fabricate missing data."""
from functools import lru_cache
import json
from pathlib import Path
from .service_categories import CATEGORY_LABELS

PATH=Path(__file__).resolve().parent/'data/fra_station_map.json'

@lru_cache(maxsize=1)
def _load():
    if not PATH.is_file():return None
    return json.loads(PATH.read_text(encoding='utf-8'))

def overview():
    data=_load()
    if not data:return {'available':False,'periods':[],'services':[],'unmapped_count':0}
    return {'available':True,'periods':data['periods'],'services':data['services'],
            'unmapped_count':len(data.get('unmapped_station_codes',[])),
            'mapped_rows':len(data['rows'])}

def detail(service_id,period='all',min_customers=1):
    data=_load()
    if not data:return None
    valid={x['id'] for x in data['services']}
    group = service_id.removeprefix('group:') if service_id.startswith('group:') else None
    if group is not None and group not in CATEGORY_LABELS:return None
    if group is None and service_id not in valid:return None
    allowed = {s['id'] for s in data['services'] if s.get('category') == group} if group else {service_id}
    if not allowed:return None
    if period!='all' and period not in data['periods']:raise ValueError('Unknown fiscal quarter')
    if min_customers<0 or min_customers>10000000:raise ValueError('Invalid minimum passengers')
    # Treat 'all' as a weighted accumulation across quarters; do not average
    # reported station percentages or average minutes without denominators.
    merged={}
    for x in data['rows']:
        if x['service_id'] not in allowed or (period!='all' and x['period']!=period):continue
        k=x['station_code']
        t=merged.setdefault(k,{'station_code':k,'station_name':x['station_name'],
                               'lat':x['lat'],'lon':x['lon'],'detraining':0,'late':0,
                               '_minutes_sum':0,'_minutes_weight':0,'source_rows':0})
        t['detraining']+=x['detraining'];t['late']+=x['late'];t['source_rows']+=x['source_rows']
        if x['avg_minutes_late'] is not None and x['avg_minutes_coverage_late_passengers']:
            n=x['avg_minutes_coverage_late_passengers'];t['_minutes_sum']+=x['avg_minutes_late']*n;t['_minutes_weight']+=n
    result=[]
    for x in merged.values():
        if x['detraining']<min_customers:continue
        n=x.pop('_minutes_weight');v=x.pop('_minutes_sum')
        x['late_pct']=round(100*x['late']/x['detraining'],2) if x['detraining'] else None
        x['avg_minutes_late']=round(v/n,1) if n else None
        x['avg_minutes_coverage_late_passengers']=n
        result.append(x)
    result.sort(key=lambda x:(-(x['detraining']),x['station_name']))
    return {'service_id':service_id,'period':period,'stations':result,'mapped_station_count':len(merged),
            'shown_station_count':len(result),'late_passengers':sum(r['late'] for r in result),
            'detraining_passengers':sum(r['detraining'] for r in result),
            'note':'Group station counts sum included service/subservice reporting units. Interpret as totals only where operational units do not overlap.' if group else None}
