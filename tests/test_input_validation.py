"""Input checks retain provenance and distinguish computation from science."""
from fastapi.testclient import TestClient
from contextlib import nullcontext
from app.main import app
from app.core.model import Model
from app.core.validation import inspect_inputs
from app.storage import models as storage


def test_missing_parameter_reports_exact_input_without_saving(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "MODELS_DIR", str(tmp_path))
    model = Model(variables=[{"name": "Output", "equation": "missing_rate * 10"}])
    report = inspect_inputs(model)
    assert not report["valid"]
    assert any("missing_rate" in issue["message"] for issue in report["issues"])
    assert report["scientific_validation"] == "not established"
    assert not list(tmp_path.iterdir())


def test_zero_initial_values_and_units_are_review_flags_not_invented_fixes():
    model = Model(stocks=[{"name": "Population", "initial_value": 0}])
    report = inspect_inputs(model)
    codes = {issue["code"] for issue in report["issues"]}
    assert report["valid"] and "all_stocks_zero" in codes and "units_unverified" in codes
    assert model.stocks[0].initial_value == 0


def test_provenance_survives_api_create_update_get(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "MODELS_DIR", str(tmp_path))
    # REST-only test: the SDK's HTTP manager lifespan is one-shot per app process.
    with nullcontext(TestClient(app)) as client:
        response = client.post("/api/models", json={"name": "Source test", "source": "https://example.org/record",
                               "reference": "Original paper", "variables": [{"name": "Rate", "equation": "1", "units": "people/year"}]})
        assert response.status_code == 200
        model = response.json()
        assert model["source"] == "https://example.org/record"
        updated = client.put('/api/models/' + model['id'], json={"name": "Changed", "tables": None})
        assert updated.status_code == 200
        fetched = client.get('/api/models/' + model['id']).json()
        assert fetched["reference"] == "Original paper"
        assert fetched["variables"][0]["units"] == "people/year"
        report = client.post("/api/validate", json={"model_id": model["id"]}).json()
        assert report["inputs"]["source"] == model["source"]


def test_partial_ai_modification_retains_unmentioned_inputs_and_units(monkeypatch):
    from app.llm import modifier
    monkeypatch.setattr(modifier, "call_llm", lambda *args, **kwargs: '{"name":"Changed","variables":[{"name":"Rate","equation":"2"}],"time_settings":{"end":2}}')
    model = Model(source="https://example.org/source", reference="Original source",
                  stocks=[{"id": "s", "name": "Stock", "initial_value": 1}],
                  variables=[{"id": "r", "name": "Rate", "equation": "1", "units": "kg/year"}],
                  time_settings={"end": 1, "dt": .1, "integration_method": "rk4"})
    changed = modifier.modify_model(model, "Change Rate to 2")
    assert changed.source == model.source and changed.reference == model.reference
    assert changed.stocks == model.stocks
    assert changed.variables[0].units == "kg/year" and changed.variables[0].id == "r"
    assert changed.time_settings.dt == .1 and changed.time_settings.integration_method == "rk4"


def test_categorized_update_and_delete_do_not_duplicate_or_resurrect(tmp_path, monkeypatch):
    from app.core.model import ModelUpdate
    monkeypatch.setattr(storage, "MODELS_DIR", str(tmp_path))
    category = tmp_path / "test"
    category.mkdir()
    original = Model(id="review-test", name="Original")
    path = category / "review-test.json"
    path.write_text(original.model_dump_json())
    assert storage.update_model(original.id, ModelUpdate(name="Edited")).name == "Edited"
    assert len(list(tmp_path.rglob("*.json"))) == 1
    assert storage.get_model(original.id).name == "Edited"
    assert storage.delete_model(original.id)
    assert storage.get_model(original.id) is None


def test_nonfinite_numeric_input_is_rejected_without_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "MODELS_DIR", str(tmp_path))
    client = TestClient(app)
    response = client.post('/api/models', content='{"stocks":[{"name":"X","initial_value":1e309}]}',
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert not list(tmp_path.iterdir())


def test_optional_ai_provider_exception_is_not_exposed(monkeypatch):
    import pytest
    from app.llm import generator
    def failure(*args,**kwargs):raise RuntimeError('private provider credential must never be exposed')
    monkeypatch.setattr(generator,'_call_llm',failure)
    with pytest.raises(generator.LLMError,match='Connect your own agent') as caught:
        generator.call_llm([])
    assert 'private provider credential' not in str(caught.value)


def test_seed_survives_storage_and_xmile_and_rejects_coercion(tmp_path, monkeypatch):
    import pytest
    from app.core.model import TimeSettings
    from app.core.xmile_generator import generate_xmile
    from app.core.xmile_parser import parse_xmile
    monkeypatch.setattr(storage, "MODELS_DIR", str(tmp_path))
    model = Model(time_settings={"random_seed": 0},
                  variables=[{"name": "Draw", "equation": "RANDOM(0,1)"}])
    saved = storage.create_model(model)
    assert storage.get_model(saved.id).time_settings.random_seed == 0
    assert parse_xmile(generate_xmile(model)).time_settings.random_seed == 0
    for invalid in [True, 1.5, "42", -1, 4294967296]:
        with pytest.raises(ValueError):
            TimeSettings(random_seed=invalid)


def test_investigate_api_preserves_model_and_reports_finer_grids(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "MODELS_DIR", str(tmp_path))
    model = Model(stocks=[{"id":"s","name":"X","initial_value":1}],
                  flows=[{"name":"Growth","equation":"X","to_stock":"s"}],
                  time_settings={"end":1,"dt":.25})
    before = model.model_dump()
    client = TestClient(app)
    response = client.post('/api/investigate',json={"model":model.model_dump(mode="json")})
    assert response.status_code == 200
    report = response.json()
    assert len(report["runs"]) == 3
    assert [run["settings"]["dt"] for run in report["runs"]] == [.25,.125,.0625]
    assert all(run["status"] == "completed" for run in report["runs"])
    assert report["scientific_validation"] == "not established"
    assert report["comparisons"][1]["maximum_scaled_stock_difference"] < report["comparisons"][0]["maximum_scaled_stock_difference"]
    assert model.model_dump() == before and not list(tmp_path.iterdir())
    assert client.post('/api/investigate',json={}).status_code == 422


def test_seeded_api_run_replays_effective_seed():
    client = TestClient(app)
    model = {"variables":[{"name":"Draw","equation":"RANDOM(0,1)"}],
             "time_settings":{"end":1,"dt":.25}}
    first = client.post('/api/simulate',json={"model":model})
    assert first.status_code == 200
    seed = first.json()["random_seed"]
    assert isinstance(seed,int)
    model["time_settings"]["random_seed"] = seed
    second = client.post('/api/simulate',json={"model":model})
    assert second.json()["values"] == first.json()["values"]


def test_scenario_receipt_records_actual_common_seed(monkeypatch):
    from app import mcp_server
    model = Model(variables=[{"name":"Draw","equation":"RANDOM(0,1)"}],
                  time_settings={"end":1,"dt":.25,"random_seed":41})
    monkeypatch.setattr(mcp_server, "resolve_model", lambda *args: model)
    report = mcp_server.compare_scenarios("fixture", [{"name":"A"},{"name":"B"}], random_seed=42)
    assert report["settings"]["random_seed"] == report["random_seed"] == 42
    assert report["scenario_random_seeds"] == {"A":42,"B":42}
    assert report["scenarios"]["A"] == report["scenarios"]["B"]
    assert model.time_settings.random_seed == 41
