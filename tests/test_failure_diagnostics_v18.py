"""Cause propagation must retain actual evaluation/lazy-branch semantics."""
import math
import pytest
from app.core.equations import EquationError, safe_eval
from app.core.model import Model
from app.core.simulator import simulate
from app.core.failure_diagnostics import failure_payload
from app.core.validation import inspect_inputs


def failure(variables, **kwargs):
    model=Model(variables=variables,time_settings={"end":1,"dt":1},**kwargs)
    with pytest.raises(EquationError) as caught:simulate(model)
    return caught.value,failure_payload(caught.value)


def test_domain_failure_comes_before_its_downstream_unknowns_and_keeps_original_name():
    error,payload=failure([{"name":"Output","equation":'"Actual Rate"+1'},
                           {"name":"Actual Rate","equation":"1/0"}])
    assert payload["root_errors"][0]["element"]=="Actual Rate"
    assert payload["root_errors"][0]["code"]=="division_by_zero"
    assert payload["blocked_errors"][0]["element"]=="Output"
    assert payload["blocked_errors"][0]["waiting_for"]=="Actual Rate"
    assert "Unknown variable" not in str(error)
    assert "__xmile_id_" not in str(error)


def test_missing_external_input_is_a_root_not_an_algebraic_cycle():
    _,payload=failure([{"name":"A","equation":"B+1"},{"name":"B","equation":"Missing+1"}])
    assert payload["root_errors"][0]["symbol"]=="Missing"
    assert payload["root_errors"][0]["code"]=="unknown_variable"
    assert payload["blocked_errors"][0]["root_cause"]=={"code":"unknown_variable","element":"B"}


def test_actual_lazy_path_does_not_invent_static_cycle():
    _,payload=failure([{"name":"A","equation":"IF(1,1/0,B)"},{"name":"B","equation":"A+1"}])
    assert [r["code"] for r in payload["root_errors"]]==["division_by_zero"]
    assert payload["blocked_errors"][0]["element"]=="B"


def test_actual_cycle_with_downstream_reports_cycle_members_without_fake_missing_input():
    _,payload=failure([{"name":"Output","equation":"A"},{"name":"A","equation":"B+1"},{"name":"B","equation":"A+1"}])
    assert payload["root_errors"]==[{"code":"algebraic_cycle","elements":["A","B"],
      "message":"Cyclic dependencies among unresolved values; no algebraic loop solver is selected"}]
    assert all(r["root_cause"]["code"]=="algebraic_cycle" for r in payload["blocked_errors"])


@pytest.mark.parametrize("equation,code",[
 ("(-1)^.5","non_real_result"),("SQRT(-1)","domain_error"),("1e308^2","numeric_overflow"),
 ("STEP(50)","function_signature"),("RANDOM()","function_signature"),("'Growing'","unsupported_expression")])
def test_primary_error_codes(equation,code):
    _,payload=failure([{"name":"X","equation":equation}])
    assert payload["root_errors"][0]["code"]==code


def test_authored_equation_instead_of_encoded_parser_tokens():
    with pytest.raises(EquationError) as caught:safe_eval('"Long Source Name"/0',{"Long Source Name":1})
    assert '"Long Source Name"/0' in str(caught.value)
    assert "__xmile_id_" not in str(caught.value)


def test_capacity_is_not_classified_as_invalid_equations():
    model=Model(variables=[{"name":"X","equation":"1"}],time_settings={"end":100001,"dt":1})
    with pytest.raises(EquationError) as caught:simulate(model)
    payload=failure_payload(caught.value)
    assert payload["code"]=="capacity_exceeded" and payload["category"]=="capacity"
    assert payload["requested"]==100001 and payload["limit"]==100000


def test_investigate_exposes_structured_runtime_failure():
    from app.core.diagnostics import investigate_model
    model=Model(variables=[{"name":"X","equation":"1/0"}],time_settings={"end":1,"dt":1})
    row=investigate_model(model,max_runs=1)["baseline"]
    assert row["status"]=="failed"
    assert row["failure"]["root_errors"][0]["code"]=="division_by_zero"


def test_stock_initializer_does_not_create_a_hidden_derivative():
    model=Model(stocks=[{"id":"x","name":"X","equation":"2+TIME"}],time_settings={"end":1,"dt":1})
    report=inspect_inputs(model,numerical_check=False)
    assert report["valid"]
    assert {"disconnected_stock","no_dynamic_stocks"}<={i["code"] for i in report["issues"]}
    assert simulate(model).values["X"]==[2,2]


def test_attached_flow_and_alias_endpoint_prevent_false_disconnected_warning():
    model=Model(stocks=[{"id":"x","name":"X"}],flows=[{"name":"Input","to_stock":"X","equation":"1"}])
    assert "disconnected_stock" not in {i["code"] for i in inspect_inputs(model,False)["issues"]}


def test_pure_identifier_cache_preserves_unicode_and_bounds_long_input_retention():
    from app.core.equations import canonical_name, _canonical_name
    assert canonical_name("Straße")=="strasse"
    assert canonical_name("Cafe\u0301\nRate")==canonical_name("CAFÉ_Rate")=="café_rate"
    before=_canonical_name.cache_info().currsize
    assert canonical_name("A"*1025)=="a"*1025
    assert _canonical_name.cache_info().currsize==before


def test_self_loop_using_id_and_name_is_not_a_stock_changing_flow():
    model=Model(stocks=[{"id":"x","name":"X"}],
                flows=[{"name":"Loop","from_stock":"x","to_stock":"X","equation":"1"}])
    assert "disconnected_stock" in {i["code"] for i in inspect_inputs(model,False)["issues"]}
    assert len(set(simulate(model).values["X"]))==1
