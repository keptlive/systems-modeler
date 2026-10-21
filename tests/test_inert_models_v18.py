"""Independent source-form ODE checks for repaired inert teaching scaffolds."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from app.core.model import Model
from app.core.simulator import simulate
ROOT=Path(__file__).resolve().parents[1]
FILE="models/neuroscience/morris-lecar-neuron-neu.json"

def model():
    return Model.model_validate_json((ROOT/FILE).read_text())

def source_rhs(t,y):
    # Ermentrout XPP reduced equations use tanh/cosh. The app definition uses
    # algebraically equivalent logistic/exponential gates, not this oracle.
    v,w=y
    calcium=.5*(1+math.tanh((v+1.2)/18))
    potassium=.5*(1+math.tanh((v-2)/30))
    rate=.04*math.cosh((v-2)/60)
    return [(100+2*(-60-v)+8*w*(-84-v)+4.4*calcium*(120-v))/20,
            rate*(potassium-w)]

@pytest.fixture(scope="module")
def reference():
    result=solve_ivp(source_rhs,(0,400),[-60,0],method="DOP853",
                     rtol=1e-11,atol=1e-13,max_step=.1,dense_output=True)
    assert result.success
    return result

def test_morris_preserves_authored_inputs_and_adds_missing_dynamics():
    fixture=json.loads((ROOT/"tests/fixtures/corpus-baseline-v18-root.json").read_text())["models"][0]
    assert fixture["file"]==FILE
    assert hashlib.sha256(fixture["content"].encode()).hexdigest()==fixture["sha256"]
    before=json.loads(fixture["content"]);after=json.loads((ROOT/FILE).read_text())
    assert not before["flows"] and len(after["flows"])==2
    assert after["id"]==before["id"] and after["time_settings"]==before["time_settings"]
    for old,new in zip(before["stocks"],after["stocks"]):
        for key in old:assert old[key]==new[key]
    for old in before["variables"]:
        assert old==next(v for v in after["variables"] if v["id"]==old["id"])
    assert {f["to_stock"] for f in after["flows"]}=={"s1","s2"}

def test_morris_full_authored_horizon_has_real_spikes_and_bounded_gating(reference):
    result=simulate(model());v=np.array(result.values["Membrane_Potential"]);w=np.array(result.values["Potassium_Activation"])
    assert len(result.time)==40001
    assert v.min()>=-61 and v.max()>40
    assert np.sum((v[:-1]<0)&(v[1:]>=0))>=4
    assert w.min()>=0 and w.max()<=1
    expected=reference.sol(result.time)
    # Authored Euler dt=.01 has a measured .348mV phase error over400ms.
    assert np.max(np.abs(v-expected[0]))<.36
    assert np.max(np.abs(w-expected[1]))<.001

def test_morris_first_step_uses_the_published_signed_balances():
    m=model();result=simulate(m,m.time_settings.model_copy(update={"end":.01}))
    dv,dw=source_rhs(0,[-60,0])
    assert result.values["Membrane_Potential"][1]==pytest.approx(-60+.01*dv,abs=1e-12)
    assert result.values["Potassium_Activation"][1]==pytest.approx(.01*dw,abs=1e-12)

def test_morris_euler_converges_at_expected_order_against_independent_solver(reference):
    m=model();errors=[]
    for dt in [.01,.005,.0025]:
        result=simulate(m,m.time_settings.model_copy(update={"end":100,"dt":dt}))
        errors.append(float(np.max(np.abs(reference.sol(result.time)[0]-result.values["Membrane_Potential"]))))
    assert errors[0]<.051
    assert .45<errors[1]/errors[0]<.55
    assert .45<errors[2]/errors[1]<.55


def oregonator_rhs(t,state):
    x,y,z=state
    return [(.001*y-x*y+x-x*x)/.01,(-.001*y-x*y+z)/1.98e-5,x-z]

def test_oregonator_preserves_three_independent_states_and_declares_new_defaults():
    fixture=next(x for x in json.loads((ROOT/"tests/fixtures/corpus-baseline-v18-root.json").read_text())["models"] if 'oregonator' in x['file'])
    assert hashlib.sha256(fixture['content'].encode()).hexdigest()==fixture['sha256']
    old=json.loads(fixture['content']);new=json.loads((ROOT/fixture['file']).read_text())
    assert not old['flows'] and len(new['flows'])==3
    assert new['id']==old['id'] and new['connectors']==old['connectors']
    for before,after in zip(old['stocks'],new['stocks']):
        for key in before:assert before[key]==after[key]
    assert new['variables'][:3]==old['variables']
    assert new['time_settings']['integration_method']=='radau'
    assert new['time_settings']['end']==30 and old['time_settings']['end']==300
    assert new['time_settings']['dt']==old['time_settings']['dt']
    assert 'formerly300' in new['description'] or 'formerly 300' in new['description']
    assert 'budget' in new['description'] and 'not a calibrated' in new['description']

def test_oregonator_bounded_demonstration_matches_independent_bdf_reference():
    m=Model.model_validate_json((ROOT/'models/other/oregonator-bz-reaction-chem.json').read_text())
    result=simulate(m)
    reference=solve_ivp(oregonator_rhs,(0,30),[.01,.1,.01],method='BDF',rtol=1e-10,atol=1e-12,t_eval=result.time)
    assert reference.success and len(result.time)==3001
    values=np.array([result.values[name] for name in ['HBrO2','Bromide','Ce4_plus']])
    assert np.all(values>0)
    assert np.max(np.abs(values-reference.y)/(1+np.abs(reference.y)))<6e-6
    assert np.count_nonzero((values[0,:-1]<.5)&(values[0,1:]>=.5))>=6
    assert result.integration_diagnostics['work_units']<1000000
    # The positive orthant is forward invariant for positive parameters.
    assert oregonator_rhs(0,[0,.1,.01])[0]>=0
    assert oregonator_rhs(0,[.01,0,.01])[1]>=0
    assert oregonator_rhs(0,[.01,.1,0])[2]>=0
