"""Independent engine review: analytical hidden-state and parsing regressions."""
import math
import pytest
from app.core.model import Model, TimeSettings
from app.core.simulator import simulate
from app.core.equations import safe_eval, EquationError


def series(equation, end=4, dt=1):
    model = Model(variables=[{"name": "Output", "equation": equation}],
                  time_settings={"start": 0, "end": end, "dt": dt})
    return simulate(model).values["Output"]


@pytest.mark.parametrize("function", ["SMOOTH", "SMTH1", "DELAY1"])
def test_ramp_input_hidden_stocks_use_previous_time(function):
    # Euler: s[n+1] = s[n] + (n-s[n]); first step has zero derivative.
    assert series(f"{function}(TIME,1,0)") == pytest.approx([0, 0, 1, 2, 3])


def test_changing_information_time_constant_keeps_state():
    assert series("SMOOTH(1,TIME+1,0)") == pytest.approx([0, 1, 1, 1, 1])


def test_explicit_initial_value_breaks_feedback_cycle():
    assert series("SMOOTH(1-Output,1,0)") == pytest.approx([0, 1, 0, 1, 0])


@pytest.mark.parametrize("function", ["SMOOTH3", "SMTH3", "DELAY3"])
def test_third_order_stages_advance_simultaneously(function):
    # Three internal stocks with tau=1 require three steps for a constant
    # input to reach the last stock; the ramp begins one timestep later.
    assert series(f"{function}(TIME,3,0)") == pytest.approx([0, 0, 0, 0, 1])


@pytest.mark.parametrize("function", ["DELAY", "DELAY_FIXED"])
def test_fixed_delay_uses_seeded_input_history(function):
    assert series(f"{function}(10+TIME,2,99)") == pytest.approx([99, 99, 10, 11, 12])


def test_fractional_fixed_delay_uses_documented_sample_and_hold():
    assert series("DELAY(TIME,1.5,99)") == pytest.approx([99, 99, 0, 1, 2])


def test_inactive_conditional_does_not_stop_hidden_time():
    assert series("IF(TIME<2,0,SMOOTH(TIME,1,0))") == pytest.approx([0, 0, 1, 2, 3])


def test_hidden_stock_and_ordinary_stock_step_together():
    model = Model(stocks=[{"id": "x", "name": "X"}],
                  flows=[{"name": "Input", "equation": "SMOOTH(TIME,1,0)", "to_stock": "x"}],
                  time_settings={"end": 4, "dt": 1})
    result = simulate(model)
    assert result.values["Input"] == pytest.approx([0, 0, 1, 2, 3])
    assert result.values["X"] == pytest.approx([0, 0, 0, 1, 3])


@pytest.mark.parametrize("expression", ["DELAY1(1,TIME+1,0)", "DELAY(1,TIME+1,0)",
                                         "SMOOTH_N(1,3,TIME+1,0)"])
def test_unsupported_changing_material_delay_or_order_is_explicit(expression):
    with pytest.raises(EquationError, match="Changing"):
        series(expression)


@pytest.mark.parametrize("expression", ["SMOOTH(1,0,0)", "DELAY(1,-1,0)",
                                         "SMOOTH_N(1,2,1.5,0)", "DELAY(1,2,3,4)"])
def test_invalid_stateful_arguments_fail_explicitly(expression):
    with pytest.raises(EquationError):
        series(expression)


@pytest.mark.parametrize("expression,answer", [
    ("(IF 1 THEN 2 ELSE 3) + (IF 0 THEN 4 ELSE 5)", 7),
    ("IF 1 THEN IF 0 THEN 2 ELSE 3 ELSE 4", 3),
    ("MAX(0, IF 1 THEN 2 ELSE 3)", 2),
    ("IF 1 THEN 2 ELSE IF 0 THEN 3 ELSE 4", 2),
    ("IF (1=1) AND NOT (2=3) THEN 2 ELSE 1/0", 2),
    ("IF 1<>2 THEN 5 ELSE 7", 5),
])
def test_nested_xmile_conditionals(expression, answer):
    assert safe_eval(expression, {}) == answer


def test_constants_do_not_shadow_user_parameters():
    assert safe_eval("e * 2", {"e": 0.2}) == pytest.approx(.4)
    assert safe_eval("pi * 2", {"Pi": 3}) == 6
    assert safe_eval("PI", {}) == math.pi


@pytest.mark.parametrize("names", [("A", "a"), ("a-b", "a_b"), ("A B", "A_B")])
def test_colliding_aliases_are_rejected(names):
    model = Model(variables=[{"name": name, "equation": "1"} for name in names])
    with pytest.raises(EquationError, match="unique"):
        simulate(model)


def test_ambiguous_stock_endpoint_is_rejected():
    model = Model(stocks=[{"id": "x", "name": "A"}, {"id": "y", "name": "x"}])
    with pytest.raises(EquationError, match="Ambiguous stock"):
        simulate(model)


def test_reserved_time_name_is_rejected():
    model = Model(variables=[{"name": "TIME", "equation": "99"}])
    with pytest.raises(EquationError, match="reserved"):
        simulate(model)


def test_nonfinite_initial_stock_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        Model(stocks=[{"name": "X", "initial_value": math.inf}])


def test_partial_final_step_keeps_dt_constant_and_uses_actual_step_for_state():
    model = Model(variables=[{"name": "Output", "equation": "SMOOTH(1,2,0)"},
                             {"name": "Step", "equation": "DT"}],
                  time_settings={"end": 1.5, "dt": 1})
    result = simulate(model)
    assert result.values["Output"] == pytest.approx([0, .5, .625])
    assert result.values["Step"] == [1, 1, 1]


def test_hidden_stock_budget_counts_stages():
    model = Model(variables=[{"name": "Output", "equation": "SMOOTH_N(1,100,100,0)"}],
                  time_settings={"end": 10000, "dt": 1})
    with pytest.raises(EquationError, match="including delay/smooth"):
        simulate(model)


def test_grid_cannot_silently_repeat_times_due_to_float_precision():
    model = Model(time_settings={"start": 1e16, "end": 1e16 + 2, "dt": .25})
    with pytest.raises(EquationError, match="represented"):
        simulate(model)


def test_fixed_delay_respects_small_time_units():
    assert series("DELAY(TIME,2e-12,99)", end=4e-12, dt=1e-12) == pytest.approx([99,99,0,1e-12,2e-12], abs=1e-20)


def test_validator_and_connector_references_share_simulation_syntax():
    from app.core.equations import validate_equation, get_equation_variables
    expression = "IF growth_rate > DT THEN IF (TIME=0) THEN Total_Population ELSE 0 ELSE 1"
    assert validate_equation(expression, ["Growth Rate", "Total Population"])[0]
    assert get_equation_variables(expression) == {"growth_rate", "Total_Population"}
    assert not validate_equation("UNKNOWN(1)", [])[0]
    assert not validate_equation("MISSING", [])[0]


def test_validator_understands_named_lookup_and_table_function_aliases():
    from app.core.equations import validate_equation, get_equation_variables
    assert validate_equation("LOOKUP(Curve_Name, X)", ["X"], ["Curve Name"])[0]
    assert validate_equation("curve_name(X)", ["X"], ["Curve Name"])[0]
    assert get_equation_variables("LOOKUP(Curve_Name, X)") == {"X"}
    assert not validate_equation("LOOKUP(Missing, X)", ["X"], ["Curve Name"])[0]


@pytest.mark.parametrize("expression", ["curve_name(TIME)", "LOOKUP(CURVE_NAME,TIME)",
                                         "LOOKUP('Curve Name',TIME)"])
def test_table_aliases_resolve_consistently(expression):
    model = Model(tables=[{"name": "Curve Name", "points": [(0, 0), (4, 8)]}],
                  variables=[{"name": "Output", "equation": expression}],
                  time_settings={"end": 4, "dt": 1})
    assert simulate(model).values["Output"] == [0, 2, 4, 6, 8]


def test_connector_discovery_retains_user_parameters_named_constants():
    from app.core.equations import get_equation_variables
    assert get_equation_variables("Pi * e") == {"Pi", "e"}


@pytest.mark.parametrize("points", [[], [(0, math.nan)], [(math.inf, 1)], [(0, 1), (0, 2)]])
def test_malformed_lookup_data_is_explicit(points):
    from app.core.equations import lookup_interp
    with pytest.raises(EquationError, match="Lookup"):
        lookup_interp(0, points)


def test_single_point_lookup_is_constant():
    from app.core.equations import lookup_interp
    assert lookup_interp(-99, [(1, 7)]) == 7


@pytest.mark.parametrize("value,expected", [(-3,-1), (0,0), (2,1)])
def test_sign_function(value, expected):
    assert safe_eval(f"SIGN({value})", {}) == expected


@pytest.mark.parametrize("y,x,expected", [(1,0,math.pi/2), (0,-1,math.pi), (-1,0,-math.pi/2)])
def test_atan2_argument_order(y,x,expected):
    assert safe_eval(f"ATAN2({y},{x})", {}) == pytest.approx(expected)


@pytest.mark.parametrize("expression,expected", [("25 MOD 24",1), ("-5 MOD 3",1),
    ("5 MOD -3",-1), ("25 MOD(24)",1), ("2+7 MOD 4*3",11),
    ("MOD(7,4)",3), ("MOD(7,4)+TIME MOD 24",4)])
def test_infix_mod_has_floor_modulus_and_multiplication_precedence(expression,expected):
    from app.core.equations import SimulationContext
    assert safe_eval(expression, {}, SimulationContext(time=25)) == expected


def test_python_keyword_and_quoted_utf8_identifiers():
    from app.core.equations import validate_equation, get_equation_variables
    expression = 'lambda + "Population total" + "人口" + "é"'
    variables = {"lambda": 2, "Population_total": 3, "人口": 4, "é": 5}
    assert safe_eval(expression, variables) == 14
    assert validate_equation(expression, list(variables))[0]
    assert get_equation_variables(expression) == {"lambda", "Population total", "人口", "é"}


def test_encoded_identifier_prefix_cannot_capture_user_names():
    expression = '__xmile_id_6162 + "ab"'
    assert safe_eval(expression, {"__xmile_id_6162": 3, "ab": 4}) == 7


def test_quoted_table_name_and_lookup_convenience_share_resolution():
    from app.core.equations import SimulationContext
    context = SimulationContext(tables={"é Curve": [(0,0),(2,4)]})
    assert safe_eval('"é Curve"(2)', {}, context) == 4
    assert safe_eval('LOOKUP("é Curve",2)', {}, context) == 4
    assert safe_eval("LOOKUP('é Curve',2)", {}, context) == 4


def test_unicode_names_remain_distinct_and_xmile_whitespace_aliases_match():
    model = Model(variables=[{"name":"人口","equation":"4"}, {"name":"é","equation":"5"},
                             {"name":"Output","equation":'"人口"+"é"'}])
    assert simulate(model).values["Output"][0] == 9
    assert safe_eval('"Total__Population"', {"Total Population":3}) == 3
    assert safe_eval('"Total Population"', {"Total\nPopulation":3}) == 3


def test_restoring_ast_identifiers_for_xmile_export():
    import ast
    from app.core.equations import preprocess_equation, restore_identifiers
    expression = 'lambda + "人口"'
    restored = restore_identifiers(ast.unparse(ast.parse(preprocess_equation(expression),mode="eval")))
    assert safe_eval(restored, {"lambda":2,"人口":3}) == 5


@pytest.mark.parametrize("expression", [r'"bad\tname"', r'"bad\uname"'])
def test_invalid_xmile_identifier_escape_is_explicit(expression):
    with pytest.raises(EquationError, match="escape"):
        safe_eval(expression, {})


def test_unclosed_quoted_name_has_equation_error_contract():
    with pytest.raises(EquationError):
        safe_eval('"unfinished', {})


def test_punctuation_and_repeated_whitespace_aliases_normalize_consistently():
    assert safe_eval("a__b", {"a--b":3}) == 3
