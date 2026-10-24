import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.model import Model, Stock, Flow, TimeSettings
from app.core.simulator import simulate
from app.core.equations import EquationError
from app.core.diagnostics import investigate_model
from app.core.xmile_generator import generate_xmile


def recurrence():
    return Model(stocks=[Stock(id='x',name='Balance',initial_value=8)],
                 flows=[Flow(name='Change',equation='Balance*.5-Balance',to_stock='x')],
                 time_settings=TimeSettings(start=0,end=3,dt=1,discrete_period=1))


def test_exact_recurrence_and_no_refinement():
    result=simulate(recurrence())
    assert result.values['Balance']==[8,4,2,1]
    report=investigate_model(recurrence())
    assert [r['status'] for r in report['runs']]==['completed','not_attempted','not_attempted']
    assert report['timestep_assessment']['status']=='inapplicable_for_discrete_period'


@pytest.mark.parametrize('changes',[{'dt':.5},{'integration_method':'rk4'},{'integration_method':'radau'},{'end':2.5}])
def test_discrete_contract_cannot_be_removed_by_override(changes):
    model=recurrence()
    settings=TimeSettings(**{**model.time_settings.model_dump(),'discrete_period':None,**changes})
    with pytest.raises(EquationError,match='Discrete'):simulate(model,settings)
    client=TestClient(app)
    for path in ['/api/simulate','/api/validate','/api/investigate']:
        response=client.post(path,json={'model':model.model_dump(mode='json'),'time_settings':settings.model_dump(mode='json')})
        assert response.status_code==422,(path,response.text)


def test_discrete_settings_and_export_are_explicit():
    with pytest.raises(ValueError):TimeSettings(end=3,dt=.5,discrete_period=1)
    with pytest.raises(ValueError):TimeSettings(end=3.5,dt=1,discrete_period=1)
    with pytest.raises(ValueError,match='JSON'):generate_xmile(recurrence())
    assert Model.model_validate_json(recurrence().model_dump_json()).time_settings.discrete_period==1
