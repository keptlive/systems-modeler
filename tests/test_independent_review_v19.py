"""Independent counterexamples for v1.9 report isolation and recurrence contracts."""
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.equations import EquationError
from app.core.model import Flow, LookupTable, Model, Stock, TimeSettings, Variable
from app.core.simulator import simulate
from app.core.validation import inspect_inputs
from app.main import app
from app.storage import workspaces


def recurrence(period=1, end=3):
    return Model(stocks=[Stock(id='s',name='Balance',initial_value=8)],
                 flows=[Flow(id='f',name='Change',equation='-.5*Balance',to_stock='s')],
                 variables=[Variable(id='v',name='Status',equation="IF(Balance>2,'High','Low')",role='report')],
                 time_settings=TimeSettings(start=0,end=end,dt=period,discrete_period=period))


@pytest.mark.parametrize('change',[{'dt':.5},{'integration_method':'rk4'},{'integration_method':'radau'},{'end':2.5}])
def test_mcp_preserves_original_recurrence_contract(change):
    from app.mcp_server import simulate_model
    kwargs={'dt':change['dt']} if 'dt' in change else {'end_time':change['end']} if 'end' in change else change
    with pytest.raises((ValueError,EquationError)):
        simulate_model(model_json=recurrence().model_dump(mode='json'),**kwargs)


def test_workspace_targeted_settings_cannot_erase_period_and_failure_is_atomic():
    from app.mcp_server import WorkspaceElementEdit, edit_workspace_elements
    m=recurrence();opened=workspaces.create(m.model_dump(mode='json'));key=opened['workspace_key']
    edit=WorkspaceElementEdit(element_type='stock',element_id='s',changes={'initial_value':99})
    try:
        # Omitting the declaration in an override must not remove it.
        with pytest.raises((ValueError,EquationError)):
            edit_workspace_elements(key,[edit],1,TimeSettings(start=0,end=3,dt=.5))
        state=workspaces.snapshot(key)
        assert state['revision']==1 and state['model']['stocks'][0]['initial_value']==8
        assert state['model']['time_settings']['discrete_period']==1
        # Even an explicit null in targeted timing settings retains the original contract.
        with pytest.raises((ValueError,EquationError)):
            workspaces.edit_elements(key,[edit.model_dump()],1,{'start':0,'end':3,'dt':.5,'discrete_period':None})
    finally:
        workspaces.close(key)


def test_workspace_valid_timing_update_preserves_period_report_role_and_exact_results():
    from app.mcp_server import WorkspaceElementEdit,edit_workspace_elements,run_workspace
    opened=workspaces.create(recurrence().model_dump(mode='json'));key=opened['workspace_key']
    try:
        edit=WorkspaceElementEdit(element_type='variable',element_id='v',changes={'role':'report','equation':"IF(Balance>=2,'Ready','Done')"})
        changed=edit_workspace_elements(key,[edit],1,TimeSettings(start=0,end=4,dt=1))
        assert changed['model']['time_settings']['discrete_period']==1
        assert changed['model']['variables'][0]['role']=='report'
        run_workspace(key,changed['revision'])
        saved=workspaces.snapshot(key,include_result=True)['result']
        assert saved['values']['Balance']==[8,4,2,1,.5]
        assert saved['report_values']['Status']==['Ready','Ready','Ready','Done','Done']
        assert 'Status' not in saved['values']
    finally:
        workspaces.close(key)


def test_discrete_completion_tolerance_must_not_create_an_extra_partial_recurrence():
    # The whole-period check historically accepted this while ceil(x-1e-10)
    # generated four updates. Rejection or exactly three updates is valid.
    try:
        result=simulate(recurrence(end=3.0000000005))
    except (ValueError,EquationError):
        return
    assert len(result.time)==4
    assert np.allclose(np.diff(result.time),1,atol=1e-9,rtol=0)


@pytest.mark.parametrize('start',[0,1000,2000])
def test_decimal_period_is_exact_and_invariant_under_time_translation(start):
    m=Model(stocks=[Stock(id='s',name='Balance',initial_value=8)],
            flows=[Flow(name='Change',equation='-.5*Balance/.1',to_stock='s')],
            variables=[Variable(name='Saved',equation='Balance',role='report')],
            time_settings=TimeSettings(start=start,end=start+.3,dt=.1,discrete_period=.1))
    result=simulate(m)
    assert len(result.time)==4
    assert result.values['Balance']==[8,4,2,1]
    assert result.report_values['Saved']==[8,4,2,1]
    assert result.integration_diagnostics['report_evaluations']==4


@pytest.mark.parametrize('method',['euler','rk4','radau'])
def test_reports_cannot_change_numeric_trajectories_or_read_other_reports(method):
    m=Model(stocks=[Stock(id='s',name='Amount',initial_value=2)],
            flows=[Flow(name='Decay',equation='Amount',from_stock='s')],
            time_settings=TimeSettings(start=0,end=2,dt=.25,integration_method=method))
    expected=simulate(m)
    m.variables=[Variable(name='Run Status',role='report',equation="IF(TIME < 1, 'Early', Amount)")]
    result=simulate(m)
    assert result.values==expected.values
    assert result.report_values['Run Status'][:4]==['Early']*4
    for expression in ['Run_Status','"Run Status"','IF(0,Run_Status,1)']:
        m.variables.append(Variable(name='Other',role='report',equation=expression))
        with pytest.raises(EquationError,match='cannot feed'):
            simulate(m)
        m.variables.pop()


def test_stochastic_numeric_inputs_keep_identical_seeded_stream_with_reports():
    m=Model(stocks=[Stock(id='s',name='Count',initial_value=0)],
            flows=[Flow(name='Draw',equation='RANDOM_BINOMIAL(10,.3)',to_stock='s')],
            time_settings=TimeSettings(start=0,end=10,dt=1,random_seed=42))
    baseline=simulate(m)
    m.variables.append(Variable(name='Result',role='report',equation="IF(Count>5,'Large','Small')"))
    result=simulate(m)
    assert result.values==baseline.values and result.random_seed==42
    assert result.integration_diagnostics['report_evaluations']==11


def test_report_table_precedence_and_all_branch_validation():
    m=Model(variables=[Variable(name='Text',role='report',equation="IF(LOOKUP('Curve',TIME)>1,'Above','Below')")],
            tables=[LookupTable(name='Curve',points=[(0,0),(2,2)])],
            time_settings=TimeSettings(start=0,end=2,dt=1))
    assert simulate(m).report_values['Text']==['Below','Below','Above']
    m.variables[0].equation="IF(1,'Fine',RANDOM_BINOMIAL(1,.5))"
    assert not inspect_inputs(m,numerical_check=False)['valid']
    response=TestClient(app).post('/api/simulate',json={'model':m.model_dump(mode='json')})
    assert response.status_code==422


def test_text_capacity_and_report_work_are_reserved_before_numeric_integration(monkeypatch):
    import app.core.integration as integration
    # Verify preflight: an intentionally invalid stock equation must not run
    # before a known report-capacity rejection.
    m=Model(stocks=[Stock(id='s',name='Bad',equation='1/0')],
            variables=[Variable(name='Label',role='report',equation=repr('x'*512))],
            time_settings=TimeSettings(start=0,end=2000,dt=1))
    with pytest.raises(EquationError,match='retained text characters'):
        simulate(m)
    m.variables[0].equation="'x'"
    monkeypatch.setattr(integration,'MAX_WORK_UNITS',100)
    with pytest.raises(EquationError,match='Reports exceed work budget'):
        simulate(m)


def test_report_ui_escapes_untrusted_names_and_labels():
    # The actual browser tests belong to root; this verifies the security-sensitive
    # rendering path used by both desktop and mobile wrappers.
    from pathlib import Path
    code=(Path(__file__).resolve().parents[1]/'static/js/simulation.js').read_text()
    method=code.split('reportHTML(results)',1)[1].split('displayResults()',1)[0]
    assert 'App.escapeHtml(name)' in method
    assert 'App.escapeHtml(String(values[values.length - 1]' in method
