"""Reproducible error evidence independent of API transport or saved files."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from app.core.equations import EquationError
from app.core.model import Model, Stock, Flow, Variable, TimeSettings
from app.core.simulator import simulate, simulate_euler, simulate_rk4
from app.core.failure_diagnostics import failure_payload


def failing_model():
    return Model(id="failure-replay", stocks=[Stock(id="s",name="Amount",initial_value=2)],
        flows=[Flow(id="f",name="Outflow",equation="Broken",from_stock="s")],
        variables=[Variable(id="b",name="Broken",equation="IF(TIME < 1, 1, 1/0)")],
        time_settings=TimeSettings(start=0,end=2,dt=.5))


def failure(model,settings=None):
    with pytest.raises(EquationError) as caught:simulate(model,settings)
    return failure_payload(caught.value)


def test_late_error_keeps_causal_chain_and_exact_reproduction_context():
    m=failing_model();before=m.model_dump_json();p=failure(m)
    assert p['code']=='unresolved_equations' and p['time']==1
    assert any(x['element']=='Broken' for x in p['root_errors'])
    assert any(x['element']=='Outflow' and x['root_cause']['element']=='Broken' for x in p['blocked_errors'])
    replay=p['reproduction'];assert replay['settings']==m.time_settings.model_dump(mode='json')
    root=Path(__file__).resolve().parents[1]
    assert len(replay['normalized_model_sha256'])==64
    assert 'app/core/reports.py' in replay['engine_sha256']
    for path,digest in replay['engine_sha256'].items():
        assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest
    assert json.loads(json.dumps(p,allow_nan=False))==p
    assert m.model_dump_json()==before


def test_timestamp_independent_model_identity_and_override_identity():
    m=failing_model();first=failure(m)['reproduction']
    m.created_at=datetime(2001,1,1,tzinfo=timezone.utc);m.updated_at=m.created_at
    override=TimeSettings(start=0,end=3,dt=.25,integration_method='rk4')
    second=failure(m,override)['reproduction']
    assert second['normalized_model_sha256']==first['normalized_model_sha256']
    assert second['settings']==override.model_dump(mode='json')
    m.variables[0].equation='IF(TIME < 1, 2, 1/0)'
    assert failure(m)['reproduction']['normalized_model_sha256']!=first['normalized_model_sha256']


@pytest.mark.parametrize('entry,method',[(simulate_euler,'euler'),(simulate_rk4,'rk4')])
def test_explicit_solver_entrypoints_preserve_error_evidence(entry,method):
    m=failing_model()
    with pytest.raises(EquationError) as caught:entry(m)
    assert caught.value.details['reproduction']['settings']['integration_method']==method


def test_report_failure_has_same_reproduction_evidence():
    m=Model(variables=[Variable(id='r',name='Report',role='report',equation="IF(TIME < 1, 'Fine', 1/0)")],
            time_settings=TimeSettings(end=2,dt=.5))
    p=failure(m)
    assert p['code']=='invalid_report' and p['time']==1 and p['element']=='Report'
    assert p['reproduction']['settings']['end']==2


def test_secondary_metadata_failure_does_not_replace_actual_error(monkeypatch):
    import app.core.diagnostics as diagnostics
    def unavailable():raise OSError('unavailable source metadata')
    monkeypatch.setattr(diagnostics,'source_hashes',unavailable)
    p=failure(failing_model())
    assert p['code']=='unresolved_equations' and p['reproduction']=={'status':'unavailable'}


def test_escaped_report_labels_cannot_create_invalid_unicode_after_input_validation():
    m=Model(variables=[Variable(name='Status',role='report',equation="'\\ud800'")],
            time_settings=TimeSettings(end=1,dt=1))
    # The input equation is valid UTF-8; its AST string value is not.
    m.model_dump_json().encode('utf8')
    p=failure(m)
    assert p['code']=='invalid_report' and 'Unicode scalar' in p['message']
    m.variables[0].equation="'\\U0001f680 成功'"
    assert simulate(m).report_values['Status']==['🚀 成功','🚀 成功']
