"""County gravity sketch model with optional NHTS benchmark and Amtrak route-total scaling."""
from __future__ import annotations
import csv, json, math, hashlib
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).parent / 'data' / 'county_rail_inputs.csv'
MAX_STOPS = 12
CALIBRATION_PATH = Path(__file__).parent / "data" / "rail_forecast_calibration.json"
NHTS_PATH = Path(__file__).parent / "data" / "nhts_2022_profile.json"

def published_nhts_profile():
    """Only use publisher-produced validated profiles; never fabricate missing data."""
    try:
        d=json.loads(NHTS_PATH.read_text(encoding="utf-8"))
        if (d.get('schema_version')==1 and d.get('status')=='nhts_2022_person_weighted'
            and int(d['counts']['weight_valid'])>=1000
            and 0<float(d['annualized_long_distance_trips_per_person'])<300
            and len(d['input_sha256'])==64):
            return d
    except (OSError,KeyError,TypeError,ValueError):pass
    return None


def published_calibration():
    """Do not cache: local calibrations are visible after publishing."""
    try:
        doc=json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
        if (doc.get("schema_version")==1 and doc.get("status")=="amtrak_route_total_calibrated"
            and doc.get("reference_routes",0)>=8 and 0<float(doc["demand_multiplier"])<1e6
            and doc.get("county_catalog_sha256")==hashlib.sha256(DATA_PATH.read_bytes()).hexdigest()
            and doc.get("nhts_input_sha256")==((published_nhts_profile() or {}).get('input_sha256'))):
            return doc
    except (OSError,ValueError,KeyError,TypeError):pass
    return None


@lru_cache(maxsize=1)
def counties():
    if not DATA_PATH.exists(): return []
    result=[]
    with DATA_PATH.open(encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            try:
                pop=int(float(r['population']))
                lat=float(r['latitude']); lon=float(r['longitude'])
                if pop<=0 or not (-90<=lat<=90 and -180<=lon<=180): continue
                result.append({'fips':r['fips'].zfill(5),'name':r['name'],'state':r.get('state',''),
                    'population':pop,'income':float(r.get('median_income') or 0),
                    'lat':lat,'lon':lon,'source':r.get('source','unknown')})
            except (KeyError,ValueError,TypeError): continue
    return result

def haversine(a,b):
    lat1,lon1=map(math.radians,(a['lat'],a['lon']))
    lat2,lon2=map(math.radians,(b['lat'],b['lon']))
    x=2*3958.7613*math.asin(min(1, math.sqrt(math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2)))
    return x

def checked_float(raw,key,default,lo,hi):
    val=float(raw.get(key,default))
    if not math.isfinite(val) or val<lo or val>hi: raise ValueError(f'{key} must be between {lo} and {hi}.')
    return val

def forecast(payload, catalog=None, calibration="auto"):
    data={c['fips']:c for c in (catalog if catalog is not None else counties())}
    stops=payload.get('stops',[])
    if not isinstance(stops,list) or not 2<=len(stops)<=MAX_STOPS: raise ValueError('Choose 2–12 station counties.')
    if len(set(stops))!=len(stops):raise ValueError('Each station county can appear only once.')
    if not all(s in data for s in stops):raise ValueError('One or more selected counties are not in the catalog.')
    p=[data[s] for s in stops]
    if calibration == "auto":
        calibration=published_calibration() if len(data)>=3000 and not any("SYNTHETIC" in str(c.get("source","")).upper() for c in p) else None
    if calibration is not None and not isinstance(calibration,dict):raise ValueError("Invalid calibration setting.")
    empirical_factor=float(calibration["demand_multiplier"]) if calibration else 1.0
    departures=checked_float(payload,'round_trips',2,0.25,30)
    speed=checked_float(payload,'rail_speed',65,20,180)
    road_speed=checked_float(payload,'road_speed',55,20,85)
    fare=checked_float(payload,'fare_per_mile',0.20,0,1)
    vot=checked_float(payload,'value_of_time',20,1,100)
    rail_detour=checked_float(payload,'rail_detour',1.25,1,2.5)
    road_detour=checked_float(payload,'road_detour',1.17,1,2.5)
    # Explicit *assumptions*, NOT estimates from NHTS or Amtrak.
    nhts=published_nhts_profile()
    # If a survey profile is published, the scale of trip production is measured
    # as weighted annualized 50+ mile trips/person. The gravity distribution itself
    # remains assumed; Amtrak observations must be recalibrated after publishing.
    benchmark=nhts['annualized_long_distance_trips_per_person'] if nhts else 0.15
    rate=checked_float(payload,'base_trip_rate',benchmark,0.0001,300)
    exponent=checked_float(payload,'distance_exponent',1.1,0,3)
    rail_intercept=checked_float(payload,'rail_intercept',-1.5,-8,4)
    rail_sensitivity=checked_float(payload,'rail_sensitivity',0.8,0,5)
    frequency_elasticity=checked_float(payload,'frequency_elasticity',0.35,0,2)
    access_hours=checked_float(payload,'access_hours',1.0,0,4)
    auto_cost_mile=checked_float(payload,'auto_cost_mile',0.22,0,1)
    market_factor=checked_float(payload,'market_factor',1.0,0.05,10)
    # Adjacent-county centroid straight-line distance is not a rail alignment.
    segments=[haversine(p[i],p[i+1])*rail_detour for i in range(len(p)-1)]
    cumulative=[0.0]
    for s in segments: cumulative.append(cumulative[-1]+s)
    od=[]; boards=[0.]*len(p); alights=[0.]*len(p); loads=[0.]*len(segments)
    for i in range(len(p)):
      for j in range(i+1,len(p)):
        direct=haversine(p[i],p[j])
        rail_miles=cumulative[j]-cumulative[i]
        road_miles=direct*road_detour
        if direct<15: continue  # Intercounty trips below this distance not modeled.
        rail_time=rail_miles/speed+access_hours
        road_time=road_miles/road_speed+0.25
        rail_gc=rail_time*vot+fare*rail_miles
        road_gc=road_time*vot+auto_cost_mile*road_miles
        utility=rail_intercept+rail_sensitivity*(road_gc-rail_gc)/50+frequency_elasticity*math.log(departures/2)
        rail_share=1/(1+math.exp(-max(-30,min(30,utility))))
        # Unordered OD pair represents both directions combined (annual one-way journeys).
        total_od=rate*empirical_factor*math.sqrt(p[i]['population']*p[j]['population'])*(max(15,direct)/100)**(-exponent)*market_factor
        journeys=total_od*rail_share
        od.append({'origin':p[i]['name'],'destination':p[j]['name'],'origin_fips':p[i]['fips'],'destination_fips':p[j]['fips'],
          'distance_miles':round(rail_miles,1),'auto_time_hours':round(road_time,2),'rail_time_hours':round(rail_time,2),
          'rail_share':round(rail_share,4),'annual_rides':round(journeys)})
        boards[i]+=journeys/2;boards[j]+=journeys/2
        alights[i]+=journeys/2;alights[j]+=journeys/2
        for k in range(i,j):loads[k]+=journeys
    total=sum(r['annual_rides'] for r in od)
    annual_pax_miles=sum(r['annual_rides']*r['distance_miles'] for r in od)
    station=[{'fips':x['fips'],'name':x['name'],'population':x['population'],'lat':x['lat'],'lon':x['lon'],
              'boardings':round(boards[i]),'alightings':round(alights[i])} for i,x in enumerate(p)]
    segs=[{'from':p[k]['name'],'to':p[k+1]['name'],'miles':round(s,1),'annual_passenger_trips':round(loads[k]),
           'avg_per_train':round(loads[k]/(departures*2*365),1)} for k,s in enumerate(segments)]
    calibrated=calibration is not None
    return {'status':'route_total_calibrated_scenario' if calibrated else 'uncalibrated_scenario',
       'model':'Gravity and generalized-cost scenario; empirical route-total scale calibration' if calibrated else 'Transparent gravity + generalized-cost mode-choice illustration',
       'nhts':{'year':2022,'weighted_persons':nhts['counts']['weight_valid'],
                'long_distance_trips_per_person_annualized':nhts['annualized_long_distance_trips_per_person'],
                'amtrak_uses_per_person_past_year':nhts['amtrak_uses_per_person_past_year'],
                'survey_amtrak_users_fraction':nhts['fraction_persons_using_amtrak_past_year']} if nhts else None,
       'calibration':{'fiscal_year':calibration['fiscal_year'],'reference_routes':calibration['reference_routes'],
           'demand_multiplier':empirical_factor,'median_loo_error_pct':calibration['median_absolute_percentage_error_loo'],
           'loo_residual_10_90':calibration['multiplicative_error_10_90_loo']} if calibrated else None,
       'annual_ridership':round(total),'annual_passenger_miles':round(annual_pax_miles),
       'route_miles':round(cumulative[-1],1),'od':od,'stations':station,'segments':segs,
       'assumptions':{'round_trips_per_day':departures,'speed_mph':speed,'fare_per_mile':fare,'base_trip_rate':rate,'market_factor':market_factor},
       'warning':('EMPIRICALLY SCALED, NOT A VALIDATED NEW-CORRIDOR FORECAST. Calibrated to FY2025 Amtrak route totals, not county OD observations. Travel-choice parameters and route service assumptions remain illustrative. NHTS trip frequency is an annualized national benchmark, not county OD flows. The empirical validation errors are not a confidence interval.' if calibrated else 'ILLUSTRATIVE SCENARIO, NOT A VALIDATED FORECAST. '+('NHTS supplies a survey-weighted national long-distance trip frequency, but not county OD or choice elasticities. ' if nhts else 'NHTS not yet published. ')+'County centroids approximate stations; actual OD trips and Amtrak calibration are not included.')}
