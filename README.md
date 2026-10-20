# Stock & Flow

Agent-driven stock-and-flow pages, explicit Euler/RK4 simulation, a browsable example library and a Model Context Protocol server.

[Simulator](https://stockandflow.live) · [Library](https://stockandflow.org) · [Usage and MCP guide](https://stockandflow.live/guide)

The editor retains AI generation/modification, saved models, JSON/XMILE import and export, diagrams, scenario comparison, four chart types, statistics and mobile panels. Numerical tools work without an AI provider. AI drafts need input and source review before use.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 3250
```

Optional provider configuration is described in `.env.example` and `app/llm/`. Keep keys outside Git. The numerical engine never sends equations to a provider. `requirements-lock.txt` records the tested development environment; production compatibility was separately checked against its existing FastAPI/Pydantic versions.

## Validate models

Use **Settings → Check inputs** or `POST /api/validate` with `{"model_id":"..."}` or `{"model":{...}}`. Inspection covers names, references, syntax, initial values, flow endpoints, tables, settings and a short numerical run. Units and provenance are retained. Scientific validity is not established by these checks or by finite simulation output.

All 1,078 checked-in definitions were audited unchanged: 929 default runs complete and 149 fail explicitly. See [the input investigation](docs/MODEL-INVESTIGATION.md), [engine review](docs/ENGINE-REVIEW.md), and SHA-bound receipts in `operations/`. Public status badges apply only to the exact model bytes audited. Production also has additional user models; preserve them during release.

## API and MCP

- `GET /api/models/catalog` is the small searchable index; `GET /api/models/{id}` fetches definitions. Legacy `GET /api/models` remains available.
- Model CRUD and XMILE import/export remain available under `/api/models`.
- `POST /api/simulate`, `/api/validate`, `/api/analyze/statistics`, `/api/analyze` and `/api/llm/{generate,modify}` serve the workbench.
- Connect an HTTP-capable MCP client to **https://stockandflow.live/mcp/**. Legacy SSE remains **https://stockandflow.live/mcp/sse**. `/mcp/info` reports transports.
- Local stdio: `.venv/bin/python -m app.mcp_server` from the repository directory.

Bring your own agent: `open_workspace` returns a private visible page, `inspect_workspace` confirms its state, `edit_workspace_elements` preserves unmentioned inputs, `update_workspace_model` replaces an explicitly intended full draft, `run_workspace` publishes the exact run, `set_workspace_view` shows the desired view, and `close_workspace` revokes the session. HTTP/SSE page tools require no server-side AI account. Expected revisions and browser acknowledgements prevent blind overwrites and false success claims. See [the page protocol and modeling lessons](docs/AGENT-WORKSPACES.md).

The nine existing MCP tools remain: `list_models`, `get_model`, `validate_model`, `simulate_model`, `compare_scenarios`, `analyze_model`, `export_model_xmile`, `generate_model_from_description`, `modify_existing_model`. Resources `systems://guide` and `systems://models/{id}` plus the `investigate_system` prompt guide evidence-based use. Numerical tools do not save models; optional AI tools return unsaved drafts. Local stdio supports these numerical/library tools; private page sessions require HTTP/SSE.

The engine rejects unresolved equations, ambiguous names, nonfinite inputs and unsupported semantics. Limits are 500 explicit elements, 10,000 intervals and one million element-intervals including hidden stages. Delay/smoothing models currently require Euler. XMILE support is a scalar subset; arrays, nested models, queues, conveyors and explicit nonnegative constraints are rejected rather than silently lost.

## Development and operations

[Architecture](docs/ARCHITECTURE.md) · [Analytics](docs/ANALYTICS.md) · [Testing](docs/TESTING.md) · [UI direction](docs/UI-DIRECTION.md) · [UI QA](docs/UI-QA.md)

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests/test_engine_review.py tests/test_regressions.py tests/test_xmile_features.py tests/test_xmile_roundtrip.py tests/test_input_validation.py tests/test_analytics.py tests/test_workspaces.py
node scripts/check_frontend.cjs
PYTHONPATH=. python scripts/check_mcp.py --stdio
PYTHONPATH=. python scripts/audit_library.py --full --output operations/library-full.json
```

Run the application before the MCP client check. Browser acceptance and alternate-engine/device limitations are recorded separately; responsive emulation is not proof of physical iOS/Android compatibility. Never deploy `models/`, `models.db`, `.env` or Git credentials over production. Preserve prior features, back up scoped code/config files, and verify live API/MCP/browser journeys and model data hashes after release.
