"""Adaptive conditional certificates cover entire supported condition shapes."""
import math
import pytest
from app.core.adaptive import state_discontinuities
from app.core.equations import EquationError
from app.core.model import Model
from app.core.simulator import simulate


def feedback(condition, yes="Stock", no="0", variables=(), initial=9):
    return Model(
        stocks=[{"id": "stock", "name": "Stock", "initial_value": initial}],
        flows=[{"name": "Rate", "equation": f"IF_THEN_ELSE({condition},{yes},{no})", "to_stock": "stock"}],
        variables=list(variables),
        time_settings={"start": 0, "end": .2, "dt": .1, "integration_method": "radau"},
    )


@pytest.mark.parametrize("condition", [
    "(Stock==0)+(Stock-10)",
    "((Stock==0)+(Stock-10))*2",
    "IF_THEN_ELSE(Stock==0,1,Stock-10)",
    "Stock AND Stock==0",
    "Stock OR Stock==0",
    "0<Stock<10",
])
@pytest.mark.parametrize("aliased", [False, True])
def test_radau_rejects_unproved_outer_condition_switches(condition, aliased):
    variables = []
    if aliased:
        variables = [{"name": "Condition A", "equation": condition},
                     {"name": "Condition B", "equation": '"Condition A"'}]
        condition = '"Condition B"'
    model = feedback(condition, variables=variables)
    assert {"element": "Rate", "operation": "uncertified state-dependent conditional"} in state_discontinuities(model)
    with pytest.raises(EquationError) as caught:
        simulate(model)
    assert caught.value.code == "unsupported_method_features"
    assert caught.value.details["state_discontinuities"]


@pytest.mark.parametrize("condition,yes,initial,expected", [
    ("Stock<0", "-Stock", -1, lambda t: -math.exp(-t)),
    ("NOT (Stock>=0)", "-Stock", -1, lambda t: -math.exp(-t)),
    ("Stock<0 OR Stock>1", "Stock*(Stock-1)", .5, lambda t: .5),
    ("Stock>0 AND Stock<1", "Stock*(1-Stock)", .5, lambda t: 1/(1+math.exp(-t))),
    ("ABS(Stock)<1", "1-ABS(Stock)", .5, lambda t: 1-.5*math.exp(-t)),
    ("Stock<0", "MIN(Stock,0)", -1, lambda t: -math.exp(t)),
    ("Stock>0", "MAX(Stock,0)", 1, lambda t: math.exp(t)),
])
@pytest.mark.parametrize("aliased", [False, True])
def test_radau_preserves_certified_continuous_piecewise_conditions(condition, yes, initial, expected, aliased):
    variables = []
    if aliased:
        variables = [{"name": "State A", "equation": "Stock"},
                     {"name": "State B", "equation": '"State A"'}]
        condition = condition.replace("Stock", '"State B"')
    model = feedback(condition, yes, variables=variables, initial=initial)
    assert state_discontinuities(model) == []
    result = simulate(model)
    assert result.integration_diagnostics["method"] == "radau"
    assert result.values["Stock"] == pytest.approx([expected(t) for t in result.time], abs=2e-7)


def test_conditional_certificate_does_not_certify_tangent_domain():
    model = feedback("TAN(Stock)<0", "TAN(Stock)", initial=.5)
    assert state_discontinuities(model)
    with pytest.raises(EquationError) as caught:
        simulate(model)
    assert caught.value.code == "unsupported_method_features"


@pytest.mark.parametrize("function", ["REM", "MODULO"])
@pytest.mark.parametrize("argument", ["Stock", "TIME"])
def test_remainder_aliases_share_discrete_adaptive_guards(function, argument):
    model = feedback("Stock<0", initial=1)
    model.flows[0].equation = f"{function}({argument},2)"
    with pytest.raises(EquationError) as caught:
        simulate(model)
    assert caught.value.code == "unsupported_method_features"
    guard = "state_discontinuities" if argument == "Stock" else "time_discontinuities"
    assert caught.value.details[guard]


@pytest.mark.parametrize("function", ["RAMP", "RAMP_VENSIM"])
@pytest.mark.parametrize("slope", ["1", "Stock", "TIME"])
def test_native_and_vensim_ramps_retain_held_input_adaptive_rejection(function, slope):
    model = feedback("Stock<0", initial=1)
    model.flows[0].equation = f"{function}({slope},0,1)"
    with pytest.raises(EquationError) as caught:
        simulate(model)
    assert caught.value.code == "unsupported_method_features"
    assert function in caught.value.details["unsupported_functions"]


@pytest.mark.parametrize("function", ["RAMP", "RAMP_VENSIM"])
def test_ramp_named_table_keeps_lookup_precedence_in_radau(function):
    model = Model(
        stocks=[{"id": "stock", "name": "Stock", "initial_value": 1}],
        variables=[{"name": "Probe", "equation": f"{function}(Stock)"}],
        tables=[{"name": function, "points": [(0, 10), (1, 20)]}],
        time_settings={"end": .2, "dt": .1, "integration_method": "radau"},
    )
    assert simulate(model).values["Probe"] == [20, 20, 20]
