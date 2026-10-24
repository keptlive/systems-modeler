from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.model import Model, ModelCreate, TimeSettingsPatch
from app.core.simulator import simulate
from app.core.validation import inspect_inputs
from app.core.xmile_generator import generate_xmile
from app.storage import models as storage


def regional():
    return {"name": "Regional growth", "dimensions": [{"name": "Region", "elements": ["North", "South"]}],
            "stocks": [{"name": "Population", "units": "person", "dimensions": ["Region"],
                        "initial_value": 20, "initial_values": {"North": 10}}],
            "flows": [{"name": "Births", "units": "person/year", "dimensions": ["Region"],
                       "equation": "Population[Region] * 0.1", "to_stock": "Population[Region]"}],
            "variables": [{"name": "Total", "units": "person", "equation": "SUM(Population[Region])"}],
            "time_settings": {"start": 0, "end": 1, "dt": 1, "units": "year"}}


def test_authored_structure_survives_save_read_run_and_json(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "MODELS_DIR", str(tmp_path))
    raw = regional()
    saved = storage.create_model(ModelCreate(**raw))
    loaded = storage.get_model(saved.id)
    before = deepcopy(loaded.model_dump())
    result = simulate(loaded)
    assert result.values["Total"] == [30, 33]
    assert result.values["Population[North]"] == [10, 11]
    assert result.integration_diagnostics["structured_source_map"]
    assert loaded.model_dump() == before
    assert loaded.dimensions == raw["dimensions"]
    assert loaded.stocks[0].initial_values == {"North": 10}
    assert loaded.connectors == []
    assert Model.model_validate_json(loaded.model_dump_json()).model_dump() == before
    with pytest.raises(ValueError, match="preserve authored structure"):
        generate_xmile(loaded)


def test_structured_http_simulation_compilation_and_validation_do_not_mutate():
    raw = regional()
    before = deepcopy(raw)
    client = TestClient(app)
    result = client.post("/api/simulate", json={"model": raw})
    assert result.status_code == 200, result.text
    assert result.json()["values"]["Total"] == [30, 33]
    compiled = client.post("/api/compile", json={"model": raw})
    assert compiled.status_code == 200
    assert len(compiled.json()["source_map"]) == 5
    report = client.post("/api/validate", json={"model": raw})
    assert report.status_code == 200, report.text
    assert report.json()["valid"]
    assert report.json()["numerical_check"] == "completed_one_step"
    assert raw == before


def test_invalid_structure_has_actionable_http_error():
    raw = regional()
    raw["stocks"][0]["initial_values"] = {"East": 99}
    client = TestClient(app)
    for endpoint in ("simulate", "compile", "units"):
        response = client.post("/api/" + endpoint, json={"model": raw})
        assert response.status_code == 422
        assert "override" in response.text.lower()
    report = inspect_inputs(Model(**raw))
    assert not report["valid"]
    assert report["issues"][0]["code"] == "invalid_override"


def test_time_units_patch_does_not_reset_settings():
    model = Model(**regional())
    updated = TimeSettingsPatch(units="day").apply_to(model.time_settings)
    assert updated.units == "day"
    assert updated.end == model.time_settings.end
    assert TimeSettingsPatch(units=None).apply_to(updated).units is None
