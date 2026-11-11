import csv
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('publisher',ROOT/'scripts/publish_financials.py')
publisher=importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)

def make_csv(path, header, data):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=header)
        w.writeheader(); w.writerows(data)

def test_publisher_flags_and_preserves_provenance(tmp_path):
    shared={'fiscal_year':'2026','fiscal_quarter':'3','apt_code':'APT_RT_1','route':'Sample Route','reporting_level':'route',
            'source_workbook':'source.xlsx','source_sheet':'Cost Recovery','source_excel_row':'12'}
    make_csv(tmp_path/'cost_recovery.csv',list(shared)+['operating_revenue','allocated_expense','cost_recovery'],[
        {**shared,'operating_revenue':'50','allocated_expense':'100','cost_recovery':'.5'},
        {**shared,'fiscal_quarter':'2','allocated_expense':'-1','operating_revenue':'50','cost_recovery':'-50'},
        {**shared,'fiscal_quarter':'1','allocated_expense':'0','operating_revenue':'50','cost_recovery':''},
    ])
    for table, expense,coverage in [('avoidable_expense','avoidable_expense','avoidable_expense_coverage'),('fully_allocated_expense','allocated_expense','allocated_expense_coverage')]:
        make_csv(tmp_path/f'{table}.csv',list(shared)+['state_payments_included','passenger_revenue',expense,coverage],[
            {**shared,'state_payments_included':'False','passenger_revenue':'30',expense:'100',coverage:'.3'},
            {**shared,'state_payments_included':'True','passenger_revenue':'40',expense:'100',coverage:'.4'},
        ])
    result=publisher.compile_financials(tmp_path)
    assert len(result['records'])==7
    assert result['status_counts']=={'valid':5,'negative_expense':1,'zero_expense':1}
    negative=[r for r in result['records'] if r['status']=='negative_expense'][0]
    assert negative['ratio'] is None and negative['ratio_source']==-50.0
    assert negative['source_excel_row']=='12'
    assert {r['state_payments_included'] for r in result['records'] if r['measure']=='avoidable_expense'}=={True,False}
    assert json.dumps(result,allow_nan=False)

def test_reject_duplicate_keys(tmp_path):
    shared={'fiscal_year':'2026','fiscal_quarter':'3','apt_code':'APT_RT_1','route':'Sample Route','reporting_level':'route',
            'source_workbook':'source.xlsx','source_sheet':'Cost Recovery','source_excel_row':'12',
            'operating_revenue':'50','allocated_expense':'100','cost_recovery':'.5'}
    make_csv(tmp_path/'cost_recovery.csv',list(shared),[shared,shared])
    for table, expense,coverage in [('avoidable_expense','avoidable_expense','avoidable_expense_coverage'),('fully_allocated_expense','allocated_expense','allocated_expense_coverage')]:
        make_csv(tmp_path/f'{table}.csv',list(shared)+['state_payments_included','passenger_revenue',expense,coverage],[])
    try: publisher.compile_financials(tmp_path)
    except ValueError as e:assert 'duplicate' in str(e)
    else:assert False,'expected duplicate detection'
