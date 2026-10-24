"""Source-backed v1.4 restorations; offline independent mathematical checks.

SDMR source commit89bbfe65c25db5bcca511c10ef6527c8ebe35696.
Cookbook commitd7ebddadad9cd87cf796b9b6031ea2b5c45da4c4.
These verify the supplied examples, not empirical calibration.
"""
import json
import math
from pathlib import Path

import pytest

from app.core.model import Model
from app.core.simulator import simulate

ROOT=Path(__file__).resolve().parents[1]


def load(name):
    return Model.model_validate_json((ROOT/f"models/other/{name}.json").read_text())


# Independent SciPy DOP853 integration of source equations, rtol=atol=1e-12.
# Columns: time,Ia,Iy,Ra,Ry,Sa,Smoothed_Reporting_Rate,Sy. No app engine used
# to generate these eight reference points; the source controls no closure feedback.
SCHOOL_REFERENCE = [
    [0,0,1,0,0,5000,0,4999],
    [10,4.029448917900989,5.4836184970355015,6.932272591331383,12.175473394844929,4989.038278490768,1.9012658935910922,4982.340908108121],
    [20,35.815327640799715,44.25359666712831,81.34420293167224,105.7286154544806,4882.840469427529,16.01377578159965,4850.0177878783925],
    [30,185.35089760524272,217.4410171812432,575.1721873479718,699.2752486730316,4239.476915046786,80.55838289611677,4083.2837341457275],
    [40,207.6440945826219,218.9143636974514,1718.8919285905251,1972.2987530609566,3073.463976826854,85.31169165560243,2808.7868832415934],
    [50,63.407664245696935,62.11759022652066,2365.6066853061766,2631.183540182999,2570.9856504481268,25.105050894440737,2306.698869590482],
    [60,12.981262324322579,12.356134589560599,2526.7612723076954,2786.989587999847,2460.2574653679817,5.067479382776618,2200.654277410593],
    [70,2.4400412292970843,2.3008172827465216,2558.381069223925,2816.956640237528,2439.178889546778,0.9481717024087211,2180.742542479727],
]


def test_school_epidemic_and_reporting_dynamics_restored_at_source_defaults():
    model=load('school-closure-initial-model')
    run=simulate(model)
    assert len(run.time)==561 and run.time[-1]==70
    assert run.values['Ia'][1] == pytest.approx(.1375*.125)
    assert run.values['Iy'][1] == pytest.approx(1+(.6/5000*4999-.5)*.125)
    assert run.values['Ia'][-1] > 0 and run.values['Smoothed_Reporting_Rate'][-1] > 0
    assert max(run.values['Close_Schools_Flag'])==1
    for i in range(len(run.time)):
        assert run.values['Ia'][i]+run.values['Ra'][i]+run.values['Sa'][i] == pytest.approx(5000,abs=1e-8)
        assert run.values['Iy'][i]+run.values['Ry'][i]+run.values['Sy'][i] == pytest.approx(5000,abs=1e-8)
    expected={'ARR':('v1','Ia','Ra'),'CRR':('v13',None,'Smoothed_Reporting_Rate'),
              'YIR':('v25','Sy','Iy'),'YRR':('v26','Iy','Ry'),'AIR':('f3','Sa','Ia')}
    for flow in model.flows:
        if flow.name in expected:
            assert (flow.id,flow.from_stock,flow.to_stock)==expected[flow.name]
    # The two original reporting flows remain diagnostic and retain identity.
    assert next(f for f in model.flows if f.name=='Reported_Infection_Rate').id=='f1'
    assert next(f for f in model.flows if f.name=='Total_Infection_Rate').id=='f2'


def test_school_refined_rk4_matches_independent_reference_points():
    model=load('school-closure-initial-model')
    settings=model.time_settings.model_copy(update={'integration_method':'rk4','dt':.0625})
    run=simulate(model,settings)
    names=['Ia','Iy','Ra','Ry','Sa','Smoothed_Reporting_Rate','Sy']
    for row in SCHOOL_REFERENCE:
        index=round(row[0]/settings.dt)
        assert run.time[index]==row[0]
        for name,expected in zip(names,row[1:]):
            assert abs(run.values[name][index]-expected)/5000 < 1e-9


def test_school_source_flag_is_diagnostic_without_invented_closure_intervention():
    model=load('school-closure-initial-model')
    baseline=simulate(model)
    changed=model.model_copy(deep=True)
    next(v for v in changed.variables if v.name=='School_Closure_Threshold').equation='0'
    altered=simulate(changed)
    assert altered.values['Close_Schools_Flag']!=baseline.values['Close_Schools_Flag']
    for name in ('Ia','Iy','Ra','Ry','Sa','Sy','CE_YY'):
        assert altered.values[name]==baseline.values[name]


def test_solow_default_flow_balance_and_refinement_match_closed_form():
    model=load('solow')
    baseline=simulate(model)
    assert baseline.values['Machines'][1]==pytest.approx(123.75)
    assert baseline.values['Machines'][-1]>39000
    assert next(f for f in model.flows if f.name=='Investment').id=='v3'
    settings=model.time_settings.model_copy(update={'integration_method':'rk4','dt':.03125})
    run=simulate(model,settings)
    # For K'=20*sqrt(K)-.1*K, u=sqrt(K) solves u'=10-.05*u.
    for time,value in zip(run.time,run.values['Machines']):
        expected=(200-190*math.exp(-.05*time))**2
        assert abs(value-expected)/40000 < 2e-8
    for name in ('Labour','Depreciation_Fraction','Reinvestment_Fraction'):
        assert run.values[name][0]==baseline.values[name][0]


def test_atmospheric_default_stays_zero_but_missing_dynamics_are_restored():
    model=load('atmospheric-bathtub')
    baseline=simulate(model)
    assert all(value==0 for value in baseline.values['Excess_Atmospheric_Carbon'])
    assert next(f for f in model.flows if f.name=='Natural_Removal').id=='v1'
    scenario=model.model_copy(deep=True)
    scenario.stocks[0].initial_value=100
    decaying=simulate(scenario)
    for step,value in enumerate(decaying.values['Excess_Atmospheric_Carbon']):
        assert value==pytest.approx(100*.99**step,abs=1e-10)
    # Explicit unsaved scenario: original zero-emissions baseline is preserved.
    next(f for f in scenario.flows if f.name=='Emissions').equation='10'
    growing=simulate(scenario)
    for step,value in enumerate(growing.values['Excess_Atmospheric_Carbon']):
        assert value==pytest.approx(1000+(100-1000)*.99**step,abs=1e-9)
    rk4=simulate(scenario,scenario.time_settings.model_copy(update={'integration_method':'rk4'}))
    for time,value in zip(rk4.time,rk4.values['Excess_Atmospheric_Carbon']):
        assert value==pytest.approx(1000+(100-1000)*math.exp(-.01*time),abs=1e-6)
    assert next(f for f in model.flows if f.name=='Emissions').equation=='0'


def test_full_beer_is_preserved_until_the_source_ambiguity_is_resolved():
    import hashlib
    from tests.model_history import v17_bytes
    raw=v17_bytes(ROOT,'models/other/full-beer-model.json')
    assert hashlib.sha256(raw).hexdigest()=='9e9b203c19351c67d1c5f7aa155198a36b7e48994ca9c713b106ee63824f5452'
