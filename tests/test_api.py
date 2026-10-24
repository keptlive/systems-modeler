"""
Test all API endpoints.
Uses FastAPI's TestClient for synchronous testing.
"""
import os
import sys
import json
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from unittest.mock import patch
import pytest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.api import models, simulate, llm
from app.storage import models as model_storage


@contextmanager
def isolated_client():
    """Keep every CRUD request in disposable storage, including manual runs."""
    # These are REST endpoint tests. A fresh API app avoids starting the shared,
    # one-shot MCP session manager or modifying its lifecycle for unrelated tests.
    application = FastAPI()
    application.include_router(models.router, prefix="/api/models")
    application.include_router(simulate.router, prefix="/api")
    application.include_router(llm.router, prefix="/api/llm")
    with TemporaryDirectory(prefix="systems-modeler-api-test-") as directory:
        with patch.object(model_storage, "MODELS_DIR", directory):
            with TestClient(application) as temporary_client:
                yield temporary_client


@pytest.fixture
def client():
    with isolated_client() as temporary_client:
        yield temporary_client


def _check_list_models(client) -> tuple:
    """Test GET /api/models - list all models."""
    try:
        response = client.get("/api/models")
        if response.status_code != 200:
            return False, f"Status {response.status_code}: {response.text}"

        data = response.json()
        if not isinstance(data, list):
            return False, f"Expected list, got {type(data)}"

        return True, f"Found {len(data)} models"
    except Exception as e:
        return False, str(e)


def _check_create_model(client) -> tuple:
    """Test POST /api/models - create a new model."""
    try:
        test_model = {
            "name": "API Test Model",
            "description": "Created by test suite",
            "stocks": [
                {
                    "id": "stock-1",
                    "name": "TestStock",
                    "initial_value": 100,
                    "equation": "",
                    "position": {"x": 100, "y": 100}
                }
            ],
            "flows": [],
            "variables": [],
            "connectors": [],
            "time_settings": {
                "start": 0,
                "end": 10,
                "dt": 0.5
            }
        }

        response = client.post("/api/models", json=test_model)
        if response.status_code not in (200, 201):
            return False, f"Status {response.status_code}: {response.text}"

        data = response.json()
        if not data.get("id"):
            return False, "No model ID returned"

        # Store for cleanup and other tests

        if data.get("name") != "API Test Model":
            return False, f"Model name mismatch: {data.get('name')}"

        return True, f"Model created with ID {data.get('id')[:8]}..."
    except Exception as e:
        return False, str(e)


def _check_get_model(client) -> tuple:
    """Test GET /api/models/{id} - get a specific model."""
    try:
        # First create a model
        test_model = {
            "name": "Get Test Model",
            "description": "For testing GET endpoint",
            "stocks": [],
            "flows": [],
            "variables": [],
            "connectors": [],
            "time_settings": {"start": 0, "end": 10, "dt": 0.5}
        }
        create_resp = client.post("/api/models", json=test_model)
        if create_resp.status_code not in (200, 201):
            return False, f"Failed to create model: {create_resp.text}"

        created = create_resp.json()
        model_id = created.get("id")

        # Then get it
        response = client.get(f"/api/models/{model_id}")
        if response.status_code != 200:
            return False, f"Status {response.status_code}: {response.text}"

        data = response.json()
        if data.get("name") != "Get Test Model":
            return False, f"Model name mismatch"

        return True, "Model retrieved successfully"
    except Exception as e:
        return False, str(e)


def _check_update_model(client) -> tuple:
    """Test PUT /api/models/{id} - update a model."""
    try:
        # First create a model
        test_model = {
            "name": "Update Test Model",
            "description": "Original description",
            "stocks": [],
            "flows": [],
            "variables": [],
            "connectors": [],
            "time_settings": {"start": 0, "end": 10, "dt": 0.5}
        }
        create_resp = client.post("/api/models", json=test_model)
        if create_resp.status_code not in (200, 201):
            return False, f"Failed to create model: {create_resp.text}"

        created = create_resp.json()
        model_id = created.get("id")

        # Update it
        update_data = {"description": "Updated description"}
        response = client.put(f"/api/models/{model_id}", json=update_data)
        if response.status_code != 200:
            return False, f"Status {response.status_code}: {response.text}"

        # Verify update
        response = client.get(f"/api/models/{model_id}")
        data = response.json()
        if data.get("description") != "Updated description":
            return False, "Description not updated"

        return True, "Model updated successfully"
    except Exception as e:
        return False, str(e)


def _check_delete_model(client) -> tuple:
    """Test DELETE /api/models/{id} - delete a model."""
    try:
        # First create a model
        test_model = {
            "name": "Delete Test Model",
            "description": "Will be deleted",
            "stocks": [],
            "flows": [],
            "variables": [],
            "connectors": [],
            "time_settings": {"start": 0, "end": 10, "dt": 0.5}
        }
        create_resp = client.post("/api/models", json=test_model)
        if create_resp.status_code not in (200, 201):
            return False, f"Failed to create model: {create_resp.text}"

        created = create_resp.json()
        model_id = created.get("id")

        # Delete it
        response = client.delete(f"/api/models/{model_id}")
        if response.status_code != 200:
            return False, f"Status {response.status_code}: {response.text}"

        # Verify deletion
        response = client.get(f"/api/models/{model_id}")
        if response.status_code != 404:
            return False, "Model still exists after deletion"

        return True, "Model deleted successfully"
    except Exception as e:
        return False, str(e)


def _check_simulate(client) -> tuple:
    """Test POST /api/simulate - run simulation."""
    try:
        test_model = {
            "id": "test-simulate-model",
            "name": "Simulate Test Model",
            "description": "For testing simulation",
            "stocks": [
                {
                    "id": "population",
                    "name": "Population",
                    "initial_value": 100,
                    "equation": "",
                    "position": {"x": 100, "y": 100}
                }
            ],
            "flows": [
                {
                    "id": "births",
                    "name": "Births",
                    "equation": "Population * 0.1",
                    "from_stock": None,
                    "to_stock": "population",
                    "position": {"x": 50, "y": 100}
                },
                {
                    "id": "deaths",
                    "name": "Deaths",
                    "equation": "Population * 0.05",
                    "from_stock": "population",
                    "to_stock": None,
                    "position": {"x": 150, "y": 100}
                }
            ],
            "variables": [],
            "connectors": [],
            "time_settings": {"start": 0, "end": 10, "dt": 0.5}
        }

        response = client.post("/api/simulate", json={"model": test_model})
        if response.status_code != 200:
            return False, f"Status {response.status_code}: {response.text}"

        data = response.json()
        if "time" not in data:
            return False, "Missing 'time' in response"
        if "values" not in data:
            return False, "Missing 'values' in response"
        if len(data["time"]) == 0:
            return False, "Empty time array"
        if "Population" not in data["values"]:
            return False, "Missing 'Population' in values"

        # Check population grew (birth rate > death rate)
        pop_values = data["values"]["Population"]
        if pop_values[-1] <= pop_values[0]:
            return False, "Population did not grow as expected"

        return True, f"Simulated {len(data['time'])} steps"
    except Exception as e:
        return False, str(e)


def _check_llm_status(client) -> tuple:
    """Test GET /api/llm/status - check LLM availability."""
    try:
        response = client.get("/api/llm/status")
        if response.status_code != 200:
            return False, f"Status {response.status_code}: {response.text}"

        data = response.json()
        if "available" not in data:
            return False, "Missing 'available' field"

        status = "available" if data["available"] else "unavailable"
        provider = data.get("provider", "none")
        return True, f"LLM {status}, provider: {provider}"
    except Exception as e:
        return False, str(e)


def test_list_models(client):
    success, message = _check_list_models(client)
    assert success, message

def test_create_model(client):
    success, message = _check_create_model(client)
    assert success, message

def test_get_model(client):
    success, message = _check_get_model(client)
    assert success, message

def test_update_model(client):
    success, message = _check_update_model(client)
    assert success, message

def test_delete_model(client):
    success, message = _check_delete_model(client)
    assert success, message

def test_simulate(client):
    success, message = _check_simulate(client)
    assert success, message

def test_llm_status(client):
    success, message = _check_llm_status(client)
    assert success, message


def test_api_storage_is_disposable():
    original_directory = model_storage.MODELS_DIR
    with isolated_client() as temporary_client:
        temporary_directory = Path(model_storage.MODELS_DIR)
        assert temporary_directory.resolve() != Path(original_directory).resolve()
        success, message = _check_create_model(temporary_client)
        assert success, message
        assert len(list(temporary_directory.glob("*.json"))) == 1
    assert model_storage.MODELS_DIR == original_directory
    assert not temporary_directory.exists()


def run_all_api_tests() -> dict:
    """Run all API tests and return results."""
    tests = [
        ("GET /api/models", _check_list_models),
        ("POST /api/models", _check_create_model),
        ("GET /api/models/{id}", _check_get_model),
        ("PUT /api/models/{id}", _check_update_model),
        ("DELETE /api/models/{id}", _check_delete_model),
        ("POST /api/simulate", _check_simulate),
        ("GET /api/llm/status", _check_llm_status),
    ]

    results = []
    passed = 0
    failed = 0

    for name, test_func in tests:
        with isolated_client() as temporary_client:
            success, message = test_func(temporary_client)
        results.append({
            "name": name,
            "success": success,
            "message": message
        })

        if success:
            passed += 1
            print(f"PASS: {name} - {message}")
        else:
            failed += 1
            print(f"FAIL: {name} - {message}")

    return {
        "passed": passed,
        "failed": failed,
        "total": len(tests),
        "results": results
    }


if __name__ == "__main__":
    print("=" * 50)
    print("API TESTS")
    print("=" * 50)

    results = run_all_api_tests()

    print("-" * 50)
    print(f"API: {results['passed']}/{results['total']} passing")

    if results['failed'] > 0:
        print("\nFAILURES:")
        for r in results['results']:
            if not r['success']:
                print(f"  - {r['name']}: {r['message']}")
        sys.exit(1)
    else:
        sys.exit(0)
