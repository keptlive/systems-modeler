"""Assertions against analytic answers and actual persistence/API behavior."""
import math
import pytest
from fastapi.testclient import TestClient
from app.core.model import Model, TimeSettings, LookupTable
from app.core.simulator import simulate
from app.core.equations import safe_eval, EquationError
from app.core.xmile_parser import parse_xmile
from app.core.xmile_generator import generate_xmile
from app.storage import models as storage
from app.main import app


def growth(method="euler"):
    return Model(name="Growth", stocks=[{"id": "x", "name": "Population", "initial_value": 100}],
                 flows=[{"name": "births", "equation": "Population * rate", "to_stock": "x"}],
                 variables=[{"name": "rate", "equation": "0.1"}],
                 time_settings={"start": 5, "end": 6, "dt": 0.25, "integration_method": method})


def test_integrators_honor_method_start_and_step():
    euler = simulate(growth())
    rk4 = simulate(growth("rk4"))
    assert euler.time == [5, 5.25, 5.5, 5.75, 6]
    assert euler.values["Population"][-1] == pytest.approx(100 * 1.025**4)
    assert rk4.values["Population"][-1] == pytest.approx(100 * math.exp(0.1), rel=1e-8)
    for i in range(5):
        assert euler.values["births"][i] == pytest.approx(euler.values["Population"][i] * 0.1)


def test_euler_uses_previous_time_and_includes_partial_end():
    m = Model(stocks=[{"id": "s", "name": "X"}],
              flows=[{"name": "input", "equation": "TIME", "to_stock": "s"}],
              time_settings={"start": 0, "end": 1, "dt": 0.3})
    r = simulate(m)
    assert r.time[-1] == 1
    assert r.values["X"][-1] == pytest.approx(0.36)


@pytest.mark.parametrize("data", [{"dt": 0}, {"dt": -1}, {"end": 0}, {"dt": float("nan")},
                                  {"integration_method": "bogus"}])
def test_invalid_time_settings(data):
    with pytest.raises(ValueError):
        TimeSettings(**data)


def test_budget_enforced_before_allocation():
    with pytest.raises(EquationError, match="exceeds"):
        simulate(growth(), TimeSettings(end=1000000, dt=.001))


def test_dependencies_flow_to_variable_and_missing_error():
    m = growth()
    m.variables.append(type(m.variables[0])(name="double_births", equation="2 * births"))
    assert simulate(m).values["double_births"][0] == 20
    m.flows[0].equation = "missing_variable"
    with pytest.raises(EquationError, match="missing_variable"):
        simulate(m)


def test_initial_stock_equations_use_parameters():
    m = growth()
    m.stocks[0].equation = "rate * 1000"
    assert simulate(m).values["Population"][0] == 100


def test_conditional_is_lazy_and_xmile_power_supported():
    assert safe_eval("IF_THEN_ELSE(1, 2^3, 1/0)", {}) == 8
    with pytest.raises(EquationError, match="zero"):
        safe_eval("1/0", {})


def test_mass_conservation():
    m = Model(stocks=[{"id": "a", "name": "A", "initial_value": 100},
                      {"id": "b", "name": "B"}],
              flows=[{"name": "transfer", "equation": "A / 5", "from_stock": "a", "to_stock": "b"}])
    r = simulate(m)
    assert all(a + b == pytest.approx(100) for a, b in zip(r.values["A"], r.values["B"]))


def test_stateful_calls_keep_initial_values_and_independent_state():
    m = Model(variables=[{"name": "A", "equation": "SMOOTH(10, 2, 0)"},
                         {"name": "B", "equation": "SMOOTH(10, 2, 5)"}],
              time_settings={"start": 0, "end": 1, "dt": .5})
    r = simulate(m)
    assert r.values["A"] == pytest.approx([0, 2.5, 4.375])
    assert r.values["B"] == pytest.approx([5, 6.25, 7.1875])
    rk = simulate(m, TimeSettings(end=1, dt=.05, integration_method="rk4"))
    assert rk.values["A"][-1] == pytest.approx(10*(1-math.exp(-.5)), rel=1e-6)
    assert rk.values["B"][-1] == pytest.approx(10-5*math.exp(-.5), rel=1e-6)


def test_storage_and_xmile_keep_lookup_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "MODELS_DIR", str(tmp_path))
    m = growth()
    m.tables = [LookupTable(name="curve", points=[(0, 1), (1, 3)])]
    m = Model.model_validate(m.model_dump())
    m.stocks[0].equation = "rate * 1000"
    saved = storage.create_model(m)
    loaded = storage.get_model(saved.id)
    assert loaded.tables == m.tables
    imported = parse_xmile(generate_xmile(loaded))
    assert imported.tables == m.tables
    assert imported.stocks[0].equation == m.stocks[0].equation


def test_model_path_traversal_rejected():
    for value in ["../../etc/passwd", "/tmp/model", "a/b", "a\\b"]:
        with pytest.raises(ValueError):
            storage.find_model_path(value)


def test_api_catalog_and_simulation_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "MODELS_DIR", str(tmp_path))
    storage.create_model(growth())
    with TestClient(app) as client:
        catalog = client.get("/api/models/catalog").json()
        assert catalog["total"] == 1
        row = catalog["models"][0]
        assert row["stock_count"] == 1 and "stocks" not in row
        response = client.post("/api/simulate", json={"model": growth("rk4").model_dump(mode="json")})
        assert response.status_code == 200
        assert len(response.json()["time"]) == 5
        bad = growth().model_dump(mode="json")
        bad["flows"][0]["equation"] = "missing"
        assert client.post("/api/simulate", json={"model": bad}).status_code == 422


def test_catalog_refreshes_after_edit(tmp_path, monkeypatch):
    from app.storage.catalog import list_summaries
    monkeypatch.setattr(storage, "MODELS_DIR", str(tmp_path))
    saved = storage.create_model(growth())
    assert list_summaries()[0]["name"] == "Growth"
    saved.name = "Edited"
    storage.save_model(saved)
    assert list_summaries()[0]["name"] == "Edited"


def test_mcp_statistics_do_not_overflow_for_finite_large_values():
    from app.mcp_server import summarize
    from app.core.model import SimulationResult
    assert summarize(SimulationResult(time=[0, 1], values={"X": [1e308, 1e308]}))["X"]["mean"] == 1e308
