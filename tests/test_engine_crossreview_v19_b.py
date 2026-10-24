"""Independent boundary and continuity-certificate counterexamples."""
import json
import math
import random

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import simulate as api
from app.core.adaptive import state_discontinuities
from app.core.equations import EquationError, safe_eval
from app.core.failure_diagnostics import failure_payload
from app.core.model import Model, SimulationRequest
from app.core.simulator import simulate


def conditional_model(expression):
    return Model(stocks=[{'id':'x','name':'X','initial_value':1}],
                 flows=[{'name':'Change','equation':expression,'to_stock':'x'}],
                 time_settings={'end':2,'dt':.1,'integration_method':'radau'})


@pytest.mark.parametrize('expression,boundary,left,right',[
    ('IF(X > LOG(100), X, 2)',math.log(100),2,math.log(100)),
    ('IF(X>0,IF(2<1<1,1,0),0)',0,0,1),
    ('IF(X>0,IF(2=1<1,0,1),0)',0,0,1),
])
def test_algebraic_certificate_cannot_change_function_or_comparison_semantics(expression,boundary,left,right):
    # Establish the actual one-sided limits independently of the certificate.
    epsilon=1e-8
    assert safe_eval(expression,{'X':boundary-epsilon})==pytest.approx(left,abs=epsilon*2)
    assert safe_eval(expression,{'X':boundary+epsilon})==pytest.approx(right,abs=epsilon*2)
    assert abs(left-right)>.5
    model=conditional_model(expression)
    assert state_discontinuities(model)
    with pytest.raises(EquationError) as error:simulate(model)
    assert error.value.code=='unsupported_method_features'


def test_report_stage_failure_records_generated_stochastic_seed(monkeypatch):
    monkeypatch.setattr(random.SystemRandom,'randrange',lambda *args,**kwargs:987654)
    model=Model(variables=[{'name':'Noise','equation':'RANDOM(0,1)'},
                           {'name':'Status','role':'report','equation':"IF(TIME<1, 'OK', 1/0)"}],
                time_settings={'end':2,'dt':1})
    with pytest.raises(EquationError) as error:simulate(model)
    failure=failure_payload(error.value)
    assert failure['code']=='invalid_report' and failure['time']==1
    assert failure['reproduction']['settings']['random_seed']==987654
    json.dumps(failure,allow_nan=False)


@pytest.mark.parametrize('patch,expected_seed',[({},0),({'dt':.5},0),({'random_seed':None},54321),({'random_seed':7},7)])
def test_partial_override_distinguishes_omitted_zero_and_null_seed(patch,expected_seed,monkeypatch):
    monkeypatch.setattr(random.SystemRandom,'randrange',lambda *args,**kwargs:54321)
    model=Model(variables=[{'name':'Noise','equation':'RANDOM(0,1)'}],
                time_settings={'start':4,'end':6,'dt':1,'random_seed':0,'rtol':1e-8,'atol':1e-12})
    request=SimulationRequest.model_validate({'model':model.model_dump(mode='json'),'time_settings':patch})
    settings=request.time_settings.apply_to(model.time_settings)
    assert settings.start==4 and settings.end==6 and settings.rtol==1e-8 and settings.atol==1e-12
    direct=simulate(model,settings)
    assert direct.random_seed==expected_seed
    app=FastAPI();app.include_router(api.router,prefix='/api')
    result=TestClient(app).post('/api/simulate',json={'model':model.model_dump(mode='json'),'time_settings':patch})
    assert result.status_code==200,result.text
    assert result.json()==direct.model_dump(mode='json')


@pytest.mark.parametrize('method',['euler','rk4','radau'])
def test_actual_overflow_failure_payload_serializes_as_finite_json(method):
    model=Model(stocks=[{'id':'x','name':'X','initial_value':1e308}],
                flows=[{'name':'Growth','equation':'1e308','to_stock':'x'}],
                time_settings={'end':2,'dt':1,'integration_method':method})
    with pytest.raises((EquationError,ValueError,ArithmeticError)) as error:simulate(model)
    payload=failure_payload(error.value)
    json.dumps(payload,allow_nan=False)
    app=FastAPI();app.include_router(api.router,prefix='/api')
    result=TestClient(app).post('/api/simulate',json={'model':model.model_dump(mode='json')})
    assert result.status_code==422,result.text
    json.dumps(result.json(),allow_nan=False)
