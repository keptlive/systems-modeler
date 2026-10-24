"""Isolated consolidation evidence; no active model mutations."""
import hashlib,json
from pathlib import Path
import pytest
from app.core.model import Model
from app.core.simulator import simulate
from app import mcp_server as server
ROOT=Path(__file__).resolve().parents[2]
FOLDER=Path(__file__).parent
PLAN=json.loads((FOLDER/"PLAN.json").read_text())
SCENARIOS=json.loads((FOLDER/"SCENARIOS.json").read_text())["arguments"]["scenarios"]


def canonical():
    return Model.model_validate_json((FOLDER/"canonical/may-chaos-population-eco.json").read_text())


def compatibility(identity,result):
    values=result.values;p=values["r"];x=values["Population"]
    if identity=="may-logistic-chaos":
        equilibrium=[1-1/r for r in p]
        return {"Population":x,"Population_Change":values["Population Change"],
                "Growth_Rate":p,"Equilibrium_Population":equilibrium,
                "Deviation":[value-e for value,e in zip(x,equilibrium)]}
    if identity=="may-ecological-chaos-eco":
        return {"Population":x,"Population_Change":values["Population Change"],"r":p,
                "Growth_Rate":[r*(1-value) for r,value in zip(p,x)]}
    mapping={"Instantaneous Log Slope":"Lyapunov Exponent Estimate",
             "Coarse Parameter Range Code":"Dynamic Regime"}
    return {mapping.get(name,name):values for name,values in result.values.items()}


@pytest.mark.parametrize("index",[0,1,2])
def test_every_legacy_default_output_reproduces_under_explicit_compatibility(index):
    row=PLAN["actions"][index];scenario=SCENARIOS[index]
    before=Model.model_validate_json((ROOT/row["proposed_archive"]).read_text())
    old=simulate(before);new=canonical()
    next(v for v in new.variables if v.id=="var-r").equation=str(scenario["parameters"]["r"])
    result=simulate(new)
    assert result.time==old.time and len(result.time)==101
    assert result.values["Population"]==old.values["Population"]
    assert compatibility(row["id"],result)==old.values


def test_existing_actual_compare_scenarios_tool_accepts_all_presets_without_saving(monkeypatch):
    source=canonical();snapshot=source.model_dump_json()
    monkeypatch.setattr(server.storage,"get_model",lambda key:source if key==source.id else None)
    def forbidden(*args,**kwargs):raise AssertionError("Scenario comparison must not save")
    monkeypatch.setattr(server.storage,"create_model",forbidden)
    monkeypatch.setattr(server.storage,"update_model",forbidden)
    report=server.compare_scenarios(source.id,SCENARIOS,random_seed=42)
    assert set(report["scenarios"])=={row["name"] for row in SCENARIOS}
    assert report["settings"]["discrete_period"]==1
    for row,scenario in zip(PLAN["actions"],SCENARIOS):
        old=simulate(Model.model_validate_json((ROOT/row["proposed_archive"]).read_text()))
        assert report["scenarios"][scenario["name"]]["Population"]==server.summarize(old)["Population"]
    assert source.model_dump_json()==snapshot


def test_exact_archive_payloads_and_single_replacement_two_retirements():
    assert len(PLAN["actions"])==3
    assert [row["action"] for row in PLAN["actions"]]==["retire","retire","replace"]
    for row in PLAN["actions"]:
        data=(ROOT/row["proposed_archive"]).read_bytes()
        assert hashlib.sha256(data).hexdigest()==row["before_sha256"]
        assert json.loads(data)["id"]==row["id"]
        if row["action"]=="replace":
            assert hashlib.sha256((ROOT/row["source"]).read_bytes()).hexdigest()==row["after_sha256"]
    assert PLAN["proposed_public_count"]==PLAN["baseline_public_count"]-2
    assert PLAN["proposed_live_count"]==PLAN["baseline_live_count"]-2


def test_full_reference_receipts_bind_all_three_legacy_defaults():
    evidence=json.loads((FOLDER/"DEFAULT-REFERENCES.json").read_text())
    assert evidence["canonical_sha256"]==PLAN["actions"][2]["after_sha256"]
    assert len(evidence["references"])==3
    for row,reference in zip(PLAN["actions"],evidence["references"]):
        original=simulate(Model.model_validate_json((ROOT/row["proposed_archive"]).read_text()))
        assert reference["legacy_id"]==row["id"]
        assert reference["legacy_before_sha256"]==row["before_sha256"]
        assert reference["time"]==original.time
        assert reference["legacy_outputs"]==original.values
        encoded=json.dumps(original.values["Population"],separators=(",",":")).encode()
        assert hashlib.sha256(encoded).hexdigest()==reference["population_float64_json_sha256"]



def test_visible_presets_and_old_ids_are_in_canonical_description():
    description=json.loads((ROOT/PLAN["actions"][2]["source"]).read_text())["description"]
    for token in ("3.7", "3.8", "3.9", "Inspect", "Equation", "Save Run", "Compare",
                  "may-logistic-chaos", "may-ecological-chaos-eco", "Growth_Rate"):
        assert token in description
