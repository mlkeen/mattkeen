"""Quarterly FRA route scorecards: matched ridership, financial, and customer OTP.

Passenger revenue is sourced from the *passenger_revenue* field of the FRA
avoidable-expense table, NEVER operating_revenue. Financial reporting units
match ridership by APT code AND reported route name AND fiscal quarter.
"""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from .services import PUBLISHED_CSV, get_all_routes, get_route, get_system_trend
from .otp_service import get_otp_match
from .service_categories import CATEGORY_LABELS

ROOT = Path(__file__).resolve().parent
FINANCIALS = ROOT / 'data' / 'fra_financials.json'


def _valid(x):
    try:
        n = float(x)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def _key(code, name, period):
    return str(code).strip(), ' '.join(str(name).casefold().split()), str(period)


def _financial_index():
    if not FINANCIALS.is_file():
        return None
    raw = json.loads(FINANCIALS.read_text(encoding='utf-8'))
    if raw.get('version') != 1:
        raise ValueError('Unsupported published FRA financials version')
    groups = defaultdict(list)
    for r in raw.get('records', []):
        if r.get('level') != 'route':
            continue
        groups[_key(r.get('apt_code'), r.get('route'), r.get('period'))].append(r)
    return groups


def _passenger_revenue(records):
    """Return passenger revenue only with an unambiguous, valid financial row.

    Both state-payment treatments should report the same passenger revenue; if
    not, show an explicit conflict rather than making an arbitrary selection.
    """
    if not records:
        return None, 'financial_record_missing', None
    measures = [r for r in records if r.get('measure') == 'avoidable_expense']
    if not measures:
        return None, 'passenger_revenue_missing', None
    values = [_valid(r.get('numerator')) for r in measures]
    if any(v is None for v in values):
        return None, 'passenger_revenue_missing', None
    if any(v < 0 for v in values):
        return None, 'negative_passenger_revenue', None
    if max(values) - min(values) > max(0.01, abs(values[0]) * 1e-8):
        return None, 'conflicting_passenger_revenue', None
    source = next((r for r in measures if r.get('state_payments_included') is False), measures[0])
    return values[0], 'valid', {
        'workbook': source.get('source_workbook'), 'sheet': source.get('source_sheet'),
        'row': source.get('source_excel_row'),
    }


def _cost_recovery(records):
    candidates = [r for r in records if r.get('measure') == 'cost_recovery']
    if len(candidates) != 1:
        return None
    r = candidates[0]
    v = _valid(r.get('ratio')) if r.get('status') == 'valid' else None
    return round(v * 100, 2) if v is not None and v >= 0 else None


def _expense_coverage(records):
    candidates = [r for r in records if r.get('measure') == 'avoidable_expense'
                  and r.get('state_payments_included') is False]
    if len(candidates) != 1:
        return None
    r = candidates[0]
    v = _valid(r.get('ratio')) if r.get('status') == 'valid' else None
    return round(v * 100, 2) if v is not None and v >= 0 else None


@lru_cache(maxsize=1)
def _load():
    financials = _financial_index()
    # Use authoritative published ridership dataset, and require unique
    # (period, APT, route name) keys before joining.
    raw_index = {}
    with PUBLISHED_CSV.open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        for r in reader:
            if r.get('reporting_level') != 'route':
                continue
            period = f"FY{int(r['fiscal_year'])} Q{int(r['fiscal_quarter'])}"
            key = _key(r.get('apt_code'), r.get('route'), period)
            if key in raw_index:
                raise ValueError(f'Duplicate ridership source route/quarter {key}')
            raw_index[key] = r

    rows = []
    periods = [p['period'] for p in get_system_trend()]
    for route in get_all_routes():
        detail = get_route(route['slug'])
        otp = get_otp_match(route['name'])
        otp_index = {r['period']: r for r in otp['series']} if otp else {}
        for obs in detail['series']:
            period = obs['period']
            raw = raw_index.get(_key(route['apt_code'], route['name'], period))
            if raw is None:
                continue
            riders = _valid(obs['ridership'])
            miles = _valid(raw.get('passenger_miles'))
            financial_records = (financials or {}).get(_key(route['apt_code'], route['name'], period), [])
            revenue, status, revenue_source = _passenger_revenue(financial_records) if financials is not None else (None, 'financials_not_published', None)
            rev_rider = round(revenue / riders, 4) if revenue is not None and riders is not None and riders > 0 else None
            rev_mile = round(revenue / miles, 5) if revenue is not None and miles is not None and miles > 0 else None
            otp_obs = otp_index.get(period)
            rows.append({
                'slug': route['slug'], 'name': route['name'], 'apt_code': route['apt_code'],
                'category': route['category'], 'period': period, 'ridership': riders,
                'yoy_pct': obs['yoy_pct'], 'passenger_miles': miles if miles is not None and miles >= 0 else None,
                'customer_otp_pct': round(otp_obs['otp'] * 100, 2) if otp_obs and otp_obs['otp'] is not None else None,
                'cost_recovery_pct': _cost_recovery(financial_records),
                'avoidable_coverage_pct': _expense_coverage(financial_records),
                'passenger_revenue': revenue, 'revenue_per_rider': rev_rider,
                'revenue_per_passenger_mile': rev_mile,
                'revenue_status': status,
                'ridership_source': {'workbook': raw.get('source_workbook'), 'sheet': raw.get('source_sheet'),
                                     'row': raw.get('source_excel_row')},
                'revenue_source': revenue_source,
                'otp_match': otp is not None,
            })
    return {'periods': periods, 'rows': rows, 'financials_available': financials is not None,
            'otp_available': any(r['otp_match'] for r in rows)}


METRICS = ('ridership', 'yoy_pct', 'customer_otp_pct', 'cost_recovery_pct',
           'avoidable_coverage_pct', 'revenue_per_rider', 'revenue_per_passenger_mile')


def overview():
    d = _load()
    return {'periods': d['periods'], 'latest_period': d['periods'][-1],
            'categories': CATEGORY_LABELS, 'financials_available': d['financials_available'],
            'otp_available': d['otp_available'], 'metrics': METRICS}


def detail(period=None, category='all', sort='ridership', direction='desc', minimum_riders=0):
    d = _load()
    period = period or d['periods'][-1]
    if period not in d['periods']:
        raise ValueError('Unknown fiscal quarter')
    if category not in ('all', *CATEGORY_LABELS):
        raise ValueError('Unknown service group')
    if sort not in METRICS:
        raise ValueError('Unknown metric')
    if direction not in ('asc', 'desc'):
        raise ValueError('Sort direction must be asc or desc')
    if not isinstance(minimum_riders, int) or minimum_riders < 0:
        raise ValueError('Minimum riders must be a nonnegative integer')
    rows = [r for r in d['rows'] if r['period'] == period and (category == 'all' or r['category'] == category)
            and (r['ridership'] is not None and r['ridership'] >= minimum_riders)]
    # Missing statistics always at the bottom in either sort direction.
    filled = [r for r in rows if r[sort] is not None]
    missing = [r for r in rows if r[sort] is None]
    filled.sort(key=lambda r: (r[sort], r['name'].casefold()), reverse=direction == 'desc')
    missing.sort(key=lambda r: r['name'].casefold())
    rows = filled + missing
    # Group summary is based on *all* source routes in the chosen group,
    # not just routes meeting the ranking's minimum-passenger threshold.
    all_group = [r for r in d['rows'] if r['period']==period and (category=='all' or r['category']==category)]
    group_summary = None
    if category != 'all':
        def complete_sum(field):
            vals=[r[field] for r in all_group]
            return sum(vals) if vals and all(v is not None and v>=0 for v in vals) else None
        ridership = complete_sum('ridership')
        miles = complete_sum('passenger_miles')
        revenue = complete_sum('passenger_revenue')
        group_summary = {'label':CATEGORY_LABELS[category], 'route_count':len(all_group),
            'ridership':ridership,'passenger_miles':miles,'passenger_revenue':revenue,
            'revenue_per_rider':round(revenue/ridership,4) if revenue is not None and ridership and ridership>0 else None,
            'revenue_per_passenger_mile':round(revenue/miles,5) if revenue is not None and miles and miles>0 else None,
            'customer_otp_pct':None,
            'note':'Revenue yields use group totals only if every included route has complete valid data; no mean of route yields. Customer OTP cannot be aggregated without matched passenger-level weights. Minimum rider filter affects rankings, not this summary.'}
    return {'group_summary':group_summary,'period': period, 'category': category, 'sort': sort, 'direction': direction,
            'minimum_riders': minimum_riders, 'count': len(rows),
            'with_metric': len(filled), 'rows': rows,
            'financials_available': d['financials_available'], 'otp_available': d['otp_available'],
            'method': 'Passenger revenue (not total operating revenue) / ridership or passenger-miles. Exact APT code + route label + quarter match; negative revenue and nonpositive denominators excluded. OTP exact whole-service matches only.'}
