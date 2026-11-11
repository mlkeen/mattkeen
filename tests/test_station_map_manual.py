import csv,json,tempfile,sys
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
script=Path(__file__).resolve().parents[1] / 'scripts/publish_station_map.py'
spec=spec_from_file_location('pub',script);pub=module_from_spec(spec);spec.loader.exec_module(pub)
with tempfile.TemporaryDirectory() as td:
 d=Path(td)
 coords=d/'coords.csv';coords.write_text('station_code,lat,lon,station_name\nBOS,42.35,-71.05,Boston\nPOR,43.65,-70.25,Portland\n')
 file=d/'station_performance.csv'; field=['fiscal_year','fiscal_quarter','service_line','service','sub_service','station_code','station_name','detraining_customers','late_detraining_customers','avg_minutes_late_late_customers']
 data=[['2026','3','State Supported','Downeaster','Downeaster','BOS','Boston','100','10','20'],['2026','3','State Supported','Downeaster','Downeaster','BOS','Boston','200','100','40'],['2026','2','State Supported','Downeaster','Downeaster','BOS','Boston','50','25','60'],['2026','3','State Supported','Downeaster','Downeaster','POR','Portland','50','10','--'],['2026','3','State Supported','Downeaster','Downeaster','XXX','Nowhere','50','10','30'],['2026','3','State Supported','Downeaster','Downeaster','BOS','Boston','10','15','30']]
 with file.open('w',newline='') as f:
  w=csv.writer(f);w.writerow(field);w.writerows(data)
 report=pub.publish(source=file,dest=d/'published.json',report=d/'report.json',coordinates=coords,download=False)
 assert report['invalid_rows']==1 and report['unmapped_codes']==['XXX'],report
 j=json.loads((d/'published.json').read_text());assert len(j['rows'])==3,len(j['rows']);assert len(j['services'])==1
 bos=[r for r in j['rows'] if r['station_code']=='BOS' and r['period']=='2026 Q3'][0]
 assert bos['detraining']==300 and bos['late']==110 and abs(bos['avg_minutes_late']-(4200/110))<.01,bos
 # service dynamically points to production published fixture through override
 spec2=spec_from_file_location('station_service',Path(__file__).resolve().parents[1] / 'app/station_service.py');station_service=module_from_spec(spec2);spec2.loader.exec_module(station_service)
 station_service.PATH=d/'published.json';station_service._load.cache_clear()
 q3=station_service.detail('Downeaster | Downeaster','2026 Q3',1)
 assert q3['shown_station_count']==2 and q3['detraining_passengers']==350,q3
 allq=station_service.detail('Downeaster | Downeaster','all',1)
 assert allq['detraining_passengers']==400 and allq['late_passengers']==145,allq
 print('PASS: publisher, aggregation, invalid counts, mapping QA, quarter filtering, passenger weighting')
