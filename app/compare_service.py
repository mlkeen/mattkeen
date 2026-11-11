"""Comparison Lab: series are joined on fiscal quarter, never by row position.

Ridership history is scoped to (APT code, original service name). OTP is
included only for a conservative one-to-one service/subservice name match.
"""
from .services import get_all_routes, get_route, get_system_trend
from .otp_service import get_otp_match, get_otp_overview

MAX_COMPARE = 4


def get_comparison(slugs):
    """Return comparable data, or raise ValueError for invalid selections."""
    if not 1 <= len(slugs) <= MAX_COMPARE:
        raise ValueError('Select between 1 and 4 services.')
    if len(set(slugs)) != len(slugs):
        raise ValueError('Select each service only once.')
    selected = []
    periods = [p['period'] for p in get_system_trend()]
    for slug in slugs:
        route = get_route(slug)
        if route is None:
            raise ValueError(f'Unknown service: {slug}')
        otp = get_otp_match(route['name'])
        # Respect the difference between a whole FRA route and one subservice.
        selected.append({
            'slug': route['slug'], 'name': route['name'], 'apt_code': route['apt_code'], 'category': route['category'],
            'latest_ridership': route['latest_ridership'], 'latest_period': route['latest_period'],
            'yoy_pct': route['yoy_pct'], 'quarters_valid': route['quarters_valid'],
            'series': [{
                'period': row['period'], 'ridership': row['ridership'],
                'yoy_pct': row['yoy_pct'], 'status': row['status'],
                'source_workbook': row['source_workbook'],
            } for row in route['series']],
            'otp': ({
                'label': otp['label'], 'slug': otp['slug'], 'latest_otp': otp['latest_otp'],
                'yoy_pp': otp['yoy_pp'],
                'series': [{'period': p['period'], 'otp': p['otp'], 'yoy_pp': p['yoy_pp']}
                           for p in otp['series']],
            } if otp else None),
        })
    return {'periods': periods, 'routes': selected, 'max_routes': MAX_COMPARE,
            'otp_available': get_otp_overview()['available'],
            'method': 'Reported FRA financial ridership; route-level C OTP only for exact whole-service matches.'}


def comparison_catalog():
    return [{k: r[k] for k in ('slug', 'name', 'apt_code', 'category', 'latest_ridership', 'quarters_valid')}
            for r in get_all_routes()]
