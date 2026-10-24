"""Read-only v1.6 input-semantics findings; no engine/model repairs.

Passing tests pin supported/current documented behavior. Regression cases preserve literal identifier distinctions without weakening
existing case/standard-whitespace alias rules.
"""
import pytest
from app.core.equations import EquationError, safe_eval
from app.core.model import Model
from app.core.simulator import simulate

def output_model(variables=(), stocks=(), flows=(), start=0):
    return Model(variables=list(variables),stocks=list(stocks),flows=list(flows),
                 time_settings={"start":start,"end":start+2,"dt":.25})

@pytest.mark.parametrize("first,second",[
 ("k3","K3"),("a","A"),("Turnover Rate","Turnover Rate"),
 ("Angular Acceleration 1","Angular_Acceleration_1"),
 ("cash balance","CASH___BALANCE"),
])
def test_documented_case_and_whitespace_collisions_are_errors(first,second):
    m=output_model(variables=[{"name":first,"equation":"1"},{"name":second,"equation":".5"}])
    with pytest.raises(EquationError,match="unique"):simulate(m)

def test_source_symbols_can_be_translated_to_unique_semantic_names_without_changing_math():
    # The literal mathematical notation k3/(K3+1) is2/3 for k3=1,K3=.5.
    # A case-insensitive engine needs distinct semantic identifiers; it should
    # never silently take one of the two numeric values.
    m=output_model(variables=[
      {"name":"Kinetic Rate 3","equation":"1"},
      {"name":"Saturation Constant 3","equation":".5"},
      {"name":"Rate","equation":"Kinetic_Rate_3/(Saturation_Constant_3+1)"}])
    assert simulate(m).values["Rate"]==pytest.approx([2/3]*9)

@pytest.mark.parametrize("initial_aux",["Initial Susceptible","Initial Exposed","Initial Angle 1"])
def test_initial_named_auxiliary_is_not_an_implicit_stock_assignment(initial_aux):
    m=output_model(stocks=[{"id":"s","name":"Susceptible","initial_value":0}],
                   variables=[{"name":initial_aux,"equation":"100"}])
    r=simulate(m)
    assert r.values["Susceptible"]==[0]*9
    assert r.values[initial_aux]==[100]*9

def test_stock_initial_equation_overrides_numeric_placeholder_once_at_actual_start():
    m=output_model(start=5,
      stocks=[{"id":"s","name":"Population","initial_value":0,"equation":"Initial_Population"}],
      variables=[{"name":"Initial Population","equation":"100+TIME"}],
      flows=[{"name":"Arrivals","equation":"2","to_stock":"s"}])
    r=simulate(m)
    assert r.values["Population"]==pytest.approx([105+2*(t-5) for t in r.time])
    assert r.values["Initial Population"]==pytest.approx([100+t for t in r.time])

def test_initial_values_resolve_forward_dependencies_without_using_placeholder_values():
    m=output_model(start=3,
      stocks=[{"id":"a","name":"First","initial_value":999,"equation":"Second+1"},
              {"id":"b","name":"Second","initial_value":999,"equation":"Initial"}],
      variables=[{"name":"Initial","equation":"TIME*2"}])
    r=simulate(m)
    assert r.values["First"]==[7]*9
    assert r.values["Second"]==[6]*9

def test_invalid_initial_equation_does_not_fall_back_to_numeric_placeholder():
    m=output_model(stocks=[{"name":"X","initial_value":100,"equation":"Missing"}])
    with pytest.raises(EquationError,match="Missing"):simulate(m)

def test_genuine_initial_cycle_is_not_resolved_by_arbitrary_numeric_defaults():
    m=output_model(stocks=[
      {"name":"A","initial_value":1,"equation":"B"},
      {"name":"B","initial_value":2,"equation":"A"}])
    with pytest.raises(EquationError,match="Unresolved"):simulate(m)

def test_unused_undefined_ratio_still_invalidates_numeric_output():
    m=output_model(stocks=[{"id":"s","name":"Count","initial_value":0}],
      variables=[{"name":"Ratio","equation":"Count/Count"}],
      flows=[{"name":"Inflow","equation":"1","to_stock":"s"}])
    with pytest.raises(EquationError,match="Division by zero"):simulate(m)

def test_explicitly_defined_empty_state_reporting_convention_is_lazy():
    # A reporting convention is explicitly provided by this synthetic author;
    # this is not permission to insert the convention into scientific models.
    m=output_model(stocks=[{"id":"s","name":"Count","initial_value":0}],
      variables=[{"name":"Ratio","equation":"IF Count=0 THEN -1 ELSE Count/Count"}],
      flows=[{"name":"Inflow","equation":"1","to_stock":"s"}])
    r=simulate(m)
    assert r.values["Ratio"]==[-1]+[1]*8
    assert r.values["Count"]==pytest.approx(r.time)

def test_semantic_abbreviations_are_not_automatically_equivalent_names():
    m=output_model(stocks=[{"name":"Susceptible Population","initial_value":100}],
      variables=[{"name":"Rate","equation":"S*.1"}])
    with pytest.raises(EquationError,match="Unknown variable: S"):simulate(m)
    assert safe_eval("susceptible_population*.1",{"Susceptible Population":100})==10

def test_delay_third_argument_is_prehistory_not_order():
    m=output_model(variables=[
      {"name":"Fixed","equation":"DELAY(1,1,3)"},
      {"name":"Third Order","equation":"DELAYN(1,1,3,0)"}])
    r=simulate(m)
    assert r.values["Fixed"][:4]==[3]*4
    assert r.values["Fixed"][4:]==[1]*5
    assert r.values["Third Order"][0]==0
    assert r.values["Third Order"][:3]==[0]*3
    assert r.values["Third Order"][3]>0

def test_numeric_equation_language_does_not_support_string_diagnostics():
    m=output_model(variables=[{"name":"State","equation":"IF(1,'Growing','At Limit')"}])
    with pytest.raises(EquationError,match="constant type"):simulate(m)

def test_signed_stocks_are_not_globally_clamped_to_zero():
    m=output_model(stocks=[{"id":"x","name":"Signed Account","initial_value":1}],
      flows=[{"name":"Withdrawal","equation":"1","from_stock":"x"}])
    assert simulate(m).values["Signed Account"][-1]==-1

def test_strict_xmile_quoted_punctuation_identifiers_should_remain_distinct():
    m=output_model(variables=[
      {"name":"A-B","equation":"1"},{"name":"A_B","equation":"2"},
      {"name":"Output","equation":'"A-B"+"A_B"'}])
    assert simulate(m).values["Output"]==[3]*9

def test_strict_xmile_en_space_is_not_whitespace_alias():
    m=output_model(variables=[
      {"name":"A B","equation":"1"},{"name":"A_B","equation":"2"},
      {"name":"Output","equation":'"A B"+"A_B"'}])
    assert simulate(m).values["Output"]==[3]*9

def test_strict_xmile_unquoted_internal_dollar_identifier():
    assert safe_eval("Cash$Balance+1",{"Cash$Balance":2})==3

def test_quoted_dollar_name_is_current_workaround():
    assert safe_eval('"Cash$Balance"+1',{"Cash$Balance":2})==3
