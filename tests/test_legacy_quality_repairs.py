"""Independent reference checks for an isolated proposed legacy repair."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
from scipy.linalg import expm
from app.core.model import Model
from app.core.integration import evaluate
from app.core.simulator import simulate
from app.core.units import analyze_units
from app.core.validation import inspect_inputs
ROOT=Path(__file__).parents[1]
D=ROOT/'operations/legacy-quality-repairs'
def model():
    return Model(**json.loads((D/'world3-capital-fixed-allocation-proposed.json').read_text()))
def test_full_trajectory_against_exact_source_law_matrix_exponential():
    m=model();result=simulate(m)
    # Frozen source laws: output=capital*(1-resource fraction)*utilization/ratio;
    # investment=output*(1-service-agriculture-consumption), depreciation=capital/lifetime.
    productivity=.95/3
    matrix=np.array([[productivity*(1-.2-.1-.43)-1/14,0],[productivity*.2,-1/20]])
    initial=np.array([210e9,144e9]);times=np.asarray(result.time)-1900
    exact=np.column_stack([expm(matrix*t)@initial for t in times])
    values=np.array([result.values[s.name] for s in m.stocks])
    np.testing.assert_allclose(values,exact,rtol=2e-9,atol=.01)
    assert values[0,-1]/initial[0]<20
    assert inspect_inputs(m,numerical_check=False)['valid']
    assert analyze_units(m)['status']=='consistent'

def test_half_step_refinement_and_output_ratio_sensitivity():
    m=model();base=simulate(m);fine=m.model_copy(deep=True);fine.time_settings.dt/=2
    fr=simulate(fine)
    for s in m.stocks:np.testing.assert_allclose(base.values[s.name],fr.values[s.name][::2],rtol=2e-9,atol=.01)
    initial={s.name:s.initial_value for s in m.stocks}
    original=evaluate(m,initial,1900,.25,{},{});assert original['Industrial Output']==pytest.approx(210e9*.95/3)
    for v in m.variables:
        if v.name=='Industrial Capital Output Ratio':v.equation='6'
    changed=evaluate(m,initial,1900,.25,{},{});assert changed['Industrial Output']==pytest.approx(original['Industrial Output']/2)

def test_random_state_balances_against_independent_source_equations():
    m=model();rng=np.random.default_rng(221)
    for _ in range(100):
        industrial,service=rng.uniform(1e8,1e13,2)
        values=evaluate(m,{'Industrial Capital':industrial,'Service Capital':service},1950,.25,{},{})
        io=industrial*.95/3
        assert values['Industrial Output']==pytest.approx(io)
        assert values['Service Output']==pytest.approx(service/1)
        assert values['Industrial Investment']==pytest.approx(io*.27)
        assert values['Industrial Depreciation']==pytest.approx(industrial/14)
        assert values['Service Investment']==pytest.approx(io*.2)
        assert values['Service Depreciation']==pytest.approx(service/20)

def test_proposal_hash_and_honest_specialization_scope():
    receipt=json.loads((D/'PROPOSAL.json').read_text());row=receipt['proposed_replacement']
    assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256']
    m=model();assert m.id=='world3-capital-sector-cla'
    assert 'not the full World3' in m.description
    assert 'frozen' in m.description and 'no Limits to Growth' in m.description
    assert len(m.stocks)==2
