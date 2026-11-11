import pytest
from app import create_app
from app.compare_service import comparison_catalog, get_comparison


def test_comparison_good_and_gaps():
    catalog = comparison_catalog()
    selected = [r['slug'] for r in catalog[:3]]
    result = get_comparison(selected)
    assert len(result['routes']) == 3
    assert len(result['periods']) == 20
    assert all(len(r['series']) == 20 for r in result['routes'])
    assert all('otp' in r for r in result['routes'])


def test_comparison_rejects_invalid():
    catalog = comparison_catalog()
    slug = catalog[0]['slug']
    for invalid in ([], [slug]*2, ['no-such-route'], [r['slug'] for r in catalog[:5]]):
        with pytest.raises(ValueError):
            get_comparison(invalid)


def test_comparison_http():
    app = create_app()
    client = app.test_client()
    response = client.get('/projects/intercity-rail/compare')
    assert response.status_code == 200
    assert b'Route' in response.data and b'Comparison Lab' in response.data
    routes = comparison_catalog()
    response = client.get('/api/rail/compare',query_string=[('route',routes[0]['slug']),('route',routes[1]['slug'])])
    assert response.status_code == 200
    assert len(response.json['routes']) == 2
    assert client.get('/api/rail/compare').status_code == 400
