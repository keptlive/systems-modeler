import json
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from app.core.model import Model, Stock, Flow, Variable, TimeSettings
from app.core.simulator import simulate
from app.core.equations import EquationError
from app.core.validation import inspect_inputs
from app.core.xmile_generator import generate_xmile


def example(method="euler"):
    return Model(stocks=[Stock(id="s", name="Inventory", initial_value=0)],
        flows=[Flow(name="Arrival", equation="1", to_stock="s")],
        variables=[Variable(name="Status", role="report", equation="IF(Inventory < .75, 'Empty', IF(Inventory < 1.75, 'Filling', 'Full'))")],
        time_settings=TimeSettings(start=0,end=2,dt=.5,integration_method=method))


@pytest.mark.parametrize("method", ["euler", "rk4", "radau"])
def test_reports_are_separate_and_do_not_change_dynamics(method):
    model=example(method);result=simulate(model)
    numeric=model.model_copy(update={"variables": []})
    baseline=simulate(numeric)
    assert result.values==baseline.values
    assert result.report_values=={"Status": ["Empty", "Empty", "Filling", "Filling", "Full"]}
    assert result.integration_diagnostics["report_evaluations"]==5
    assert inspect_inputs(model)["valid"]
    assert Model.model_validate_json(model.model_dump_json()).variables[0].role=="report"


@pytest.mark.parametrize("equation", ["Status", "IF(1, 1, Status)", '\"Status\" + 2'])
def test_no_feedback_even_in_inactive_branch(equation):
    model=example();model.flows[0].equation=equation
    with pytest.raises(EquationError,match="cannot feed"):
        simulate(model)
    assert not inspect_inputs(model,numerical_check=False)["valid"]


@pytest.mark.parametrize("equation", ["IF(1, 'ok', RANDOM_UNIFORM(0,1))", "IF(1,'ok',SMOOTH(1,2))", "IF('bad',1,2)", "'x' + 'y'", "IF(0, 'a' * 100, 'ok')"])
def test_invalid_report_expressions_rejected_all_branches(equation):
    model=example();model.variables[0].equation=equation
    with pytest.raises(EquationError):simulate(model)


def test_lazy_numeric_branch_and_nonfinite_rejection():
    model=example();model.variables[0].equation="IF(Inventory = 0, 'At rest', 1/Inventory)"
    assert simulate(model).report_values['Status']==['At rest',2,1,2/3,.5]
    model.variables[0].equation='1e309'
    with pytest.raises(EquationError,match='finite'):simulate(model)


def test_report_names_are_not_available_to_other_reports():
    model=example();model.variables.append(Variable(name='Other',role='report',equation='Status'))
    with pytest.raises(EquationError,match='cannot feed'):simulate(model)


def test_time_switch_report_does_not_create_radau_rhs_switch():
    model=example('radau');model.variables[0].equation="IF(TIME < 1, 'Early', 'Late')"
    assert simulate(model).report_values['Status']==['Early','Early','Late','Late','Late']


def test_report_limits_and_names():
    model=example();model.variables[0].equation=repr('a'*513)
    with pytest.raises(EquationError,match='512'):simulate(model)
    model.variables[0].equation=repr('a'*512);model.time_settings=TimeSettings(end=100,dt=.01)
    with pytest.raises(EquationError,match='text characters'):simulate(model)
    model=example();model.variables[0].name='Inventory'
    with pytest.raises(EquationError,match='unique'):simulate(model)


def test_numeric_auxiliaries_still_reject_text_and_xmile_is_explicit():
    model=example();model.variables[0].role='auxiliary'
    with pytest.raises(EquationError):simulate(model)
    with pytest.raises(ValueError,match='JSON'):generate_xmile(example())


def test_limits_growth_preserves_original_status_and_independent_rhs():
    root=Path(__file__).resolve().parents[1]
    model=Model.model_validate_json((root/'models/education/limits-to-growth-system-archetype-edu.json').read_text())
    report=next(v for v in model.variables if v.name=='System State')
    assert report.role=='report'
    assert report.equation=="IF(Limiting_Effect < 0.5, 'Growing', IF(Limiting_Effect < 0.9, 'Constrained', 'At Limit'))"
    def rhs(t,y):
        p,c=y;effect=min(1,c/500)
        return [.1*p*(1-effect)-.05*p*effect,.01*p-.02*c]
    result=simulate(model)
    reference=solve_ivp(rhs,(0,100),[100,0],method='DOP853',rtol=1e-11,atol=1e-12,dense_output=True)
    errors=[]
    for dt in [1,.5,.25]:
        out=simulate(model,model.time_settings.model_copy(update={'dt':dt}))
        expected=reference.sol(out.time)
        errors.append(max(np.max(np.abs(np.array(out.values[n])-expected[i])) for i,n in enumerate(['Performance','Limiting Condition'])))
        assert min(out.values['Performance'])>0
        assert min(out.values['Limiting Condition'])>=0
        assert out.report_values['System State']==['Growing' if c/500<.5 else 'Constrained' if c/500<.9 else 'At Limit' for c in out.values['Limiting Condition']]
    assert errors[1]<errors[0]*.6 and errors[2]<errors[1]*.6


def test_report_rest_and_mcp_contract():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.mcp_server import simulate_model
    model=example()
    response=TestClient(app).post('/api/simulate',json={'model':model.model_dump(mode='json')})
    assert response.status_code==200
    assert response.json()['report_values']['Status'][-1]=='Full'
    assert 'Status' not in response.json()['values']
    output=simulate_model(model_json=model.model_dump(mode="json"),max_points=3)
    assert output['report_values']['Status']==['Empty','Filling','Full']
    assert 'Status' not in output['summary'] and 'Status' not in output['data']
