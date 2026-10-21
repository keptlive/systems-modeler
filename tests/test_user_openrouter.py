"""Request-scoped free routing, safe failures and structured output contracts."""
import json
from types import SimpleNamespace
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.llm import generator as g
from app.llm.credentials import UserAI

HEADERS = {"X-OpenRouter-Key": "test-only-placeholder", "X-OpenRouter-Model": "openrouter/free"}


def transport(monkeypatch, content="OK", status=200, finish="stop", error=None):
    calls = []
    class Client:
        def __init__(self, **kwargs):
            assert kwargs == {"timeout": 60.0, "follow_redirects": False}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            calls.append((url, kwargs))
            if error: raise error
            return httpx.Response(status, json={"choices": [{"finish_reason": finish, "message": {"content": content}}]})
    monkeypatch.setattr(httpx, "Client", Client)
    monkeypatch.setattr(g, "get_llm_client", lambda: pytest.fail("No server fallback allowed"))
    return calls


@pytest.mark.parametrize("headers", [{"X-OpenRouter-Key": ""}, {"X-OpenRouter-Model": "openrouter/free"}, {**HEADERS, "X-OpenRouter-Model": "paid/model"}])
def test_invalid_credentials_do_not_fall_back(headers, monkeypatch):
    monkeypatch.setattr(g, "get_llm_client", lambda: pytest.fail("Must not use server key"))
    assert TestClient(app).get("/api/llm/status", headers=headers).status_code == 400


def test_user_status_does_not_verify_or_disclose_key():
    response = TestClient(app).get("/api/llm/status", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["verified"] is False
    assert HEADERS["X-OpenRouter-Key"] not in response.text
    assert "test-only" not in repr(UserAI("test-only"))


def test_connection_uses_only_free_router(monkeypatch):
    calls = transport(monkeypatch)
    response = TestClient(app).post("/api/llm/test", headers=HEADERS)
    assert response.json()["verified"] is True
    payload = calls[0][1]["json"]
    assert payload["model"] == "openrouter/free"
    assert "models" not in payload and "route" not in payload
    assert payload["max_tokens"] == 64


@pytest.mark.parametrize("status,expected", [(401,401),(403,401),(429,429),(402,502),(500,502)])
def test_provider_errors_are_safe(monkeypatch, status, expected):
    transport(monkeypatch, status=status)
    response = TestClient(app).post("/api/llm/test", headers=HEADERS)
    assert response.status_code == expected
    assert HEADERS["X-OpenRouter-Key"] not in response.text


def test_timeout_safe(monkeypatch):
    transport(monkeypatch, error=httpx.ReadTimeout("credential-bearing upstream details"))
    response = TestClient(app).post("/api/llm/test", headers=HEADERS)
    assert response.status_code == 504 and "credential-bearing" not in response.text


@pytest.mark.parametrize("content,finish", [(None,"stop"),("", "stop"),("partial", "length")])
def test_incomplete_responses_rejected(monkeypatch, content, finish):
    transport(monkeypatch, content=content, finish=finish)
    assert TestClient(app).post("/api/llm/test", headers=HEADERS).status_code == 502


@pytest.mark.parametrize("text", ["[]", "null", "42", "{bad}", '{"value":NaN}', '```json\n{}', "prose {}"])
def test_json_must_be_complete_finite_object(text):
    with pytest.raises(g.LLMError): g.parse_model_json(text)


def test_fenced_json_supported():
    assert g.parse_model_json('```json\n{"stocks": []}\n```') == {"stocks": []}


def test_generate_and_modify_use_request_key(monkeypatch):
    client = TestClient(app)
    model = {"name":"Population", "stocks":[{"name":"Population", "initial_value":10}]}
    calls = transport(monkeypatch, content=json.dumps(model))
    generated = client.post("/api/llm/generate", headers=HEADERS, json={"description":"Population"})
    assert generated.status_code == 200, generated.text
    modified = client.post("/api/llm/modify", headers=HEADERS, json={"model":generated.json(), "modification":"Keep unchanged"})
    assert modified.status_code == 200, modified.text
    assert modified.json()["stocks"][0]["id"] == generated.json()["stocks"][0]["id"]
    assert len(calls) == 2
    assert all(call[1]["json"]["response_format"] == {"type":"json_object"} for call in calls)


@pytest.mark.parametrize("path", ["/api/analyze", "/api/analyze/ask"])
def test_analysis_user_key_and_safe_failure(monkeypatch, path):
    payload={"simulation_results":{"time":[0,1],"values":{"Population":[10,11]}},"question":"What changed?"}
    transport(monkeypatch, content=json.dumps({"summary":"Recorded growth.","insights":["Population rose."],"recommendations":["Check units."],"answer":"It rose by one."}))
    response=TestClient(app).post(path, headers=HEADERS, json=payload)
    assert response.status_code == 200 and response.json()["ai_used"] is True
    transport(monkeypatch, content="[]")
    response=TestClient(app).post(path, headers=HEADERS, json=payload)
    assert response.status_code == 502 and "test-only" not in response.text
