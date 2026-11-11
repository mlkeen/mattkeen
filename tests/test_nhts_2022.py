import csv,io,json,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from publish_nhts_2022 import prepare
import pytest


def create_source(path):
    buf=io.StringIO();writer=csv.writer(buf)
    writer.writerow(['WTPERFIN','LONGDIST','LD_AMT','MAINMODE','PERSONID'])
    for i in range(1200):
        writer.writerow([2 if i%2 else 1,1 if i%2 else 2,1 if i%2 else 0,'13' if i%2 else '01',i])
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('nested/longdistance.csv',buf.getvalue())
        z.writestr('nested/trippub.csv','TRPMILES,WTTRDFIN\n10,1\n')


def test_survey_person_weighted(tmp_path):
    path=tmp_path/'official.zip';create_source(path)
    d=prepare(path)
    assert d['counts']['weight_valid']==1200
    assert d['annualized_long_distance_trips_per_person']==16.0
    assert abs(d['amtrak_uses_per_person_past_year']-2/3)<1e-5
    assert abs(d['fraction_persons_using_amtrak_past_year']-2/3)<1e-5
    assert abs(d['amtrak_share_of_most_recent_long_distance_trip']-2/3)<1e-5


def test_does_not_accept_wrong_file(tmp_path):
    p=tmp_path/'wrong.csv';p.write_text('TRPMILES,WTTRDFIN\n100,1\n')
    with pytest.raises(ValueError):prepare(p)


def test_rejects_tiny_sample(tmp_path):
    p=tmp_path/'tiny.csv';p.write_text('WTPERFIN,LONGDIST,LD_AMT,MAINMODE\n1,2,0,01\n')
    with pytest.raises(ValueError):prepare(p)
