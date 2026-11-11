"""Transparent screening-level incremental transit benefit-cost model.

All input monetary amounts are REAL base-year US dollars. Baseline project
is no-build. No fare revenues or taxes counted as additional social benefits.
"""
from __future__ import annotations
from math import isfinite

DEFAULTS = {
    'name': 'Example: Frequent bus service upgrade',
    'base_year': 2026,
    'construction_years': 2,
    'operating_years': 20,
    'discount_rate': 3.1,
    'capital_cost': 25000000,
    'annual_incremental_om': 1100000,
    'om_growth_pct': 0,
    'affected_existing_trips': 800000,
    'diverted_trips': 90000,
    'generated_trips': 25000,
    'time_saved_minutes': 5,
    'value_of_time': 18,
    'avoided_auto_miles_per_diverted_trip': 7,
    'vehicle_operating_cost_per_mile': 0.28,
    'annual_safety_benefit': 80000,
    'annual_air_quality_benefit': 65000,
    'annual_other_benefit': 0,
    'annual_residual_value': 0,
    'ridership_growth_pct': 0,
    'benefit_ramp_years': 1,
}

NUMERIC = tuple(k for k in DEFAULTS if k != 'name')


def validate(data):
    cfg = dict(DEFAULTS)
    for key in DEFAULTS:
        if key in data:
            cfg[key] = data[key]
    errors = []
    cfg['name'] = str(cfg['name']).strip()[:150]
    for key in NUMERIC:
        try:
            value = float(cfg[key])
            if not isfinite(value): raise ValueError()
            cfg[key] = value
        except (ValueError, TypeError):
            errors.append(f'{key} must be a finite number')
    if errors: raise ValueError('; '.join(errors))
    for key in ('base_year','construction_years','operating_years','benefit_ramp_years'):
        if int(cfg[key]) != cfg[key]: errors.append(f'{key} must be an integer')
        cfg[key] = int(cfg[key])
    if not (2000 <= cfg['base_year'] <= 2100): errors.append('base_year out of range')
    if not (1 <= cfg['construction_years'] <= 20): errors.append('construction_years must be 1 to 20')
    if not (1 <= cfg['operating_years'] <= 60): errors.append('operating_years must be 1 to 60')
    if not (1 <= cfg['benefit_ramp_years'] <= cfg['operating_years']): errors.append('benefit_ramp_years must be between 1 and operating_years')
    if not (0 <= cfg['discount_rate'] <= 30): errors.append('discount_rate must be between 0 and 30 percent')
    if not (-99 < cfg['ridership_growth_pct'] <= 30): errors.append('ridership_growth_pct must be above -99 and at most 30')
    if not (-99 < cfg['om_growth_pct'] <= 30): errors.append('om_growth_pct must be above -99 and at most 30')
    for key in ('capital_cost','annual_incremental_om','affected_existing_trips','diverted_trips','generated_trips',
                'time_saved_minutes','value_of_time','avoided_auto_miles_per_diverted_trip',
                'vehicle_operating_cost_per_mile','annual_safety_benefit','annual_air_quality_benefit',
                'annual_other_benefit','annual_residual_value'):
        if cfg[key] < 0: errors.append(f'{key} cannot be negative')
    if errors: raise ValueError('; '.join(errors))
    return cfg


def analyze(data):
    c = validate(data)
    rate = c['discount_rate']/100
    rows=[]; pv_benefits=0.0; pv_costs=0.0
    pv_by_category = {'existing_time':0.,'new_time':0.,'avoided_auto':0.,'safety':0.,'air_quality':0.,'other':0.,'residual':0.}
    # Year t=0 is the base year (first construction year), with no discounting.
    # For analytic consistency all flows are placed at year end except first-year capital (t=0).
    for t in range(c['construction_years']+c['operating_years']):
        in_service = t>=c['construction_years']
        service_year = t-c['construction_years']+1 if in_service else 0
        capital = c['capital_cost']/c['construction_years'] if not in_service else 0.
        factors={k:0. for k in pv_by_category}
        om = 0.
        if in_service:
            demand_factor=(1+c['ridership_growth_pct']/100)**(service_year-1)
            ramp=min(1.,service_year/c['benefit_ramp_years'])
            effect=demand_factor*ramp
            unit_time=c['time_saved_minutes']/60*c['value_of_time']
            factors['existing_time']=c['affected_existing_trips']*effect*unit_time
            # Simplified rule-of-half for newly diverted and generated trips.
            factors['new_time']=(c['diverted_trips']+c['generated_trips'])*effect*unit_time*.5
            factors['avoided_auto']=c['diverted_trips']*effect*c['avoided_auto_miles_per_diverted_trip']*c['vehicle_operating_cost_per_mile']
            for k, field in (('safety','annual_safety_benefit'),('air_quality','annual_air_quality_benefit'),('other','annual_other_benefit')):
                factors[k]=c[field]*ramp
            if service_year==c['operating_years']:
                factors['residual']=c['annual_residual_value']
            om=c['annual_incremental_om']*(1+c['om_growth_pct']/100)**(service_year-1)
        annual_b=sum(factors.values()); annual_c=capital+om
        disc=(1+rate)**t
        pv_b=annual_b/disc; pv_c=annual_c/disc
        pv_benefits+=pv_b;pv_costs+=pv_c
        for k,v in factors.items():pv_by_category[k]+=v/disc
        rows.append({'year':c['base_year']+t,'t':t,'phase':'Operations' if in_service else 'Construction',
                     'service_year':service_year,'capital_cost':capital,'incremental_om':om,
                     **factors,'benefits':annual_b,'costs':annual_c,
                     'net':annual_b-annual_c,'pv_benefits':pv_b,'pv_costs':pv_c,'pv_net':pv_b-pv_c})
    # If incremental O&M is negative (net savings), move it to benefit side for a meaningful BCR.
    # This avoids negative denominators while preserving NPV; individual annual values remain auditable.
    # The initial MVP disallows negative incremental O&M in ratio reporting until an explicit
    # benefit/cost accounting policy is implemented.
    bcr=pv_benefits/pv_costs if pv_costs>0 else None
    return {'inputs':c,'years':rows,'pv_benefits':pv_benefits,'pv_costs':pv_costs,
            'npv':pv_benefits-pv_costs,'bcr':bcr,'pv_categories':pv_by_category,
            'undiscounted_benefits':sum(r['benefits'] for r in rows),
            'undiscounted_costs':sum(r['costs'] for r in rows),
            'assumptions':['Illustrative input assumptions, not USDOT-recommended defaults.',
                           'Annual trip cohorts and time savings must be measured against no-build.',
                           'Generated and diverted passenger time benefit uses a simplified half-rule.',
                           'Avoided auto operating costs assume each diverted transit trip replaces one car trip; adjust for occupancy and access trips.',
                           'Air-quality benefits entered as annual dollars; do not also count them in vehicle operating costs.',
                           'All figures must be expressed in the same constant-dollar price year.',
                           'Same editable discount rate is used for all categories in this screening tool; grant applications may require a distinct emissions rate.',
                           'Fare revenue is a transfer and is not counted as an additional social benefit.',
                           'Capital assumed evenly over construction years; first construction year is t=0.']}


def scenarios(data):
    base=validate(data)
    cases=[('Base',{}) ,('Capital +20%',{'capital_cost':base['capital_cost']*1.2}),
           ('Benefits -20%',{'affected_existing_trips':base['affected_existing_trips']*.8,
                             'diverted_trips':base['diverted_trips']*.8,
                             'generated_trips':base['generated_trips']*.8,
                             'annual_safety_benefit':base['annual_safety_benefit']*.8,
                             'annual_air_quality_benefit':base['annual_air_quality_benefit']*.8,
                             'annual_other_benefit':base['annual_other_benefit']*.8}),
           ('Discount +2 pp',{'discount_rate':min(30,base['discount_rate']+2)})]
    return [{'label':label,'npv':a['npv'],'bcr':a['bcr'],'pv_benefits':a['pv_benefits'],'pv_costs':a['pv_costs']}
            for label,override in cases for a in [analyze({**base,**override})]]
