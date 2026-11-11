import csv
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.publish_delays import compile_delays

HEADER=['fiscal_year','fiscal_quarter','service','sub_service','responsibility','delay_code','delay_minutes','host_code','source_workbook','source_sheet','source_excel_row','host_train_miles']

def sample(tmp_path, minutes='15'):
    path=tmp_path/'delay_by_code.csv'
    with path.open('w',newline='',encoding='utf-8') as stream:
        w=csv.writer(stream);w.writerow(HEADER)
        w.writerows([[2022,1,'Downeaster','Downeaster','Host Railroad','DSR',minutes,'CS','file.xlsx','DelayandMileage',2,9999],
                     [2022,1,'Downeaster','Downeaster','Amtrak','ENG','4','CS','file.xlsx','DelayandMileage',3,9999],
                     [2022,2,'Downeaster','Downeaster','Host Railroad','DSR','10','CS','file2.xlsx','DelayandMileage',2,10000]])
    return path

def test_aggregation_and_no_double_count(tmp_path):
    out=compile_delays(sample(tmp_path))
    assert out['rows_processed']==3
    assert out['periods']==['FY2022 Q1','FY2022 Q2']
    assert sum(x['minutes'] for x in out['records'])==29
    assert 'host_train_miles' not in out['records'][0]

def test_invalid_negative(tmp_path):
    import pytest
    with pytest.raises(ValueError,match='negative delay'):
        compile_delays(sample(tmp_path,'-1'))

def test_flask_without_publication(monkeypatch,tmp_path):
    import pytest
    pytest.importorskip("flask")
    from app import create_app, delay_service
    monkeypatch.setattr(delay_service,'DATA',tmp_path/'missing.json')
    delay_service._load.cache_clear()
    client=create_app({'TESTING':True}).test_client()
    assert client.get('/projects/intercity-rail/delays').status_code==200
    assert b'Delay data not published yet' in client.get('/projects/intercity-rail/delays').data
    assert client.get('/api/rail/delays').json['available'] is False
    assert client.get('/api/rail/delays/1').status_code==404
    delay_service._load.cache_clear()

def test_flask_with_publication(monkeypatch,tmp_path):
    import pytest
    pytest.importorskip("flask")
    from app import create_app, delay_service
    path=tmp_path/'fra_delays.json'
    path.write_text(json.dumps(compile_delays(sample(tmp_path))),encoding='utf8')
    monkeypatch.setattr(delay_service,'DATA',path)
    delay_service._load.cache_clear()
    client=create_app({'TESTING':True}).test_client()
    assert client.get('/projects/intercity-rail/delays').status_code==200
    overview=client.get('/api/rail/delays').json
    assert overview['available'] is True
    item=client.get('/api/rail/delays/'+overview['services'][0]['id']).json
    assert sum(x['minutes'] for x in item['trends'] if x['minutes'] is not None)==29
    assert sum(x['minutes'] for x in item['responsibilities'])==29
    assert sum(x['minutes'] for x in item['hosts'])==29
    assert sum(x['minutes'] for x in item['causes'])==29
    delay_service._load.cache_clear()
