"""Analytic stiff references, conservation, strict work and transport contracts."""
import math
import pytest
from pydantic import ValidationError
from app.core.model import Model, TimeSettings
from app.core.simulator import simulate
from app.core.equations import EquationError


def manufactured(**changes):
    settings={"start":0,"end":5,"dt":.25,"integration_method":"radau","rtol":1e-8,"atol":1e-11}
    settings.update(changes)
    return Model(stocks=[{"id":"x","name":"X","initial_value":1},
                         {"id":"y","name":"Y","initial_value":0}],
                 flows=[{"name":"DX","equation":"-1000*(X-COS(TIME))-SIN(TIME)","to_stock":"x"},
                        {"name":"DY","equation":"X","to_stock":"y"}],time_settings=settings)


def test_stiff_manufactured_cosine_and_integral_on_exact_saved_grid():
    result=simulate(manufactured())
    assert result.time==[i*.25 for i in range(21)]
    assert max(abs(x-math.cos(t)) for t,x in zip(result.time,result.values["X"]))<2e-8
    assert max(abs(y-math.sin(t)) for t,y in zip(result.time,result.values["Y"]))<2e-8
    evidence=result.integration_diagnostics
    assert evidence["model_evaluations"]>evidence["nfev"]+len(result.time)  # Jacobian probes included
    assert evidence["work_units"]==evidence["model_evaluations"]*4
    assert evidence["work_units"]<=1000000


def test_sparse_output_grid_does_not_force_a_stiff_explicit_step():
    model=Model(stocks=[{"id":"x","name":"X","initial_value":0}],
                flows=[{"name":"DX","equation":"30-X","to_stock":"x"}],
                time_settings={"end":1000000,"dt":1000,"integration_method":"radau"})
    result=simulate(model)
    assert result.time==[i*1000 for i in range(1001)]
    assert result.values["X"][0]==0
    assert max(abs(x-30) for x in result.values["X"][1:])<1e-7
    assert model.time_settings.dt==1000


def test_robertson_stiff_mass_action_against_independent_published_value_and_mass():
    # Classic Robertson test: t=40, A~.7158270687, B~9.18553476e-6.
    model=Model(stocks=[{"id":"a","name":"A","initial_value":1},
                         {"id":"b","name":"B"},{"id":"c","name":"C"}],
        flows=[{"name":"AB","equation":".04*A","from_stock":"a","to_stock":"b"},
               {"name":"BA","equation":"10000*B*C","from_stock":"b","to_stock":"a"},
               {"name":"BC","equation":"30000000*B^2","from_stock":"b","to_stock":"c"}],
        time_settings={"end":40,"dt":.5,"integration_method":"radau","rtol":1e-9,"atol":1e-12})
    result=simulate(model)
    assert result.values["A"][-1]==pytest.approx(.7158270687,abs=5e-9)
    assert result.values["B"][-1]==pytest.approx(9.18553476e-6,abs=1e-11)
    assert max(abs(a+b+c-1) for a,b,c in zip(*(result.values[n] for n in ["A","B","C"])))<2e-12
    assert min(min(result.values[n]) for n in ["A","B","C"])>=0


@pytest.mark.parametrize("expression",["RANDOM(0,1)","IF(1,0,RANDOM(0,1))","SMOOTH(1,1)","DELAY(1,1)","STEP(1,1)","PULSE(1,1)","RAMP(1,1)"])
def test_history_stochastic_and_held_inputs_are_explicitly_unsupported(expression):
    model=manufactured()
    model.variables=Model(variables=[{"name":"Probe","equation":expression}]).variables
    with pytest.raises(EquationError) as caught:simulate(model)
    assert caught.value.code=="unsupported_method_features"


def test_named_graphical_function_takes_precedence_over_step_primitive():
    model=manufactured()
    model.tables=Model(tables=[{"name":"STEP","points":[[0,1],[5,2]],"interpolation":"continuous"}]).tables
    model.variables=Model(variables=[{"name":"Probe","equation":"STEP(X)"}]).variables
    result=simulate(model)
    assert result.values["Probe"][-1]==pytest.approx(1+math.cos(5)/5,abs=1e-8)


def test_work_limit_interrupts_solver_without_partial_results(monkeypatch):
    import app.core.adaptive as adaptive
    monkeypatch.setattr(adaptive,"MAX_WORK_UNITS",100)
    with pytest.raises(EquationError) as caught:simulate(manufactured())
    assert caught.value.code=="capacity_exceeded"
    assert caught.value.details["resource"]=="work_units"
    assert caught.value.details["requested"]>100


def test_output_evaluations_count_even_for_constant_stocks(monkeypatch):
    import app.core.adaptive as adaptive
    monkeypatch.setattr(adaptive,"MAX_WORK_UNITS",100)
    model=Model(stocks=[{"name":"X","initial_value":1}],time_settings={"end":1000,"dt":1,"integration_method":"radau"})
    with pytest.raises(EquationError) as caught:simulate(model)
    assert caught.value.code=="capacity_exceeded"


@pytest.mark.parametrize("update",[{"rtol":1e-15},{"rtol":.2},{"rtol":float("nan")},{"atol":0},{"atol":float("inf")}])
def test_tolerances_are_validated_instead_of_scipy_silently_clipping(update):
    with pytest.raises(ValidationError):TimeSettings(**update)


def test_radau_json_roundtrip_and_explicit_xmile_boundary():
    from app.core.xmile_generator import generate_xmile
    model=manufactured(rtol=1e-7,atol=1e-10)
    copy=Model.model_validate_json(model.model_dump_json())
    assert copy.time_settings==model.time_settings
    from app.core.xmile_parser import parse_xmile
    before=model.model_dump(mode='json'); original=simulate(model)
    restored=parse_xmile(generate_xmile(model)); result=simulate(restored)
    assert restored.time_settings.model_dump()==model.time_settings.model_dump()
    assert result.time==original.time and result.values==original.values
    assert result.report_values==original.report_values
    assert [v.equation for v in restored.flows]==[v.equation for v in model.flows]
    assert model.model_dump(mode='json')==before


def test_mcp_explicit_method_and_tolerance_overrides():
    from app.mcp_server import simulate_model
    model=manufactured(integration_method="euler")
    result=simulate_model(model_json=model.model_dump(mode="json"),integration_method="radau",rtol=1e-8,atol=1e-11)
    assert result["settings"]["integration_method"]=="radau"
    assert result["settings"]["rtol"]==1e-8
    assert result["integration_diagnostics"]["method"]=="radau"
    assert model.time_settings.integration_method=="euler"


def test_solver_rejects_invalid_diagnostic_without_hiding_or_zero_substitution():
    model=manufactured()
    model.variables=Model(variables=[{"name":"Undefined","equation":"1/0"}]).variables
    with pytest.raises(EquationError) as caught:simulate(model)
    assert caught.value.code=="unresolved_equations"
    assert caught.value.details["root_errors"][0]["code"]=="division_by_zero"


@pytest.mark.parametrize("equation",[
 "IF(TIME>10 AND TIME<11,1,0)",
 "IF THEN ELSE(TIME>10,1,0)",
 "IF(Clock>10 AND Clock<11,1,0)",
 "FLOOR(TIME)","MOD(TIME,2)","TIME%2","TIME//2"])
def test_narrow_time_pulses_and_indirect_aliases_cannot_be_silently_skipped(equation):
    # A solver can step directly from9 to12 with zero derivative on both sides,
    # missing the whole unit-area pulse. Rejection is explicit; no fake zero run.
    model=Model(stocks=[{"id":"x","name":"X"}],
                variables=[{"name":"Clock","equation":"Clock2+1"},{"name":"Clock2","equation":"TIME-1"}],
                flows=[{"name":"Input","equation":equation,"to_stock":"x"}],
                time_settings={"end":100,"dt":20,"integration_method":"radau"})
    with pytest.raises(EquationError) as caught:simulate(model)
    assert caught.value.code=="unsupported_method_features"
    assert caught.value.details["time_discontinuities"]


def test_stock_dependent_conditional_is_not_confused_with_explicit_time_alias():
    model=manufactured()
    # Both branches meet at X=2; the manufactured cosine stays below it.
    model.flows[0].equation="IF(X<2,-1000*(X-COS(TIME))-SIN(TIME),-1000*(2-COS(TIME))-SIN(TIME))"
    result=simulate(model)
    assert max(abs(x-math.cos(t)) for t,x in zip(result.time,result.values["X"]))<2e-8


def test_uncertified_state_branch_is_rejected_even_if_reference_never_crosses():
    model=manufactured()
    model.flows[0].equation="IF(X<2,-1000*(X-COS(TIME))-SIN(TIME),0)"
    with pytest.raises(EquationError) as caught:simulate(model)
    assert caught.value.code=="unsupported_method_features"
    assert caught.value.details["state_discontinuities"]
