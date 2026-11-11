"""Run with pytest in a project where Flask is installed."""
from math import isclose
from app.services import get_group_ridership, get_system_trend
from app.service_categories import CATEGORY_LABELS
from app.scorecards_service import detail as scorecards_detail
from app.financial_service import detail as financial_detail
from app.delay_service import detail as delay_detail
from app.station_service import detail as station_detail


def test_ridership_categories_reconcile_latest():
    last = get_system_trend()[-1]['ridership']
    parts = [get_group_ridership(c)['latest_ridership'] for c in CATEGORY_LABELS]
    assert all(x is not None for x in parts)
    assert isclose(sum(parts), last, rel_tol=1e-10)


def test_scorecards_group_summary_is_unfiltered_by_minimum():
    d1 = scorecards_detail(category='long_distance', minimum_riders=0)
    d2 = scorecards_detail(category='long_distance', minimum_riders=100000)
    assert d1['group_summary'] == d2['group_summary']
    assert d1['group_summary']['customer_otp_pct'] is None


def test_finance_no_unweighted_ratio_average():
    group = financial_detail('group:state_supported')
    if group is None: return
    for o in group['observations']:
        if o['status']=='valid':
            assert isclose(o['ratio'],o['numerator']/o['denominator'])


def test_missing_data_is_not_invented():
    assert get_group_ridership('bad_group') is None
    assert delay_detail('group:bad_group') is None
    assert station_detail('group:bad_group') is None
    assert financial_detail('group:bad_group') is None
