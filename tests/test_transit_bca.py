import pytest
from app.bca_engine import analyze,scenarios,DEFAULTS

def test_zero_project():
    d={**DEFAULTS,**{k:0 for k in ('capital_cost','annual_incremental_om','affected_existing_trips','diverted_trips','generated_trips','annual_safety_benefit','annual_air_quality_benefit','annual_other_benefit')}}
    result=analyze(d)
    assert result['npv']==0 and result['bcr'] is None

def test_zero_discount_exact_arithmetic():
    d={**DEFAULTS,'discount_rate':0,'construction_years':1,'operating_years':1,'capital_cost':100,'annual_incremental_om':10,'affected_existing_trips':60,'diverted_trips':0,'generated_trips':0,'time_saved_minutes':60,'value_of_time':2,'annual_safety_benefit':0,'annual_air_quality_benefit':0,'annual_other_benefit':0,'annual_residual_value':0,'benefit_ramp_years':1}
    r=analyze(d)
    assert r['pv_costs']==110
    assert r['pv_benefits']==120
    assert r['npv']==10
    assert r['bcr']==pytest.approx(120/110)
    assert len(r['years'])==2

def test_discount_and_generated_half_rule():
    d={**DEFAULTS,'construction_years':1,'operating_years':1,'discount_rate':10,'capital_cost':0,'annual_incremental_om':0,'affected_existing_trips':0,'diverted_trips':0,'generated_trips':100,'time_saved_minutes':60,'value_of_time':10,'annual_safety_benefit':0,'annual_air_quality_benefit':0,'annual_other_benefit':0}
    r=analyze(d)
    assert r['pv_benefits']==pytest.approx(500/1.1)

def test_reject_negative_denominators():
    with pytest.raises(ValueError):analyze({'annual_incremental_om':-1})
    with pytest.raises(ValueError):analyze({'construction_years':0})

def test_sensitivity_cases():
    s=scenarios(DEFAULTS)
    assert len(s)==4
    assert s[1]['npv']<s[0]['npv']
