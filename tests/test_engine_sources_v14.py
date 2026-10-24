"""Source-backed engine compatibility; no model definitions are rewritten."""
import pytest
from app.core.equations import (EquationError, SimulationContext, safe_eval,
                                get_equation_variables, validate_equation)
from app.core.model import Model
from app.core.simulator import simulate


@pytest.mark.parametrize("expression, expected", [
    ("IF THEN ELSE(1<2,3,4)", 3),
    ("if then else(0,1/0,4)", 4),
    ("IF THEN ELSE(X=0,1,1/X)", 1),
    ("IF THEN ELSE(1,IF THEN ELSE(0,2,3),1/0)", 3),
    ("IF 1 THEN IF THEN ELSE(0,2,3) ELSE 4", 3),
    ("IF THEN ELSE(1,IF 0 THEN 2 ELSE 3,4)", 3),
])
def test_original_vensim_conditional_spelling_is_lazy(expression, expected):
    assert safe_eval(expression, {"X": 0}) == expected


def test_school_closure_original_equation_and_dependencies():
    expression = "IF THEN ELSE(Reported_Cases_Per_100000>School_Closure_Threshold,1,0)"
    names = ["Reported Cases Per 100000", "School Closure Threshold"]
    assert validate_equation(expression, names) == (True, "")
    assert get_equation_variables(expression) == {"Reported_Cases_Per_100000", "School_Closure_Threshold"}
    assert safe_eval(expression, dict(zip(names, [101, 100]))) == 1
    assert safe_eval(expression, dict(zip(names, [100, 100]))) == 0


@pytest.mark.parametrize("expression, expected", [
    ("3 > 2 > 1", 0),       # (3>2)>1 -> 1>1
    ("1 = 2 < 3", 1),       # 1=(2<3)
    ("0 = 3 > 2 > 1", 1),
    ("2 = 2 = 1", 1),       # (2=2)=1
    ("3 > 2 = 1 < 2", 1),
    ("1 <> 2 < 3", 0),
    ("(1 = 2) < 3", 1),
    ("3 > (2 > 1)", 1),
    ("IF 1 = 2 < 3 THEN 7 ELSE 1/0", 7),
])
def test_xmile_comparison_precedence_and_left_associativity(expression, expected):
    assert safe_eval(expression, {}) == expected


@pytest.mark.parametrize("expression, expected", [
    ("2*3 { product } + 4 { sum }", 10),
    ("IF { comment } 1 THEN 2 ELSE 1/0", 2),
    ("1 + { ignored 'quote' and ( bad syntax } 2", 3),
    ('"Name {with braces}" + 1', 5),
    ("1+{ multiline\ncomment }2", 3),
])
def test_xmile_brace_comments_preserve_quoted_identifiers(expression, expected):
    assert safe_eval(expression, {"Name {with braces}": 4}) == expected


def test_braces_in_single_quoted_table_name_are_preserved():
    context = SimulationContext(tables={"Curve {one}": [(0, 4), (1, 5)]})
    assert safe_eval("LOOKUP('Curve {one}', { input } 0)", {}, context) == 4


@pytest.mark.parametrize("expression", ["1 + {unclosed", "1+2}"])
def test_unbalanced_brace_comments_are_explicit(expression):
    with pytest.raises(EquationError, match="comment"):
        safe_eval(expression, {})


def test_comments_and_conditionals_integrate_through_both_methods():
    model = Model(stocks=[{"id": "x", "name": "X", "initial_value": 0}],
                  flows=[{"name": "Rate", "equation": "IF THEN ELSE(1 = 2 < 3, 2 { units/sec }, 0)", "to_stock": "x"}],
                  time_settings={"end": 2, "dt": .5})
    for method in ("euler", "rk4"):
        settings = model.time_settings.model_copy(update={"method": method})
        result = simulate(model, settings)
        assert result.values["X"] == pytest.approx([0, 1, 2, 3, 4])


@pytest.mark.parametrize("expression", [
    "STEP(1,0,999)", "PULSE(1,0,1,999)", "RAMP(1,0,1,999)",
    "WITH_LOOKUP(0,((0,1),(1,2)),999)", "LOOKUP('Curve',0,999)",
])
def test_context_functions_do_not_silently_drop_arguments(expression):
    context = SimulationContext(tables={"Curve": [(0, 1), (1, 2)]})
    with pytest.raises(EquationError, match="requires"):
        safe_eval(expression, {}, context)


@pytest.mark.parametrize("points", ["((0,1),(1,2,3))", "((0,1),999)", "((0,1),(1,))"])
def test_inline_lookup_cannot_silently_discard_malformed_points(points):
    with pytest.raises(EquationError, match="two coordinates"):
        safe_eval(f"WITH_LOOKUP(.5,{points})", {})


def test_inline_lookup_accepts_consistent_list_or_tuple_pairs():
    for points in ("((0,1),(1,3))", "[[0,1],[1,3]]"):
        assert safe_eval(f"WITH_LOOKUP(.5,{points})", {}) == 2


def test_unverified_dialects_still_fail_explicitly():
    for expression in ("STEP(50)", "RANDOM()", "RANDOM_NORMAL(0,1,0,1,42)"):
        with pytest.raises(EquationError):
            safe_eval(expression, {})
