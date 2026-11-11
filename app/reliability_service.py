"""Exploratory comparison: ridership YoY (%) versus customer OTP YoY (pp).

Joins only unambiguous exact whole-service matches and fiscal quarters. This
is a descriptive association, not a causal design or independent panel sample.
"""
from __future__ import annotations
from functools import lru_cache
from math import sqrt
from .services import get_all_routes, get_route, get_system_trend
from .otp_service import get_otp_match, get_otp_overview


def catalog():
    items = []
    for route in get_all_routes():
        otp = get_otp_match(route['name'])
        if otp:
            items.append({'slug':route['slug'], 'name':route['name'],
                          'apt_code':route['apt_code'], 'category':route['category'], 'otp_label':otp['label']})
    return {'available':get_otp_overview()['available'], 'routes':items,
            'periods':[p['period'] for p in get_system_trend()],
            'definition':'Ridership growth is year-over-year percent; OTP change is year-over-year percentage points.'}


def data(route_slugs=None, period=None):
    info=catalog()
    if not info['available']:
        return {'available':False,'points':[],'stats':None,'periods':info['periods'],
                'selected_routes':[], 'count_routes':0,'excluded':{'no_otp_source':True}}
    candidates={r['slug']:r for r in info['routes']}
    if route_slugs is None or not route_slugs:
        selected=list(candidates)
    else:
        selected=list(route_slugs)
        if len(set(selected))!=len(selected):
            raise ValueError('Select each route no more than once.')
        if any(s not in candidates for s in selected):
            raise ValueError('Unknown or unmatched service in selection.')
    if period not in (None,'all') and period not in info['periods']:
        raise ValueError('Unknown fiscal quarter.')
    points=[]
    for slug in selected:
        r=get_route(slug)
        otp=get_otp_match(r['name'])
        if otp is None:continue
        by_period={p['period']:p for p in otp['series']}
        for row in r['series']:
            if period not in (None,'all') and row['period']!=period:continue
            match=by_period.get(row['period'])
            if not match:continue
            growth=row['yoy_pct']
            change=match['yoy_pp']
            if growth is None or change is None:continue
            # Ridership YoY excludes negative source adjustments through loader.
            points.append({'slug':slug,'name':r['name'],'apt_code':r['apt_code'],
                           'period':row['period'],'category':r['category'],'ridership_growth_pct':growth,
                           'otp_change_pp':change,'ridership':row['ridership'],
                           'otp':match['otp'],
                           'ridership_source_workbook':row['source_workbook'],
                           'otp_source_workbook':match['source_workbook']})
    points.sort(key=lambda p:(p['period'],p['name']))
    n=len(points)
    stats=None
    if n>=3:
        # Regress ridership YoY percentage growth (y) on OTP YoY pp (x).
        xs=[p['otp_change_pp'] for p in points]
        ys=[p['ridership_growth_pct'] for p in points]
        xm=sum(xs)/n;ym=sum(ys)/n
        sxx=sum((x-xm)**2 for x in xs);syy=sum((y-ym)**2 for y in ys)
        if sxx>0 and syy>0:
            sxy=sum((x-xm)*(y-ym) for x,y in zip(xs,ys))
            slope=sxy/sxx; corr=sxy/sqrt(sxx*syy)
            stats={'n':n,'routes':len({p['slug'] for p in points}),
                   'slope':round(slope,5),'intercept':round(ym-slope*xm,5),
                   'correlation':round(corr,5),'r_squared':round(corr**2,5)}
    return {'available':True,'points':points,'stats':stats,'periods':info['periods'],
            'selected_routes':selected,'count_routes':len({p['slug'] for p in points}),
            'method':'Descriptive OLS pooled across route-quarters; repeated services and temporal confounding invalidate naive causal or significance interpretations. Year-over-year compares the same fiscal quarter in adjacent years.'}
