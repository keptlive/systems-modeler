"""Typed adapter integration against independent scalar formulas."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.core.structured import compile_structured_model, StructuredModelError
from app.core.model import Model
from app.core.simulator import simulate


def fixture(expr):
    return {"name":"reductions", "dimensions":[{"name":"R","elements":["A","B"]}],
        "variables":[{"name":"P","dimensions":["R"],"equation":"2+TIME","equations":{"B":"8-2*TIME"}},
                     {"name":"Q","equation":expr}], "time_settings":{"end":8,"dt":0.25}}


def run(raw):
    return simulate(Model.model_validate(compile_structured_model(raw)["model"])).values


@pytest.mark.parametrize("op,manual", [("SUM","(2+TIME)+(8-2*TIME)"),
    ("MEAN","((2+TIME)+(8-2*TIME))/2"), ("MIN","MIN(2+TIME,8-2*TIME)"),
    ("MAX","MAX(2+TIME,8-2*TIME)")])
@pytest.mark.parametrize("solver", ["euler","rk4","radau"])
def test_independent_full_trajectory(op, manual, solver):
    raw=fixture(op+"(P[R])")
    raw["time_settings"]["integration_method"]=solver
    saved=deepcopy(raw)
    actual=run(raw)
    expected=run(fixture(manual))
    assert actual["Q"] == expected["Q"]
    assert raw == saved


@pytest.mark.parametrize("expr,expected", [('MEAN("P[R]")',5),('MAX(0,MEAN(P))',5),
    ('SUM(P[A])',2),('MEAN(P[A])',2)])
def test_quoted_and_scalar_outer(expr, expected):
    assert run(fixture(expr))["Q"][0] == expected


def test_multiargument_clipping_keeps_current_cell():
    raw=fixture("SUM(P)")
    raw["variables"].append({"name":"Clip","dimensions":["R"],"equation":"MAX(P[R],0)"})
    values=run(raw)
    assert values["Clip[A]"] == values["P[A]"]
    assert values["Clip[B]"][0] == 8


@pytest.mark.parametrize("op", ["MIN","MAX"])
def test_unary_literal_cell_keeps_scalar_source(op):
    out=compile_structured_model(fixture(op+"(P[A])"))["model"]
    assert out["variables"][-1]["equation"] == op+'("P[A]")'


def test_no_placeholder_injection_or_collision():
    raw=fixture('SUM(P)+__structured_sum_0+"__structured_sum_0_"')
    raw["variables"] += [{"name":"__structured_sum_0","equation":"7"},
                           {"name":"__structured_sum_0_","equation":"11"}]
    assert run(raw)["Q"][0] == 28


@pytest.mark.parametrize("expr", ['MEAN(P*2)','SUM(P,2)','MEAN(P[Missing])',
    'MIN(P[Missing])','MEAN("P[R]{bad}")'])
def test_errors_fail_closed(expr):
    with pytest.raises(StructuredModelError):
        compile_structured_model(fixture(expr))


def test_shared_budget_across_expanded_cells():
    raw=fixture("SUM(P)")
    raw["variables"].append({"name":"Repeated","dimensions":["R"],"equation":"1"})
    # Each expression is under the local limit; aggregate authored work is not.
    raw["variables"] += [{"name":"V"+str(i),"equation":"1"+" "*99000} for i in range(22)]
    with pytest.raises(StructuredModelError) as error:
        compile_structured_model(raw)
    assert error.value.code == "resource_limit"


def test_generated_text_limit():
    raw={"dimensions":[{"name":"R","elements":["M"+str(i) for i in range(1000)]}],
        "variables":[{"name":"P"+"x"*120,"dimensions":["R"],"equation":"1"},
                     {"name":"Q","equation":"MEAN(P"+"x"*120+")"}]}
    with pytest.raises(StructuredModelError) as error:
        compile_structured_model(raw)
    assert error.value.code == "resource_limit"


def test_module_local_arrays_and_scalar_ports():
    raw=fixture("m.result")
    raw["module_definitions"]={"M":{"inputs":["input"],"outputs":{"result":"Mean"},
        "variables":[{"name":"Local","dimensions":["R"],"equation":"input","equations":{"B":"input*3"}},
                     {"name":"Mean","equation":"MEAN(Local[R])+MEAN(input)"}]}}
    raw["modules"]=[{"name":"m","definition":"M","inputs":{"input":"P[A]"}}]
    assert run(raw)["Q"][0] == 6
    raw["module_definitions"]["M"]["variables"][-1]["equation"]="MEAN(P)"
    with pytest.raises(StructuredModelError):
        compile_structured_model(raw)

@pytest.mark.parametrize("op", ["MIN","MAX"])
def test_unary_scalar_time_keeps_existing_scalar_validation(op):
    out=compile_structured_model(fixture(op+"(TIME)"))["model"]
    assert out["variables"][-1]["equation"] == op+"(TIME)"

@pytest.mark.parametrize("op,column", [("SUM","total"),("MEAN","average"),("MIN","minimum"),("MAX","maximum")])
def test_executed_simlin_reference_all_samples(op, column):
    receipt=json.loads((Path(__file__).parents[1]/"docs/array-reduction-simlin-reference.json").read_text())
    raw=fixture(op+"(P[R])")
    raw["time_settings"]={"end":4,"dt":0.125}
    assert run(raw)["Q"] == receipt["values"][column]


@pytest.mark.parametrize("solver", ["euler","rk4","radau"])
def test_stock_feedback_matches_hand_expanded(solver):
    raw=fixture("MEAN(P[R])")
    raw["stocks"]=[{"name":"State","initial_value":1}]
    raw["flows"]=[{"name":"Growth","equation":"State * (MEAN(P[R])+MIN(P[R])+MAX(P[R])) * 0.01", "to_stock":"State"}]
    raw["time_settings"]["integration_method"]=solver
    expected=deepcopy(raw)
    expected["variables"][-1]["equation"]="(P[A]+P[B])/2"
    expected["flows"][0]["equation"]="State * ((P[A]+P[B])/2+MIN(P[A],P[B])+MAX(P[A],P[B])) * 0.01"
    assert run(raw)["State"] == run(expected)["State"]
