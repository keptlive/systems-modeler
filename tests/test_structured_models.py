"""Native lowering checked against independently written scalar models."""
from copy import deepcopy
import pytest
from app.core.structured import compile_structured_model, StructuredModelError
from app.core.model import Model
from app.core.simulator import simulate

def run(raw):
    return simulate(Model.model_validate(raw)).values

def test_array_matches_independent_scalar_reference_and_preserves_source():
    raw = {"name":"regions", "dimensions":[{"name":"Region","elements":["North","South"]}],
        "stocks":[{"name":"Population","dimensions":["Region"],"initial_value":20,"initial_values":{"North":10}}],
        "flows":[{"name":"Births","dimensions":["Region"],"equation":"Population[Region] * 0.1","to_stock":"Population[Region]"}],
        "variables":[{"name":"Total","equation":"SUM(Population[Region])"}],
        "time_settings":{"end":2,"dt":0.25}}
    saved = deepcopy(raw)
    compiled = compile_structured_model(raw)
    actual = run(compiled["model"])
    reference = {"name":"manual","stocks":[{"id":"n","name":"N","initial_value":10},{"id":"s","name":"S","initial_value":20}],
        "flows":[{"name":"BN","equation":"N * 0.1","to_stock":"n"},{"name":"BS","equation":"S * 0.1","to_stock":"s"}],
        "variables":[{"name":"T","equation":"N + S"}], "time_settings":raw["time_settings"]}
    expected = run(reference)
    for a,b in [("Population[North]","N"),("Population[South]","S"),("Total","T")]:
        assert actual[a] == pytest.approx(expected[b])
    assert raw == saved
    assert compiled == compile_structured_model(raw)
    assert len(compiled["source_map"]) == 5

def test_multidimensional_mapping_and_subset_sum():
    raw={"dimensions":[{"name":"Region","elements":["North","South"]},{"name":"Age","elements":["Young","Old"]}],
        "variables":[{"name":"P","dimensions":["Region","Age"],"equation":"2","equations":{"North,Old":"5"}},
            {"name":"T","equation":"SUM(P[North,Age])"},{"name":"Q","dimensions":["Region","Age"],"equation":"P[Region,Age] + P[South,Young]"}]}
    out=compile_structured_model(raw)["model"]
    values=run(dict(out,name="multi"))
    assert values["T"][0] == 7
    assert values["Q[North,Old]"][0] == 7

def modules():
    return {"name":"modules", "module_definitions":{"Tank":{"inputs":["rate"],"outputs":{"remaining":"A","received":"B"},
        "stocks":[{"name":"A","initial_value":100},{"name":"B","initial_value":0}],
        "flows":[{"name":"transfer","equation":"A * rate","from_stock":"A","to_stock":"B"}]}},
        "variables":[{"name":"speed","equation":"0.1"},{"name":"Total","equation":"left.remaining + left.received"}],
        "modules":[{"name":"left","definition":"Tank","inputs":{"rate":"speed"}},{"name":"right","definition":"Tank","inputs":{"rate":"speed"}}],
        "time_settings":{"end":3,"dt":0.25}}

def test_reusable_modules_conserve_and_do_not_capture():
    out=run(compile_structured_model(modules())["model"])
    assert out["Total"] == pytest.approx([100]*len(out["Total"]))
    assert out["left.A"] == out["right.A"]
    raw=modules()
    raw["module_definitions"]["Tank"]["flows"][0]["equation"]="A * speed"
    with pytest.raises(StructuredModelError, match="Unknown reference speed"):
        compile_structured_model(raw)

def test_nested_module_output_and_input_binding():
    raw=modules()
    raw["module_definitions"]["Wrapper"]={"inputs":["r"],"outputs":{"value":"inside.remaining"},
        "modules":[{"name":"inside","definition":"Tank","inputs":{"rate":"r"}}]}
    raw["modules"]=[{"name":"left","definition":"Wrapper","inputs":{"r":"speed"}}]
    raw["variables"][1]["equation"]="left.value"
    out=run(compile_structured_model(raw)["model"])
    assert out["Total"] == out["left.inside.A"]

@pytest.mark.parametrize("change,code",[
    (lambda r:r["stocks"][0].update(dimensions=["Missing"]), "invalid_shape"),
    (lambda r:r["stocks"][0].update(initial_values={"East":2}), "invalid_override"),
    (lambda r:r["variables"][0].update(equation="P[East]"), "invalid_index"),
    (lambda r:r["variables"][0].update(equation="P"), "unbound_dimension"),
    (lambda r:r["variables"][0].update(equation="SUM(P[Region] * 2)"), "unsupported_semantics"),
    (lambda r:r["dimensions"][0].update(elements=["North","North"]), "invalid_dimension"),
    (lambda r:r.update(connectors=[{"from_element":"x","to_element":"y"}]), "unsupported_semantics"),
    (lambda r:r["stocks"][0].update(initial_values=[]), "invalid_override"),
])
def test_invalid_array_contract(change,code):
    raw={"dimensions":[{"name":"Region","elements":["North","South"]}],"stocks":[{"name":"P","dimensions":["Region"]}],
        "variables":[{"name":"T","equation":"SUM(P[Region])"}]}
    change(raw)
    with pytest.raises(StructuredModelError) as exc:
        compile_structured_model(raw)
    assert exc.value.code == code
    assert exc.value.diagnostics[0]["severity"]=="error"

def test_module_recursion_missing_input_and_cross_boundary_flow():
    raw=modules()
    raw["module_definitions"]["Tank"]["modules"]=[{"name":"recursive","definition":"Tank","inputs":{"rate":"rate"}}]
    with pytest.raises(StructuredModelError) as exc: compile_structured_model(raw)
    assert exc.value.code=="recursive_module"
    raw=modules(); raw["modules"][0]["inputs"]={}
    with pytest.raises(StructuredModelError) as exc: compile_structured_model(raw)
    assert exc.value.code=="module_binding"
    raw=modules();raw["flows"]=[{"name":"bad","equation":"1","to_stock":"left.remaining"}]
    with pytest.raises(StructuredModelError) as exc: compile_structured_model(raw)
    assert exc.value.code=="invalid_flow_endpoint"

def test_bounds_and_duplicate_names():
    raw={"dimensions":[{"name":"D","elements":["v"+str(i) for i in range(65)]}],
        "stocks":[{"name":"P","dimensions":["D"]},{"name":"Q","dimensions":["D"]}]}
    raw["dimensions"].append({"name":"E","elements":["v"+str(i) for i in range(65)]})
    raw["stocks"][0]["dimensions"]=["D","E"]
    with pytest.raises(StructuredModelError) as exc: compile_structured_model(raw)
    assert exc.value.code=="resource_limit"
    raw=modules();raw["modules"][0]["name"]="speed"
    with pytest.raises(StructuredModelError) as exc: compile_structured_model(raw)
    assert exc.value.code=="invalid_name"

def test_scalar_passthrough_and_missing_declaration():
    raw={"name":"Scalar model","stocks":[{"id":"a","name":"A space","initial_value":3}]}
    assert compile_structured_model(raw)["model"]==raw
    with pytest.raises(StructuredModelError) as exc:
        compile_structured_model({"stocks":[{"name":"P","dimensions":["X"]}]})
    assert exc.value.code=="invalid_shape"

def test_quoted_references_cannot_escape_module_scope():
    raw=modules()
    raw["module_definitions"]["Tank"]["flows"][0]["equation"]='"speed" * A'
    with pytest.raises(StructuredModelError, match="Unknown reference speed"):
        compile_structured_model(raw)



def test_cyclic_module_port_bindings_are_rejected():
    raw={"module_definitions":{"Pass":{"inputs":["x"],"outputs":{"value":"x"}}},
        "modules":[{"name":"a","definition":"Pass","inputs":{"x":"b.value"}},
            {"name":"b","definition":"Pass","inputs":{"x":"a.value"}}]}
    with pytest.raises(StructuredModelError) as exc: compile_structured_model(raw)
    assert exc.value.code == "module_binding"

def test_depth_instance_and_sum_work_bounds():
    definitions={}
    for i in range(10):
        definitions["M"+str(i)]={"modules":[{"name":"inner","definition":"M"+str(i+1)}]} if i < 9 else {}
    raw={"module_definitions":definitions,"modules":[{"name":"outer","definition":"M0"}]}
    with pytest.raises(StructuredModelError) as exc: compile_structured_model(raw)
    assert exc.value.code == "resource_limit"
    raw={"module_definitions":{"Empty":{}},"modules":[{"name":"i"+str(i),"definition":"Empty"} for i in range(129)]}
    with pytest.raises(StructuredModelError) as exc: compile_structured_model(raw)
    assert exc.value.code == "resource_limit"
    raw={"dimensions":[{"name":"D","elements":["v"+str(i) for i in range(1000)]}],
        "variables":[{"name":"Array","dimensions":["D"],"equation":"1"},
            {"name":"Total","equation":" + ".join(["SUM(Array[D])"]*200)}]}
    with pytest.raises(StructuredModelError) as exc: compile_structured_model(raw)
    assert exc.value.code == "resource_limit"

@pytest.mark.parametrize("raw", [
    {"dimensions":{}},
    {"stocks":{}},
    {"dimensions":[{"name":"D","elements":["a"]}],"stocks":[{"name":"P","dimensions":[{}]}]},
    {"modules":[{"name":"x","definition":{}}],"module_definitions":{}},
    {"modules":[{"name":"x","definition":"A","inputs":[]}],"module_definitions":{"A":{}}},
    {"modules":[{"name":"x","definition":"A"}],"module_definitions":{"A":{"tables":[{}]}}},
])
def test_malformed_structured_shapes_raise_diagnostics(raw):
    # Empty metadata is a compatible scalar passthrough; malformed types aren't.
    with pytest.raises(StructuredModelError):
        compile_structured_model(raw)


def test_scalar_model_dump_defaults_do_not_trigger_lowering():
    raw=Model(name="scalar",stocks=[{"id":"a","name":"A space","initial_value":2}]).model_dump(mode="json")
    for elem in raw["stocks"]:
        elem.update(dimensions=[],equations={},initial_values={})
    raw.update(dimensions=[],modules=[],module_definitions={})
    assert compile_structured_model(raw)["model"] == raw


def test_sum_markers_cannot_capture_declared_variable():
    raw={"dimensions":[{"name":"D","elements":["a","b"]}],
        "variables":[{"name":"x","dimensions":["D"],"equation":"1"},
            {"name":"__structured_sum_0","equation":"9"},
            {"name":"Total","equation":"SUM(x[D]) + __structured_sum_0"}]}
    values=run(dict(compile_structured_model(raw)["model"],name="collision"))
    assert values["Total"][0] == 11

def test_sum_inside_quoted_name_is_not_interpreted_and_time_step_builtin():
    raw={"dimensions":[{"name":"D","elements":["a"]}],
        "variables":[{"name":"x","equation":"1"},{"name":"t","equation":'"SUM(x)" + TIME_STEP'}]}
    with pytest.raises(StructuredModelError,match="Expected a declared element reference"):
        compile_structured_model(raw)
    raw["variables"][1]["equation"]="TIME_STEP"
    assert run(dict(compile_structured_model(raw)["model"],name="dt"))["t"][0] == .25


def test_identifier_bounds_and_duplicate_original_ids():
    for field in ("name","member","instance"):
        raw={"dimensions":[{"name":"D","elements":["a"]}],"variables":[{"name":"x","equation":"1"}]}
        if field=="name":raw["dimensions"][0]["name"]="x"*129
        elif field=="member":raw["dimensions"][0]["elements"]=["x"*129]
        else:raw.update(module_definitions={"M":{}},modules=[{"name":"x"*129,"definition":"M"}])
        with pytest.raises(StructuredModelError):compile_structured_model(raw)
    raw={"dimensions":[{"name":"D","elements":["a"]}],"stocks":[{"id":"same","name":"A"},{"id":"same","name":"B"}]}
    with pytest.raises(StructuredModelError) as exc:compile_structured_model(raw)
    assert exc.value.code=="duplicate_id"


@pytest.mark.parametrize("where",["instance","dimension","element","body"])
def test_unknown_structural_semantics_are_not_silently_discarded(where):
    raw=modules()
    raw["dimensions"]=[{"name":"D","elements":["a"]}]
    if where=="instance":raw["modules"][0]["dimensions"]=["D"]
    elif where=="dimension":raw["dimensions"][0]["mapping"]={"a":"b"}
    elif where=="element":raw["module_definitions"]["Tank"]["stocks"][0]["nonnegative"]=True
    else:raw["module_definitions"]["Tank"]["unsupported_semantics"]={}
    with pytest.raises(StructuredModelError) as exc:compile_structured_model(raw)
    assert exc.value.code=="unsupported_semantics"


def test_original_id_cannot_redirect_another_stock_name():
    raw={"dimensions":[{"name":"D","elements":["a"]}],
        "stocks":[{"id":"B","name":"A"},{"id":"c","name":"B"}],
        "flows":[{"name":"f","to_stock":"B","equation":"1"}]}
    with pytest.raises(StructuredModelError) as exc:compile_structured_model(raw)
    assert exc.value.code=="ambiguous_id"


def test_scalar_alias_collisions_fail_during_structured_compilation():
    raw={"dimensions":[{"name":"D","elements":["a","A"]}],
        "variables":[{"name":"x","dimensions":["D"],"equation":"1"}]}
    with pytest.raises(StructuredModelError) as exc:compile_structured_model(raw)
    assert exc.value.code=="ambiguous_name"
