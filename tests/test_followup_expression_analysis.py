"""New pure expressions retain units and dependency semantics."""
from copy import deepcopy
import pytest
from app.core.model import Model
from app.core.simulator import simulate
from app.core.execution_order import derive_execution_order
from app.core.units import analyze_units
import app.core.integration as integration

@pytest.mark.parametrize('expression', [
    'ARCSIN(input)', 'ARCCOS(input)', 'ARCTAN(input)', 'INT(input)',
    'TRUNC(input)', 'QUANTUM(input, .2)', 'SAFEDIV(input, 2, 7)',
    'ZIDZ(input, 2)', 'XIDZ(input, 2, 7)', 'MODULO(input, .3)', 'REM(input, .3)',
])
def test_new_pure_dependencies_match_fallback(expression, monkeypatch):
    model = Model(variables=[{'name':'output','equation':expression},
        {'name':'input','equation':'.5'}], time_settings={'end':1,'dt':.25})
    before = deepcopy(model.model_dump())
    assert [name for name, _ in derive_execution_order(model)] == ['input','output']
    planned = simulate(model)
    monkeypatch.setattr(integration, 'derive_execution_order', lambda *a, **kw: None)
    fallback = simulate(model)
    assert planned.time == fallback.time and planned.values == fallback.values
    assert model.model_dump() == before

@pytest.mark.parametrize('rhs, expected', [('3','consistent'), ('seconds','inconsistent')])
def test_rem_units_match_remainder_arguments(rhs, expected):
    model = Model(variables=[{'name':'distance','equation':'10','units':'meter'},
        {'name':'seconds','equation':'3','units':'second'},
        {'name':'output','equation':f'REM(distance, {rhs})','units':'meter'}])
    assert analyze_units(model, time_units='second')['status'] == expected

def test_vensim_ramp_dimensional_contract():
    model = Model(variables=[{'name':'slope','equation':'2','units':'meter/second'},
        {'name':'begin','equation':'1','units':'second'},
        {'name':'finish','equation':'3','units':'second'},
        {'name':'output','equation':'RAMP_VENSIM(slope,begin,finish)','units':'meter'}])
    assert analyze_units(model, time_units='second')['status'] == 'consistent'
