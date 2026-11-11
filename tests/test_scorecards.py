"""Run with pytest from project root; full HTTP test requires Flask dependency."""
from __future__ import annotations
import json
import pytest
from app import scorecards_service as sc


def test_revenue_reconciliation():
    core = {'measure': 'avoidable_expense', 'numerator': 1500.0,
            'source_workbook': 'FY26 Q3 Financial Metrics.xlsx', 'source_sheet': 'Avoidable', 'source_excel_row': '17'}
    rows = [{**core, 'state_payments_included': False}, {**core, 'state_payments_included': True}]
    value, status, src = sc._passenger_revenue(rows)
    assert (value, status, src['row']) == (1500.0, 'valid', '17')
    assert sc._passenger_revenue([{**rows[0], 'numerator': -5.0}])[1] == 'negative_passenger_revenue'
    assert sc._passenger_revenue([rows[0], {**rows[1], 'numerator': 1200.0}])[1] == 'conflicting_passenger_revenue'
    assert sc._passenger_revenue([])[1] == 'financial_record_missing'


def test_financial_ratios_preserve_quality_flags():
    row = {'measure': 'cost_recovery', 'status': 'valid', 'ratio': .75}
    assert sc._cost_recovery([row]) == 75
    assert sc._cost_recovery([{**row, 'status': 'negative_expense', 'ratio': None}]) is None


def test_publish_missing_then_present(tmp_path, monkeypatch):
    # Test using the real published ridership sample and a synthetic financial
    # record matching its route code, name and latest quarter exactly.
    sc._load.cache_clear()
    monkeypatch.setattr(sc, 'FINANCIALS', tmp_path / 'fra_financials.json')
    no_finances = sc.detail(period='FY2026 Q3')
    assert no_finances['count'] > 0
    assert not no_finances['financials_available']
    assert all(r['revenue_per_rider'] is None for r in no_finances['rows'])
    sample = next(r for r in no_finances['rows'] if r['ridership'] and r['passenger_miles'] and r['passenger_miles'] > 0)
    rev = 400000.0
    synthetic = {'version': 1, 'records': [
        {'level': 'route', 'period': sample['period'], 'apt_code': sample['apt_code'],
         'route': sample['name'], 'measure': 'avoidable_expense', 'state_payments_included': False,
         'numerator': rev, 'status': 'valid', 'ratio': 0.5, 'source_workbook': 'fixture.xlsx',
         'source_sheet': 'Avoidable', 'source_excel_row': '12'},
        {'level': 'route', 'period': sample['period'], 'apt_code': sample['apt_code'],
         'route': sample['name'], 'measure': 'avoidable_expense', 'state_payments_included': True,
         'numerator': rev, 'status': 'valid', 'ratio': 0.5},
        {'level': 'route', 'period': sample['period'], 'apt_code': sample['apt_code'],
         'route': sample['name'], 'measure': 'cost_recovery', 'status': 'valid', 'ratio': .75}
    ]}
    sc.FINANCIALS.write_text(json.dumps(synthetic), encoding='utf-8')
    sc._load.cache_clear()
    try:
        actual = sc.detail(period='FY2026 Q3')
        result = next(r for r in actual['rows'] if r['slug'] == sample['slug'])
        assert result['revenue_per_rider'] == round(rev / sample['ridership'], 4)
        assert result['revenue_per_passenger_mile'] == round(rev / sample['passenger_miles'], 5)
        assert result['cost_recovery_pct'] == 75
        assert result['revenue_source']['workbook'] == 'fixture.xlsx'
        assert all(r['revenue_per_rider'] is None for r in actual['rows'] if r['slug'] != sample['slug'])
        assert sc.detail(category=sample['category'], sort='revenue_per_rider')['rows'][0]['slug'] == sample['slug']
        with pytest.raises(ValueError): sc.detail(period='FY2001 Q1')
        with pytest.raises(ValueError): sc.detail(sort='not_a_metric')
    finally:
        sc._load.cache_clear()


def test_scorecards_endpoint():
    flask = pytest.importorskip('flask')
    from app import create_app
    app = create_app({'TESTING': True})
    with app.test_client() as client:
        page = client.get('/projects/intercity-rail/scorecards')
        assert page.status_code == 200
        assert b'Revenue per passenger-mile' in page.data
        data = client.get('/api/rail/scorecards?period=FY2026+Q3&category=long_distance').get_json()
        assert len(data['rows']) > 0
        assert all(r['category'] == 'long_distance' for r in data['rows'])
        assert client.get('/api/rail/scorecards?sort=bad').status_code == 400
