"""Publish FRA station performance for the Station Performance Map.

Reads the existing normalized ETL output; matches station codes to the
DOT/BTS NTAD Amtrak Stations ArcGIS dataset. No place-name geocoding.
Usage: python scripts/publish_station_map.py
Options: --coordinates path/to/station_coordinates.csv ; --no-download
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/processed/station_performance.csv'
DEST = ROOT / 'app/data/fra_station_map.json'
REPORT = ROOT / 'data/reports/station_map_report.json'
CACHE = ROOT / 'data/raw/fra/amtrak_station_coordinates.geojson'
SERVICE_URL = 'https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/NTAD_Amtrak_Stations/FeatureServer/0/query'
REQUIRED = {'fiscal_year','fiscal_quarter','service','sub_service','station_code',
            'detraining_customers','late_detraining_customers'}

def numeric(s):
    try:
        x = float(str(s).strip().replace(',',''))
        return x if x == x and abs(x) != float('inf') else None
    except (TypeError, ValueError):
        return None

def code(s): return str(s or '').strip().upper()

def get_geojson(cache=CACHE, download=True):
    if cache.is_file():
        return json.loads(cache.read_text(encoding='utf-8'))
    if not download:
        raise FileNotFoundError(f'Coordinates file missing: {cache}. Remove --no-download or supply --coordinates.')
    # BTS currently publishes fewer than 2000 station points; page in batches
    # and explicitly request a WGS84 latitude/longitude response.
    features=[]; offset=0
    while True:
        args={'where':'1=1','outFields':'OBJECTID,Code,StationName,lon,lat',
              'outSR':'4326','f':'geojson','resultOffset':str(offset),'resultRecordCount':'500'}
        with urlopen(SERVICE_URL+'?'+urlencode(args),timeout=40) as response:
            data=json.load(response)
        if 'error' in data or data.get('type') != 'FeatureCollection':
            raise RuntimeError(f'Unexpected BTS station response: {str(data)[:250]}')
        batch=data.get('features',[])
        features.extend(batch)
        if len(batch)<500:break
        offset+=len(batch)
        if offset>10000:raise RuntimeError('Unusually large BTS station dataset: refusing endless pagination')
    cache.parent.mkdir(parents=True,exist_ok=True)
    obj={'type':'FeatureCollection','features':features}
    cache.write_text(json.dumps(obj),encoding='utf-8')
    return obj

def read_coordinates(path=None, download=True):
    """Return code lookup and ambiguous codes. Accept CSV override or BTS GeoJSON."""
    if path and Path(path).suffix.lower()=='.csv':
        with Path(path).open(newline='',encoding='utf-8-sig') as f:items=list(csv.DictReader(f))
        candidates=[(code(r.get('station_code') or r.get('Code')),numeric(r.get('lat') or r.get('latitude')),numeric(r.get('lon') or r.get('longitude')),
                      r.get('station_name') or r.get('name') or '') for r in items]
    else:
        geo=get_geojson(Path(path) if path else CACHE,download=download)
        candidates=[]
        for feature in geo.get('features',[]):
            p=feature.get('properties') or {}
            xy=(feature.get('geometry') or {}).get('coordinates') or [None,None]
            candidates.append((code(p.get('Code') or p.get('code')),numeric(p.get('lat')) or numeric(xy[1]),
                               numeric(p.get('lon')) or numeric(xy[0]),p.get('StationName') or p.get('Name') or ''))
    values={}; conflicts=set()
    for k,lat,lon,name in candidates:
        if not k or lat is None or lon is None or not (-90<=lat<=90 and -180<=lon<=180):continue
        if k in values and (abs(values[k]['lat']-lat)>0.001 or abs(values[k]['lon']-lon)>0.001):
            conflicts.add(k)
        else:values[k]={'lat':lat,'lon':lon,'reference_name':str(name)}
    for k in conflicts:values.pop(k,None)
    return values, sorted(conflicts)

def publish(source=SOURCE,dest=DEST,report=REPORT,coordinates=None,download=True):
    lookup,conflicts=read_coordinates(coordinates,download=download)
    grouped={};services={};periods=set();codes=set();bad=0;raw_rows=0;missing_metric=0
    with Path(source).open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        missing=REQUIRED-set(reader.fieldnames or [])
        if missing:raise ValueError(f'CSV missing required columns: {sorted(missing)}')
        for r in reader:
            raw_rows+=1
            year=numeric(r.get('fiscal_year'));q=numeric(r.get('fiscal_quarter'))
            station=code(r.get('station_code'))
            service=(r.get('service') or '').strip();sub=(r.get('sub_service') or '').strip() or service
            total=numeric(r.get('detraining_customers'));late=numeric(r.get('late_detraining_customers'))
            if (year is None or q is None or int(q) not in (1,2,3,4) or not station or not service
                or total is None or late is None or total<0 or late<0 or late>total):
                bad+=1;continue
            period=f'{int(year)} Q{int(q)}';periods.add(period);codes.add(station)
            service_id=service+' | '+sub
            services[service_id]={'id':service_id,'service':service,'sub_service':sub,
                                  'label':service if service==sub else f'{service} / {sub}',
                                  'service_line':(r.get('service_line') or '').strip()}
            key=(period,service_id,station)
            item=grouped.setdefault(key,{'period':period,'service_id':service_id,'station_code':station,
                                          'station_name':(r.get('station_name') or '').strip(),
                                          'detraining':0,'late':0,'late_minutes_weighted_sum':0,
                                          'late_minutes_weight':0,'source_rows':0})
            item['detraining']+=int(total);item['late']+=int(late);item['source_rows']+=1
            avg=numeric(r.get('avg_minutes_late_late_customers'))
            if avg is not None and avg>=0 and late>0:
                item['late_minutes_weighted_sum']+=avg*late
                item['late_minutes_weight']+=int(late)
            elif late>0:missing_metric+=1
    rows=[];unmapped=set()
    for item in grouped.values():
        ref=lookup.get(item['station_code'])
        if not ref:
            unmapped.add(item['station_code']);continue
        n=item.pop('late_minutes_weight')
        total_minutes=item.pop('late_minutes_weighted_sum')
        item['avg_minutes_late']=round(total_minutes/n,2) if n else None
        item['avg_minutes_coverage_late_passengers']=n
        item['lat']=ref['lat'];item['lon']=ref['lon'];rows.append(item)
    rows.sort(key=lambda r:(r['period'],r['service_id'],r['station_code']))
    for item in services.values():
        if item['service_line'].lower()=='long distance':item['category']='long_distance'
        elif item['service_line'].lower() in {'state supported','state-supported'}:item['category']='state_supported'
        elif 'acela' in item['service'].lower():item['category']='acela'
        elif 'northeast corridor' in item['service_line'].lower() or 'nec' == item['service_line'].lower():item['category']='nec_other'
        else:item['category']='special'
    payload={'schema_version':1,'source':'FRA Station Performance; USDOT/BTS NTAD Amtrak Stations 2026',
             'periods':sorted(periods),'services':sorted(services.values(),key=lambda x:x['label']),
             'rows':rows,'unmapped_station_codes':sorted(unmapped)}
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(payload,separators=(',',':'),ensure_ascii=False),encoding='utf-8')
    report_data={'source_rows':raw_rows,'valid_aggregated_rows':len(grouped),'mapped_aggregated_rows':len(rows),
                 'invalid_rows':bad,'unmapped_codes':sorted(unmapped),'unmapped_codes_count':len(unmapped),
                 'conflicting_location_codes':conflicts,'missing_avg_minutes_rows_with_late_passengers':missing_metric,
                 'unique_station_codes':len(codes),'coordinate_lookup_count':len(lookup)}
    report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(report_data,indent=2),encoding='utf-8')
    return report_data

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coordinates',help='Optional local BTS GeoJSON or CSV with station_code,lat,lon')
    parser.add_argument('--no-download',action='store_true',help='Only use locally cached coordinates')
    args=parser.parse_args()
    try:
        result=publish(coordinates=args.coordinates,download=not args.no_download)
    except Exception as exc:
        print(f'Failed: {exc}',file=sys.stderr);sys.exit(1)
    print(json.dumps(result,indent=2))
    print(f'Published to {DEST}; QA report: {REPORT}')
