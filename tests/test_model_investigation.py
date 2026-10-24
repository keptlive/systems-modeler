"""Investigation must explain experiments without changing inputs or hiding failures."""
import json
import math

import pytest

from app.core.model import Model, TimeSettings
from app.core import diagnostics as d
from app.core.simulator import simulate


def decay(method="euler", dt=.2):
    return Model(id="decay-test", name="Analytic decay", stocks=[{"id":"stock","name":"Amount","initial_value":1}],
                 flows=[{"name":"Loss","equation":"Amount","from_stock":"stock"}],
                 time_settings={"start":0,"end":1,"dt":dt,"integration_method":method})


def test_refinements_preserve_horizon_and_show_expected_euler_differences():
    model=decay()
    before=model.model_dump_json()
    report=d.investigate_model(model)
    assert [row["settings"]["dt"] for row in report["runs"]] == [.2,.1,.05]
    assert all(row["settings"]["end"] == 1 and row["scope"] == "full supplied horizon" for row in report["runs"])
    assert all(row["status"] == "completed" for row in report["runs"])
    changes=[row["maximum_scaled_stock_difference"] for row in report["comparisons"]]
    assert changes[0] > changes[1] > 0
    assert report["budget"]["total_element_intervals_upper_bound"] == 3_000_000
    assert model.model_dump_json() == before
    assert report["scientific_validation"] == "not established"
    assert not report["source_changed"]
    json.dumps(report,allow_nan=False)


def test_rk4_refinement_reports_small_error_without_scientific_claim():
    report=d.investigate_model(decay("rk4"))
    assert report["timestep_assessment"]["status"] == "small_differences_on_checked_grids"
    assert report["runs"][0]["stocks"][0]["final"] == pytest.approx(math.exp(-1),rel=2e-5)


def test_missing_parameter_does_not_repeat_identical_invalid_runs(monkeypatch):
    model=Model(variables=[{"name":"Output","equation":"missing_parameter * 2"}])
    calls=[]
    original=d.simulate
    def tracked(*args):
        calls.append(1)
        return original(*args)
    monkeypatch.setattr(d,"simulate",tracked)
    report=d.investigate_model(model)
    assert len(calls) == 1
    assert report["baseline"]["status"] == "failed"
    assert all(row["status"] == "not_attempted" for row in report["runs"][1:])
    assert report["equation_evidence"]["undefined_symbols"][0]["undefined_symbols"] == ["missing_parameter"]


def test_large_grid_is_not_replaced_with_short_smoke_horizon(monkeypatch):
    model=decay(dt=.000001)
    monkeypatch.setattr(d,"simulate",lambda *args:pytest.fail("Oversized grids should not run"))
    report=d.investigate_model(model)
    assert all(row["status"] == "not_attempted" for row in report["runs"])
    assert all(row["settings"]["end"] == 1 for row in report["runs"])


def test_normal_random_alias_does_not_receive_deterministic_convergence_claim():
    model=Model(variables=[{"name":"Noise","equation":"NORMAL(0,1)"}],time_settings={"end":1,"dt":.2})
    report=d.investigate_model(model)
    assert report["equation_evidence"]["stochastic"]
    assert all(row["status"] == "not_attempted" for row in report["runs"][1:])
    assert any("coupled" in warning for warning in report["warnings"])


def test_lookup_named_normal_is_not_a_random_call():
    model=Model(variables=[{"name":"Output","equation":"NORMAL(TIME)"}],
                tables=[{"name":"NORMAL","points":[[0,0],[1,1]]}],time_settings={"end":1,"dt":.2})
    report=d.investigate_model(model)
    assert not report["equation_evidence"]["stochastic"]
    assert all(row["status"] == "completed" for row in report["runs"])


def test_closed_transfer_sum_and_negative_values_are_separate_evidence():
    model=Model(stocks=[{"id":"a","name":"A","initial_value":1},{"id":"b","name":"B","initial_value":0}],
                flows=[{"name":"Transfer","equation":"2","from_stock":"a","to_stock":"b"}],time_settings={"end":1,"dt":.25})
    report=d.investigate_model(model)
    baseline=report["baseline"]
    conservation=baseline["conservation"][0]
    assert conservation["initial_total"] == conservation["final_total"] == 1
    assert conservation["max_absolute_drift"] == 0
    lead=baseline["domain_leads"][0]
    assert lead["code"] == "negative_stock_values" and lead["minimum"] == -1
    assert "signed" in lead["interpretation"]
    assert model.stocks[0].initial_value == 1


def test_unconnected_stocks_raise_transcription_review_lead():
    report=d.investigate_model(Model(stocks=[{"name":"Population","initial_value":10}]),max_runs=1)
    assert report["baseline"]["domain_leads"][0]["code"] == "stocks_without_attached_flows"


def test_comparisons_use_physical_times_with_short_last_step():
    model=decay(dt=.3)
    coarse=simulate(model)
    finer=simulate(model,TimeSettings(start=0,end=1,dt=.15))
    comparison=d.compare_runs(coarse,finer,model)
    assert comparison["per_stock"][0]["compared_samples"] == 5
    assert 0 < comparison["maximum_scaled_stock_difference"] < .1


def test_model_hash_ignores_automatic_timestamps_but_tracks_equations():
    a,b=decay(),decay()
    a.flows[0].id=b.flows[0].id
    assert d.model_hash(a) == d.model_hash(b)
    b.flows[0].equation="Amount * 2"
    assert d.model_hash(a) != d.model_hash(b)


@pytest.mark.parametrize("runs", [0,4,-1,True,1.5,"3"])
def test_caller_cannot_expand_work_budget(runs):
    with pytest.raises(ValueError,match="max_runs"):
        d.investigate_model(decay(),runs)


def test_source_change_is_reported(monkeypatch):
    hashes=iter([{"source":"before"},{"source":"after"}])
    monkeypatch.setattr(d,"source_hashes",lambda:next(hashes))
    report=d.investigate_model(decay(),max_runs=1)
    assert report["source_changed"] and any("changed" in text for text in report["warnings"])

def test_repaired_sir_matches_all_primary_canonical_samples_offline():
    import csv
    import hashlib
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    fixture=root/"tests/fixtures/sir-sdx-canonical.csv"
    metadata=json.loads(fixture.with_suffix(".json").read_text())
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == metadata["fixture_sha256"]
    model=Model.model_validate_json((root/"models/other/sir.json").read_text())
    result=simulate(model)
    with fixture.open(newline="") as stream:
        rows=list(csv.DictReader(stream))
    assert len(rows) == len(result.time) == metadata["samples"] == 3201
    for actual_time, row in zip(result.time,rows):
        assert abs(actual_time-float(row["Time"])) <= metadata["comparison_tolerance"]["maximum_time_label_rounding"]
    for name in ("Susceptible","Infectious","Recovered"):
        expected=[float(row[name]) for row in rows]
        scale=max(map(abs,expected))
        assert max(abs(actual-reference) for actual,reference in zip(result.values[name],expected))/scale <= metadata["comparison_tolerance"]["maximum_scaled_stock_difference"]
    assert result.values["Susceptible"][0] == 1000
    assert result.values["Infectious"][0] == 5
    assert max(abs(sum(result.values[name][i] for name in ("Susceptible","Infectious","Recovered"))-1005) for i in range(len(result.time))) < 1e-9


def test_repaired_si_matches_source_initialization_reporting_and_analytic_solution():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    model=Model.model_validate_json((root/"models/other/si.json").read_text())
    baseline=simulate(model)
    assert baseline.values["Susceptible"][0] == 10000
    assert baseline.values["Infected"][0] == 1
    assert baseline.values["Cumulative_Reported_Cases"][0] == 0
    assert baseline.values["Infected"][1] == pytest.approx(1.04375)
    assert baseline.values["Cumulative_Reported_Cases"][1] == pytest.approx(.04375)
    assert max(abs(s+i-10001) for s,i in zip(baseline.values["Susceptible"],baseline.values["Infected"])) < 1e-9
    assert max(abs(cases-(infected-1)) for cases,infected in zip(baseline.values["Cumulative_Reported_Cases"],baseline.values["Infected"])) < 1e-9
    refined=simulate(model,model.time_settings.model_copy(update={"integration_method":"rk4","dt":model.time_settings.dt/2}))
    expected=[10001/(1+10000*math.exp(-.35*10001/10000*t)) for t in refined.time]
    assert max(abs(value-reference) for value,reference in zip(refined.values["Infected"],expected))/10001 < 2e-8


def test_feature_parser_failure_remains_diagnostic_not_service_error(monkeypatch):
    def invalid(*args):
        raise ValueError("Unsupported feature in malformed equation")
    monkeypatch.setattr(d,"equation_features",invalid)
    report=d.investigate_model(decay())
    assert report["equation_evidence"]["syntax"][0]["stage"] == "engine_feature_check"
    assert report["runs"][1]["status"] == "not_attempted"

@pytest.mark.parametrize('model_id',['sir-simple','sales-agency-fit-adjustment'])
def test_reconstructed_cookbook_models_against_independent_references(model_id):
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    fixtures=json.loads((root/'tests/fixtures/cookbook-source-reference.json').read_text())['models']
    model=Model.model_validate_json((root/f'models/other/{model_id}.json').read_text())
    baseline=simulate(model)
    assert baseline.time[-1] == model.time_settings.end
    if model_id=='sir-simple':
        assert len(model.stocks)==4 and len(model.flows)==3
        assert baseline.values['susceptible'][0]==1000
        assert baseline.values['infectious'][0]==5
        assert baseline.values['infectious'][1] > 5
        assert max(abs(s+i+r-1005) for s,i,r in zip(baseline.values['susceptible'],baseline.values['infectious'],baseline.values['recovered'])) < 1e-9
        assert max(abs(c-(1000-s)) for c,s in zip(baseline.values['cumulative_cases'],baseline.values['susceptible'])) < 1e-9
        settings=model.time_settings.model_copy(update={'integration_method':'rk4','dt':.03125})
        checked=simulate(model,settings)
        for row in fixtures[model_id]['reference']:
            index=round((row['time']-settings.start)/settings.dt)
            assert checked.time[index] == row['time']
            for name in ('susceptible','infectious','recovered','cumulative_cases'):
                assert abs(checked.values[name][index]-row[name])/1005 < 1e-8
    else:
        assert len(model.flows)==4
        assert baseline.values['Sales_Agents_with_Good_Fit'][-1] > 8
        settings=model.time_settings.model_copy(update={'integration_method':'rk4'})
        checked=simulate(model,settings)
        for t,good,poor,productivity in zip(checked.time,checked.values['Sales_Agents_with_Good_Fit'],checked.values['Sales_Agents_with_Poor_Fit'],checked.values['Total_Productivity']):
            expected_good=.2*48*(1-math.exp(-t/48))
            expected_poor=.8*6*(1-math.exp(-t/6))
            assert good == pytest.approx(expected_good,abs=1e-9)
            assert poor == pytest.approx(expected_poor,abs=1e-9)
            assert productivity == pytest.approx(expected_good+.5*expected_poor,abs=1e-9)

def test_dt_dependent_initial_domain_failure_can_recover_on_finer_grid():
    model=Model(stocks=[{'name':'X','equation':'SQRT(1-DT)'}],time_settings={'start':0,'end':4,'dt':2})
    report=d.investigate_model(model)
    assert report['equation_evidence']['references_time_step']
    assert [row['status'] for row in report['runs']] == ['failed','completed','completed']
    assert report['runs'][1]['stocks'][0]['initial'] == 0
    assert report['runs'][2]['stocks'][0]['initial'] == pytest.approx(math.sqrt(.5))
    assert any('initial conditions' in text for text in report['warnings'])