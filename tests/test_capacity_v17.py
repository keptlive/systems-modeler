"""Expanded capacity preserves the requested numerical grid and bounded outputs."""
import math
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import simulate as simulate_api
from app.core.equations import EquationError
from app.core.model import Model, TimeSettings
from app.core.simulator import simulate
from app.llm.analyzer import validate_results, descriptive_analysis


def ramp(intervals=40000, method="euler"):
    return Model(stocks=[{"id": "x", "name": "X", "initial_value": 3}],
                 flows=[{"name": "Input", "equation": "2", "to_stock": "x"}],
                 time_settings={"start": 0, "end": 4, "dt": 4 / intervals,
                                "integration_method": method})


@pytest.mark.parametrize("method", ["euler", "rk4"])
def test_12800_intervals_oscillator_against_analytical_solution(method):
    model = Model(stocks=[{"id":"x", "name":"X", "initial_value":1},
                          {"id":"v", "name":"V", "initial_value":0}],
                  flows=[{"name":"DX", "equation":"V", "to_stock":"x"},
                         {"name":"DV", "equation":"-X", "to_stock":"v"}],
                  time_settings={"end":10, "dt":10/12800, "integration_method":method})
    result = simulate(model)
    assert result.time == [i * (10/12800) for i in range(12801)]
    tolerance = .004 if method == "euler" else 2e-11
    assert max(abs(x-math.cos(t)) for t,x in zip(result.time,result.values["X"])) < tolerance
    assert max(abs(v+math.sin(t)) for t,v in zip(result.time,result.values["V"])) < tolerance
    validate_results(result.model_dump())


def test_40000_intervals_full_output_analytics_and_rest():
    application = FastAPI()
    application.include_router(simulate_api.router, prefix="/api")
    with TestClient(application) as client:
        response = client.post("/api/simulate", json={"model":ramp().model_dump(mode="json")})
    assert response.status_code == 200, response.text
    result=response.json()
    assert len(result["time"]) == 40001
    assert result["time"][0] == 0 and result["time"][-1] == 4
    assert max(abs(x-(3+2*t)) for t,x in zip(result["time"],result["values"]["X"])) < 1e-10
    validate_results(result)
    report=descriptive_analysis(result)
    assert report


def test_absolute_interval_ceiling_rejects_before_running():
    with pytest.raises(EquationError, match="100,000 intervals"):
        simulate(ramp(100001))


def test_initial_sample_counts_toward_retained_value_budget():
    # 100000 intervals * 10 series would fit the old interval-only budget,
    # but 100001 retained samples * 10 exceeds the result/analytics contract.
    model=ramp(100000)
    model.variables.extend(Model(variables=[{"name":f"Y{i}", "equation":"1"} for i in range(8)]).variables)
    with pytest.raises(EquationError, match="retained scalar values"):
        simulate(model)


def test_rk4_and_hidden_stages_still_count_toward_work():
    model=ramp(50000, "rk4")
    model.variables=Model(variables=[{"name":"Smoothed","equation":"SMOOTH3(X,1,0)"}]).variables
    with pytest.raises(EquationError, match="work units"):
        simulate(model)


def test_analytics_absolute_and_total_value_guards_remain():
    with pytest.raises(ValueError, match="100001 samples"):
        validate_results({"time":list(range(100002)), "values":{"X":[0]*100002}})
    with pytest.raises(ValueError, match="1000000 total"):
        validate_results({"time":list(range(100001)), "values":{str(i):[0]*100001 for i in range(10)}})


def test_investigation_and_mcp_accept_expanded_capacity_without_model_writes():
    from app.core.diagnostics import investigate_model
    from app.mcp_server import simulate_model
    model=ramp(12800)
    report=investigate_model(model,max_runs=1)
    assert report["runs"][0]["status"] == "completed"
    assert report["runs"][0]["samples"] == 12801
    result=simulate_model(model_json=model.model_dump(mode="json"),max_points=20)
    assert result["time_points"] == 12801
    assert result["sampled"] is True
    assert len(result["data"]["time"]) == 20
    assert result["data"]["X"][-1] == pytest.approx(11,abs=1e-10)
