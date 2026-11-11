"""Explicit APT financial-route service categories, shared by all rail pages.

FRA operating service lines are NEC, State Supported, and Long Distance;
we expose Acela separately by request and reserve NEC Regional and special trains.
Classification is by APT code and is historical/financial route classification,
not a claim that every operational subservice is separately state-funded.
"""
from __future__ import annotations

CATEGORY_LABELS = {
    'acela': 'Acela',
    'state_supported': 'State Supported Service',
    'long_distance': 'Long Distance',
    'nec_other': 'Other Northeast Corridor',
    'special': 'Special / Unclassified',
}
LONG_DISTANCE_CODES = {'16','18','19','25','26','27','28','30','31','32','33','34','45','48','52','63'}
STATE_SUPPORTED_CODES = {'03','04','07','09','11','12','14','15','17','20','21','22','23','24','29','35','36','37','39','40','41','46','47','50','51','54','56','57','64','65','66','67'}
SPECIAL_CODES = {'96','99'}
NEC_OTHER_CODES = {'05'}
# Springfield and Virginia reporting segments are State Supported in the
# financial-route classification, even where the physical train is an NEC service.


def category_for_apt(apt_code, name=''):
    code = str(apt_code).rsplit('_', 1)[-1].zfill(2)
    if code == '01': return 'acela'
    if code == '05': return 'nec_other'
    if code in SPECIAL_CODES: return 'special'
    if code in LONG_DISTANCE_CODES: return 'long_distance'
    if code in STATE_SUPPORTED_CODES: return 'state_supported'
    return 'special'


def category_for_operational(service, subservice=''):
    """Map published operational service labels only when recognizable.

    Never infer a subservice's financial classification from a fuzzy match.
    A not-mapped reporting unit is surfaced as Special / Unclassified.
    """
    from .services import get_all_routes
    normalized = lambda x: ' '.join(str(x).casefold().split())
    by_name = {}
    for r in get_all_routes():
        key = normalized(r['name'])
        by_name.setdefault(key,set()).add(r['category'])
    for text in (service, subservice):
        categories = by_name.get(normalized(text), set())
        if len(categories) == 1: return next(iter(categories))
    # Recognizable operational crosswalks (do not combine measures).
    s=normalized(service)
    if s in {'acela'}:return 'acela'
    if s in {'northeast regional','on spine northeast regional','regional'}:return 'nec_other'
    return 'special'
