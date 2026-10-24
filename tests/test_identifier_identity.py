"""Literal names, unique legacy fallback, and complete declaration ownership."""
import json
import pytest
from app.core.equations import safe_eval,EquationError,SimulationContext,symbol_identity,canonical_name,resolve_name
from app.core.model import Model
from app.core.simulator import simulate
from app.core.units import analyze_units
from app.core.validation import inspect_inputs
from app.core.feedback_analysis import analyze_feedback
from app.core.xmile_generator import generate_xmile
from app.core.xmile_parser import parse_xmile

@pytest.mark.parametrize("name",["A-B","A\u2002B","Cash$Balance"])
def test_literal_identity_preserves_punctuation(name):
    assert symbol_identity(name)!=symbol_identity(name.replace("-","_").replace("\u2002","_").replace("$","_"))
    assert canonical_name(name)==canonical_name(name.replace("-","_").replace("\u2002","_").replace("$","_"))

@pytest.mark.parametrize("expression,want",[("Cash$1e+3",5),("Cash$1e-3",-1),("Cash$$Balance+1",3),("Cash$e\u0301+1",3)])
def test_unquoted_dollar_physical_identifier_span(expression,want):
    name=expression[:-2]
    assert safe_eval(expression,{name:2})==want

@pytest.mark.parametrize("expression",["$Cash+1","Cash $ Balance+1","Cash$ Balance+1"])
def test_dollar_does_not_join_whitespace_or_leading_dollar(expression):
    with pytest.raises(EquationError):safe_eval(expression,{"Cash$Balance":2})

def test_generated_identifier_prefix_cannot_capture_authored_name():
    encoded="__xmile_id_"+b"Cash$Balance".hex()
    assert safe_eval(f"Cash$Balance+{encoded}",{"Cash$Balance":2,encoded:7})==9
    assert safe_eval('"Cash$Balance"+1',{"Cash$Balance":2})==3

def test_exact_owner_blocks_unresolved_alias_fallback():
    context=SimulationContext();context.declared_symbols=("A-B","A_B")
    with pytest.raises(EquationError,match="Unknown variable"):
        safe_eval('"A_B"',{"A-B":1},context)
    assert safe_eval('"A_B"',{"A-B":1,"A_B":2},context)==2
    with pytest.raises(EquationError,match="Ambiguous"):
        safe_eval('"A!B"',{"A-B":1,"A_B":2})
    assert safe_eval("Pre_Service_Teachers+1",{"Pre-Service Teachers":2})==3

@pytest.mark.parametrize("solver",["euler","rk4","radau"])
def test_distinct_state_flow_init_table_units_and_feedback(solver):
    m=Model(stocks=[{"id":"x","name":"Store-A","initial_value":0,"equation":'"Initial-A"',"units":"kg"},
                    {"id":"y","name":"Store_A","initial_value":0,"equation":'"Initial_A"',"units":"kg"}],
      flows=[{"name":"Flow-A","equation":'"Curve-A"(1)',"to_stock":"x","units":"kg/second"},
             {"name":"Flow_A","equation":'"Curve_A"(1)',"to_stock":"y","units":"kg/second"}],
      variables=[{"name":"Initial-A","equation":"2","units":"kg"},{"name":"Initial_A","equation":"5","units":"kg"}],
      tables=[{"name":"Curve-A","points":[[0,1],[2,1]],"input_units":"1","output_units":"kg/second"},
              {"name":"Curve_A","points":[[0,2],[2,2]],"input_units":"1","output_units":"kg/second"}],
      time_settings={"end":1,"dt":.25,"integration_method":solver,"units":"second"})
    before=m.model_dump(mode="json");r=simulate(m)
    assert r.values["Store-A"]==pytest.approx([2+t for t in r.time],abs=1e-9)
    assert r.values["Store_A"]==pytest.approx([5+2*t for t in r.time],abs=1e-9)
    assert inspect_inputs(m)["valid"] and analyze_units(m)["status"]=="consistent"
    assert analyze_feedback(m,r)["samples"]
    out=parse_xmile(generate_xmile(m)); result=simulate(out)
    assert result.time==r.time and result.values==r.values and result.report_values==r.report_values
    assert out.time_settings.model_dump()==m.time_settings.model_dump()
    for kind in ('stocks','flows','variables'):
        assert [(v.name,v.equation,v.units) for v in getattr(out,kind)]==[(v.name,v.equation,v.units) for v in getattr(m,kind)]
    assert [(t.name,t.points,t.input_units,t.output_units) for t in out.tables]==[(t.name,t.points,t.input_units,t.output_units) for t in m.tables]
    assert m.model_dump(mode="json")==before

def test_forward_exact_dependencies_and_lazy_branch_cycles():
    m=Model(variables=[{"name":"A-B","equation":"Later"},{"name":"A_B","equation":"2"},
       {"name":"Later","equation":"7"},{"name":"Output","equation":'"A-B"+"A_B"'}],time_settings={"end":1,"dt":.25})
    assert simulate(m).values["Output"]==[9]*5
    m.variables[0].equation='IF(1,7,"A_B")';m.variables[1].equation='"A-B"+1'
    assert simulate(m).values["A_B"]==[8]*5
    m.variables[0].equation='"A_B"';m.variables[1].equation='"A-B"'
    with pytest.raises(EquationError,match="Unresolved"):simulate(m)

def test_new_legacy_collision_random_streams_are_distinct_and_replayable():
    m=Model(variables=[{"name":"A-B","equation":"RANDOM_UNIFORM(0,1)"},{"name":"A_B","equation":"RANDOM_UNIFORM(0,1)"}],
       time_settings={"end":2,"dt":.25,"random_seed":314})
    a,b=simulate(m),simulate(m)
    assert a.values==b.values and a.values["A-B"]!=a.values["A_B"]

def test_reports_do_not_capture_punctuation_distinct_numeric_symbol():
    m=Model(variables=[{"name":"A-B","equation":"2"},{"name":"A_B","role":"report","equation":"'label'"},
       {"name":"Output","equation":'"A-B"+1'}],time_settings={"end":1,"dt":.25})
    r=simulate(m);assert r.values["Output"]==[3]*5 and r.report_values["A_B"]==["label"]*5
    m.variables[2].equation='"A_B"+1'
    with pytest.raises(EquationError,match="report outputs"):simulate(m)

@pytest.mark.parametrize("pair",[("A B","A_B"),("A\u00a0B","A_B"),("e\u0301","é"),("k3","K3")])
def test_true_semantic_collisions_remain_errors(pair):
    m=Model(variables=[{"name":n,"equation":"1"} for n in pair])
    with pytest.raises(EquationError,match="unique"):simulate(m)


def test_rng_namespace_cannot_collide_with_authored_symbol():
    names=["A-B","A_B","__strict_symbol_612d62",":strict:612d62"]
    m=Model(variables=[{"name":n,"equation":"RANDOM_UNIFORM(0,1)"} for n in names],time_settings={"end":1,"dt":.25,"random_seed":812})
    run=simulate(m);assert run.values==simulate(m).values
    assert len({tuple(v) for v in run.values.values()})==4


def test_failure_diagnostics_keep_distinct_blocked_dependency_owners():
    m=Model(variables=[{"name":"A-B","equation":"Missing"},{"name":"A_B","equation":"1/0"},{"name":"First","equation":chr(34)+"A-B"+chr(34)},{"name":"Second","equation":"A_B"}])
    with pytest.raises(EquationError) as error:simulate(m)
    blocked={r["element"]:r["waiting_for"] for r in error.value.details["blocked_errors"]}
    assert blocked=={"First":"A-B","Second":"A_B"}
