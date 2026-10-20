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


# Stochastic contract: isolated streams, one sample per call/time, replay receipts.
def seeded_model(expression="RANDOM(0,1)", seed=42, end=4, dt=1):
    return Model(variables=[{"name":"Output","equation":expression}],
                 time_settings={"end":end,"dt":dt,"random_seed":seed})


def test_explicit_random_seed_replays_known_uniform_sequence():
    expected = [.5219839097124932,.8066907771186791,.9604947743238768,
                .2896253777644655,.7661074377979527]
    first = simulate(seeded_model("RANDOM(0,1,17)",seed=1))
    second = simulate(seeded_model("RANDOM(0,1,17)",seed=2))
    assert first.values["Output"] == pytest.approx(expected)
    assert second.values == first.values


def test_run_seed_and_effective_seed_receipt_allow_replay():
    model = seeded_model(seed=None)
    original = simulate(model)
    assert isinstance(original.random_seed,int) and 0 <= original.random_seed < 2**32
    replay = simulate(model, model.time_settings.model_copy(update={"random_seed":original.random_seed}))
    assert original.values == replay.values
    assert simulate(seeded_model(seed=41)).values != simulate(seeded_model(seed=42)).values


def test_random_streams_are_independent_of_equation_order_and_unrelated_calls():
    model = seeded_model()
    model.variables += [type(model.variables[0])(name="B",equation="NORMAL(2,3)")]
    expected = simulate(model).values
    model.variables.reverse()
    model.variables.insert(0,type(model.variables[0])(name="Unrelated",equation="RANDOM(0,1)"))
    result = simulate(model)
    assert all(result.values[name] == values for name,values in expected.items())


def test_dependency_retry_does_not_consume_extra_random_draw():
    model = seeded_model("RANDOM(0,1,17)+Later")
    model.variables.append(type(model.variables[0])(name="Later",equation="0"))
    expected = simulate(model).values
    model.variables.reverse()
    assert simulate(model).values == expected
    assert expected["Output"][0] == pytest.approx(.5219839097124932)


def test_hidden_state_initialization_and_derivative_reuse_same_time_noise():
    result = simulate(seeded_model("SMOOTH(RANDOM(0,1,17),1)"))
    assert result.values["Output"] == pytest.approx([
        .5219839097124932,.5219839097124932,.8066907771186791,
        .9604947743238768,.2896253777644655])


def test_seeded_streams_do_not_share_or_mutate_process_global_rng():
    import random
    from concurrent.futures import ThreadPoolExecutor
    model = seeded_model("RANDOM_NORMAL(2,3)")
    before = random.getstate()
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _:simulate(model).values,range(8)))
    assert all(result == results[0] for result in results)
    assert random.getstate() == before


def test_conditionally_inactive_random_stream_draws_only_when_called():
    result = simulate(seeded_model("IF(TIME<2,0,RANDOM(0,1,17))"))
    assert result.values["Output"] == pytest.approx([0,0,.5219839097124932,.8066907771186791,.9604947743238768])


def test_uniform_normal_aliases_and_distribution_parameters():
    assert simulate(seeded_model("NORMAL(2,3)")).values == simulate(seeded_model("RANDOM_NORMAL(2,3)")).values
    assert simulate(seeded_model("RANDOM(2,3)")).values == simulate(seeded_model("RANDOM_UNIFORM(2,3)")).values
    assert simulate(seeded_model("NORMAL(7,0)")).values["Output"] == [7]*5
    uniform = simulate(seeded_model("RANDOM(-2,3)",end=1000,dt=1)).values["Output"]
    normal = simulate(seeded_model("NORMAL(0,1,17)",end=1000,dt=1)).values["Output"]
    import statistics
    assert all(-2 <= value <= 3 for value in uniform)
    assert statistics.mean(normal) == pytest.approx(0,abs=.1)
    assert statistics.pstdev(normal) == pytest.approx(1,abs=.1)


@pytest.mark.parametrize("seed", ["True","False","1.5","-1","4294967296","1e309"])
def test_invalid_random_function_seed_is_explicit(seed):
    with pytest.raises(EquationError,match="seed"):
        simulate(seeded_model(f"RANDOM(0,1,{seed})"))


@pytest.mark.parametrize("expression", ["RANDOM()","RANDOM(2,1)","NORMAL(0,-1)","RANDOM(0,1e309)"])
def test_invalid_or_nonstandard_random_calls_do_not_silently_run(expression):
    with pytest.raises(EquationError):
        simulate(seeded_model(expression))


def test_changing_random_seed_mid_run_is_not_silent_reseeding():
    with pytest.raises(EquationError,match="Changing.*seed"):
        simulate(seeded_model("RANDOM(0,1,TIME)"))


def test_stochastic_standalone_context_reuses_same_time_then_advances():
    from app.core.equations import SimulationContext, RandomRuntime
    context = SimulationContext(time=0,random_runtime=RandomRuntime(42))
    first = safe_eval("RANDOM(0,1,17)",{},context)
    assert safe_eval("RANDOM(0,1,17)",{},context) == first
    context.time = 1
    assert safe_eval("RANDOM(0,1,17)",{},context) == pytest.approx(.8066907771186791)


def test_stochastic_call_budget_is_counted():
    model = seeded_model("+".join(["RANDOM(0,1)"]*100),end=10000,dt=1)
    with pytest.raises(EquationError,match="stochastic"):
        simulate(model)


def rk_hidden(expression,dt=.1,end=4):
    model = Model(variables=[{"name":"Output","equation":expression}],
                  time_settings={"end":end,"dt":dt,"integration_method":"rk4"})
    return simulate(model)


@pytest.mark.parametrize("function", ["SMOOTH","SMTH1","DELAY1"])
def test_rk4_ramp_hidden_state_matches_analytic_solution(function):
    result = rk_hidden(f"{function}(TIME,1,0)")
    assert result.values["Output"][-1] == pytest.approx(3+math.exp(-4),abs=1e-6)


@pytest.mark.parametrize("function", ["SMOOTH3","DELAY3","SMTHN"])
def test_rk4_three_hidden_stages_match_analytic_step_response(function):
    expression = f"{function}(1,3,3,0)" if function == "SMTHN" else f"{function}(1,3,0)"
    assert rk_hidden(expression).values["Output"][-1] == pytest.approx(1-13*math.exp(-4),abs=1e-6)


def test_rk4_hidden_state_converges_at_fourth_order():
    exact = 3+math.exp(-4)
    coarse = abs(rk_hidden("SMOOTH(TIME,1,0)",dt=.4).values["Output"][-1]-exact)
    fine = abs(rk_hidden("SMOOTH(TIME,1,0)",dt=.2).values["Output"][-1]-exact)
    assert 12 < coarse/fine < 22


def test_rk4_visible_and_hidden_stocks_share_all_derivative_stages():
    model = Model(stocks=[{"id":"x","name":"X"}],
                  flows=[{"name":"Input","equation":"SMOOTH(TIME,1,0)","to_stock":"x"}],
                  time_settings={"end":4,"dt":.1,"integration_method":"rk4"})
    result = simulate(model)
    assert result.values["X"][-1] == pytest.approx(5-math.exp(-4),abs=1e-6)
    assert all(x+s == pytest.approx(t*t/2,abs=1e-12)
               for t,x,s in zip(result.time,result.values["X"],result.values["Input"]))


def test_rk4_hidden_feedback_and_changing_smoothing_time():
    assert rk_hidden("SMOOTH(1-Output,1,0)").values["Output"][-1] == pytest.approx(.5*(1-math.exp(-8)),abs=1e-7)
    assert rk_hidden("SMOOTH(1,TIME+1,0)",dt=.05).values["Output"][-1] == pytest.approx(.8,abs=1e-7)


@pytest.mark.parametrize("expression", ["DELAY(TIME,1,0)","DELAY_FIXED(TIME,1,0)",
                                         "RANDOM(0,1,17)","NORMAL(0,1)"])
def test_rk4_rejects_only_unverified_history_or_stochastic_semantics(expression):
    with pytest.raises(EquationError,match="unsupported"):
        rk_hidden(expression)


def test_named_table_that_shares_stochastic_function_name_is_not_noise():
    from app.core.equations import equation_features
    model = Model(variables=[{"name":"Output","equation":"RANDOM(TIME)"}],
                  tables=[{"name":"RANDOM","points":[(0,0),(4,8)]}],
                  time_settings={"end":4,"dt":1,"integration_method":"rk4"})
    assert equation_features("RANDOM(TIME)",["RANDOM"])["random_calls"] == 0
    assert simulate(model).values["Output"] == [0,2,4,6,8]


def test_zero_width_uniform_remains_exact_at_float_extremes():
    import sys
    value = sys.float_info.max
    result = simulate(seeded_model(f"RANDOM({value},{value},17)",end=1000,dt=1))
    assert result.values["Output"] == [value]*1001


def test_rk4_coupled_visible_hidden_oscillator_matches_closed_form():
    model = Model(stocks=[{"id":"x","name":"X","initial_value":1}],
                  flows=[{"name":"Removal","equation":"SMOOTH(X,1,0)","from_stock":"x"}],
                  time_settings={"end":2,"dt":.05,"integration_method":"rk4"})
    result = simulate(model)
    frequency = math.sqrt(3)/2
    expected_x = math.exp(-1)*(math.cos(2*frequency)+math.sin(2*frequency)/math.sqrt(3))
    expected_s = 2/math.sqrt(3)*math.exp(-1)*math.sin(2*frequency)
    assert result.values["X"][-1] == pytest.approx(expected_x,abs=1e-7)
    assert result.values["Removal"][-1] == pytest.approx(expected_s,abs=1e-7)


def test_random_features_recognize_quoted_calls_and_table_precedence():
    from app.core.equations import equation_features
    assert equation_features('"RANDOM"(0,1)')["random_calls"] == 1
    assert equation_features("NORMAL(0,1)")["random_calls"] == 1
    assert equation_features('"NORMAL"(TIME)',["Normal"])["random_calls"] == 0


@pytest.mark.parametrize("expression,expected", [
    ("IF MOD(TIME,7)<5 THEN 1 ELSE 0",1),
    ("IF 1 THEN MOD(7,4) ELSE 0",3),
    ("NOT MOD(7,4)",0),
    ("IF 1 THEN TIME MOD(24) ELSE 0",1),
])
def test_mod_function_is_not_confused_with_infix_after_control_keywords(expression,expected):
    from app.core.equations import SimulationContext
    assert safe_eval(expression,{},SimulationContext(time=25)) == expected


def test_delayed_material_in_transit_preserves_total_mass_with_rk4():
    model = Model(stocks=[{"id":"a","name":"Origin","initial_value":100},
                          {"id":"b","name":"Destination"}],
                  flows=[{"name":"Departure","equation":"1","from_stock":"a"},
                         {"name":"Arrival","equation":"DELAY1(Departure,2,0)","to_stock":"b"}],
                  time_settings={"end":4,"dt":.1,"integration_method":"rk4"})
    result = simulate(model)
    assert all(origin+destination+2*arrival == pytest.approx(100,abs=1e-12)
               for origin,destination,arrival in zip(result.values["Origin"],
                 result.values["Destination"],result.values["Arrival"]))


@pytest.mark.parametrize("expression,expected", [("NOT 0+1",2),("NOT 0^0",0),
    ("2^NOT 1",1),("NOT 0<2",1),("IF NOT 0+1=2 THEN 7 ELSE 8",7)])
def test_xmile_not_has_unary_arithmetic_precedence(expression,expected):
    assert safe_eval(expression,{}) == expected


def test_xmile_not_and_mod_restore_to_external_syntax():
    import ast
    from app.core.equations import preprocess_equation,restore_identifiers
    expression = "NOT 0+7 MOD 4"
    restored = restore_identifiers(ast.unparse(ast.parse(preprocess_equation(expression),mode="eval")))
    assert "NOT" in restored and "MOD" in restored
    assert safe_eval(restored,{}) == safe_eval(expression,{})
    with pytest.raises(EquationError,match="raw ~"):
        safe_eval("~0",{})


def test_rk4_budget_counts_hidden_stages_and_all_derivative_evaluations():
    model = Model(variables=[{"name":"Output","equation":"SMOOTH_N(1,100,20,0)"}],
                  time_settings={"end":10000,"dt":1,"integration_method":"rk4"})
    with pytest.raises(EquationError,match="RK4 evaluations"):
        simulate(model)
