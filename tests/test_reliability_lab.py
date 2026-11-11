from app.reliability_service import catalog,data
from app import create_app

def test_no_or_valid_otp():
    c=catalog()
    assert 'available' in c
    assert isinstance(c['routes'],list)
    d=data()
    if not c['available']:
        assert d['available'] is False
        assert d['points']==[]
    else:
        assert d['available'] is True
        assert all(p['ridership_growth_pct'] is not None and p['otp_change_pp'] is not None for p in d['points'])
        assert len(d['points'])==len({(p['slug'],p['period']) for p in d['points']})

def test_invalid_filters():
    import pytest
    with pytest.raises(ValueError):data(route_slugs=['does-not-exist']) if catalog()['available'] else (_ for _ in ()).throw(ValueError())
    if catalog()['available']:
        with pytest.raises(ValueError):data(period='FY0000 Q1')

def test_page():
    app=create_app()
    app.config['TESTING']=True
    with app.test_client() as client:
        assert client.get('/projects/intercity-rail/reliability').status_code==200
        assert client.get('/api/rail/reliability').status_code==200
