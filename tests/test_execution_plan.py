"""Plans preserve trajectories/errors and report truthful reduced DAG work."""
import pytest
from app.core import integration
from app.core.equations import EquationError
from app.core.model import Model
from app.core.simulator import simulate


def outcome(model):
    try:
        result = simulate(model)
        return ("ok", result.model_dump(mode="json"))
    except EquationError as error:
        return ("error", str(error), error.code, error.details)


@pytest.mark.parametrize("method", ["euler", "rk4", "radau"])
@pytest.mark.parametrize("variables,stocks,flows", [
    ([{"name":"Last","equation":"Middle+1"},{"name":"Middle","equation":"First+1"},{"name":"First","equation":"2"}], [], []),
    ([{"name":"a","equation":"b+1"},{"name":"b","equation":"a+1"}], [], []),
    ([{"name":"a","equation":"IF(1, 4, unknown)"}], [], []),
    ([{"name":"a","equation":"pi+1"}], [{"name":"pi","initial_value":0,"equation":"q+1"},{"name":"q","initial_value":0,"equation":"2"}], []),
    ([{"name":"rate","equation":"0.1"}], [{"id":"s","name":"Amount","initial_value":5}], [{"name":"Drain","equation":"Amount*rate","from_stock":"s"}]),
])
def test_planned_and_live_metadata_are_identical(monkeypatch, method, variables, stocks, flows):
    model = Model(variables=variables, stocks=stocks, flows=flows,
                  time_settings={"end":2,"dt":.25,"integration_method":method,"random_seed":123})
    planned = outcome(model)
    monkeypatch.setattr(integration, "_make_evaluation_plan", lambda model: None)
    live = outcome(model)
    if planned[0] == "error":
        assert live == planned
    else:
        assert live[0] == "ok"
        planned_data, live_data = planned[1], live[1]
        planned_diagnostics = planned_data.pop("integration_diagnostics") or {}
        live_diagnostics = live_data.pop("integration_diagnostics") or {}
        assert planned_data == live_data
        planned_retries = planned_diagnostics.get("dependency_retries", 0)
        live_retries = live_diagnostics.get("dependency_retries", 0)
        assert planned_retries <= live_retries
        if planned_diagnostics and live_diagnostics:
            assert planned_diagnostics["work_units"] <= live_diagnostics["work_units"]
            assert live_diagnostics["work_units"] - planned_diagnostics["work_units"] == live_retries - planned_retries
            for key in ("work_units", "dependency_retries"):
                planned_diagnostics.pop(key)
                live_diagnostics.pop(key)
            assert planned_diagnostics == live_diagnostics
        elif live_diagnostics:
            # Ordinary deterministic zero-retry runs omit the optional receipt.
            assert not planned_diagnostics and planned_retries == 0 and live_retries > 0
            assert live_diagnostics["binomial_trials"] == live_diagnostics["report_evaluations"] == 0
        else:
            assert not planned_diagnostics
    assert integration._active_plan.get() is None


@pytest.mark.parametrize("expression", ["RANDOM_UNIFORM(0,1)", "RANDOM_BINOMIAL(20,.3)", "SMOOTH(2,1)", "IF(TIME<1,2,SMOOTH(3,1))"])
def test_stochastic_and_hidden_state_keep_exact_order(monkeypatch, expression):
    model = Model(variables=[{"name":"Forward","equation":"Later+1"},{"name":"Draw","equation":expression},{"name":"Later","equation":"3"}],time_settings={"end":3,"dt":.25,"random_seed":100})
    planned = outcome(model)
    monkeypatch.setattr(integration, "_make_evaluation_plan", lambda model: None)
    assert outcome(model) == planned


def test_editing_same_model_rebuilds_plan_and_context_is_reset():
    model = Model(variables=[{"name":"Value","equation":"1"}],time_settings={"end":1,"dt":1})
    assert simulate(model).values["Value"] == [1,1]
    model.variables[0].equation = "7"
    assert simulate(model).values["Value"] == [7,7]
    assert integration._active_plan.get() is None
    plan = integration._make_evaluation_plan(model)
    with pytest.raises(TypeError):
        plan.table_types["x"] = "discrete"
    with pytest.raises(AttributeError):
        plan.declared_names.add("new")
