"""Calibrate ONE overall demand multiplier using real FY2025 Amtrak route totals.

Explicitly DOES NOT calibrate OD shares, choice elasticities, station access or
alignment. Corridor county lists are hand-selected representative stops, not an
official GTFS stop inventory; use results for screening, not investment decisions.

Usage: python scripts/calibrate_rail_forecast.py [--check-only]
Requires a Census-published county catalog and the included FRA-derived FY25
route totals file. No internet access necessary.
"""
from __future__ import annotations
import argparse,csv,json,math,statistics,sys,importlib.util,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("rail_engine", ROOT/"app/rail_forecast_engine.py")
engine=importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
counties,forecast=engine.counties,engine.forecast

ROUTES={
 'Downeaster':['25025','25009','23031','23005'],
 'Hiawatha':['17031','55079'],
 'Lincoln Service':['17031','17167','29510'],
 'Piedmont':['37183','37081','37119'],
 'Wolverine':['17031','26077','26161','26163'],
 'Pacific Surfliner':['06073','06059','06037','06111','06083','06079'],
 'Capitol Corridor':['06067','06013','06001','06085'],
 'Cascades':['53033','53053','53067','53011','41051','41039'],
 'Keystone':['36061','42101','42071','42043'],
 'Heartland Flyer':['40109','40027','40019','48439'],
 'Missouri River Runner':['29095','29051','29019','29510'],
 'Blue Water':['17031','26077','26065','26049','26147'],
 'San Joaquin':['06067','06077','06099','06019','06029'],
 'Borealis':['17031','55079','55025','27123'],
}
# Representative route segments only; does not model every station or overlapping services.
OBS=ROOT/'data/raw/fra/fy2025_amtrak_route_ridership.csv'
OUT=ROOT/'app/data/rail_forecast_calibration.json'

def calibrate(catalog, observations, route_map=ROUTES):
    if len(catalog)<3000 or any('SYNTHETIC' in str(c.get('source','')).upper() for c in catalog):
        raise ValueError('Publish the real nationwide county catalog first (at least 3,000 counties).')
    available={c['fips'] for c in catalog}
    samples=[]; skipped=[]
    for route,stops in route_map.items():
        missing=set(stops)-available
        if missing or route not in observations or observations[route]<=0:
            skipped.append({'route':route,'missing_fips':sorted(missing),'missing_observation':route not in observations});continue
        # Baseline model using uncalibrated defaults. No fitted access, speed, or frequency inputs.
        pred=forecast({'stops':stops},catalog,calibration=None)['annual_ridership']
        if pred<=0:continue
        actual=observations[route]
        samples.append({'route':route,'observed':actual,'baseline':pred,'ratio':actual/pred,'stops':stops})
    if len(samples)<8:raise ValueError(f'Only {len(samples)} eligible reference corridors; need 8 or more.')
    # Geometric mean minimizes squared logarithmic error; no imaginary precision.
    lrat=[math.log(s['ratio']) for s in samples]
    factor=math.exp(statistics.mean(lrat))
    for i,s in enumerate(samples):
        loo=math.exp((sum(lrat)-lrat[i])/(len(lrat)-1))
        s['leave_one_out_prediction']=round(s['baseline']*loo)
        s['leave_one_out_ratio']=round(s['observed']/s['leave_one_out_prediction'],3) if s['leave_one_out_prediction'] else None
        s['full_fit_prediction']=round(s['baseline']*factor)
        s['absolute_percentage_error_loo']=round(abs(s['baseline']*loo/s['observed']-1)*100,1)
    # Multiplicative residual interval is empirical, NOT a formal prediction interval.
    errs=sorted(math.log(s['observed']/(s['baseline']*math.exp((sum(lrat)-math.log(s['ratio']))/(len(lrat)-1)))) for s in samples)
    def quantile(a,q):
        h=(len(a)-1)*q;lo=int(h);hi=min(lo+1,len(a)-1)
        return a[lo]*(1-(h-lo))+a[hi]*(h-lo)
    result={'schema_version':1,'status':'amtrak_route_total_calibrated','fiscal_year':2025,
      'method':'Geometric-mean scaling of route totals; leave-one-corridor-out validation',
      'demand_multiplier':round(factor,7),'reference_routes':len(samples),
      'county_catalog_sha256':hashlib.sha256(engine.DATA_PATH.read_bytes()).hexdigest(),
      'nhts_input_sha256':(engine.published_nhts_profile() or {}).get('input_sha256'),
      'nhts_annualized_long_distance_trips_per_person':(engine.published_nhts_profile() or {}).get('annualized_long_distance_trips_per_person'),
      'median_absolute_percentage_error_loo':round(statistics.median(s['absolute_percentage_error_loo'] for s in samples),1),
      'multiplicative_error_10_90_loo':[round(math.exp(quantile(errs,.1)),3),round(math.exp(quantile(errs,.9)),3)],
      'training_routes':samples,'skipped_routes':skipped,
      'data_source':'FRA quarterly Amtrak performance route ridership, FY2025 Q1–Q4, summed; locally supplied normalized ridership.csv',
      'geography_source':'ACS county population + Census County Gazetteer; manually curated representative route county sequences',
      'limitations':[
        'Calibrates total demand scale only, not individual OD markets, rail mode share or behavioral elasticities.',
        '2022 NHTS, when published, anchors the total long-distance-trip frequency only. Long-distance 30-day counts multiplied by 12 do not identify local OD demand.',
        'Reference-route county lists omit some stations and may omit served markets; route totals can include riders outside the represented segment.',
        'Reference service frequency, fare, speed, access time and competing modes are assumed defaults, not observed route-specific values.',
        'Leave-one-out errors describe this reference set; not validated accuracy for new-build corridors.',
        'Rail segment mileage uses detoured county centroid separation, not observed track mileage.',
        'Route totals for connecting and overlapping Amtrak services can complicate interpretation.'
      ]}
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-only',action='store_true');parser.add_argument('--observations',type=Path,default=OBS);args=parser.parse_args()
    with args.observations.open(encoding='utf-8-sig',newline='') as f:
        values={r['route']:float(r['ridership']) for r in csv.DictReader(f) if int(r['quarters'])==4}
    res=calibrate(counties(),values)
    print('Corridors:',res['reference_routes'],'   multiplier:',res['demand_multiplier'],'   LOOCV median APE:',res['median_absolute_percentage_error_loo'],'%')
    for s in res['training_routes']:
        print(f"  {s['route']:<25} observed {s['observed']:>10,.0f}   cross-validated prediction {s['leave_one_out_prediction']:>10,}")
    if args.check_only:print('Check only; no file written.');return
    OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix('.tmp');tmp.write_text(json.dumps(res,indent=2)+'\n',encoding='utf-8');tmp.replace(OUT)
    print('Wrote',OUT)
if __name__=='__main__':main()
