# Stock & Flow

Agent-driven stock-and-flow pages, explicit Euler/RK4/Radau simulation, a browsable example library and a Model Context Protocol server.

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

The current 1.9 audit runs all 1,078 checked-in definitions at their full default horizons: **1,050 complete and 28 fail explicitly**, with no newly failing defaults. All 47 previous failures were investigated; 19 definitions are repaired. Tests compare reconstructed source dynamics, conservation, analytic results and appropriate refinements. Completion is not empirical validation. See the [failure register](docs/FAILURE-REGISTER-1.9.md), [release evidence](docs/RELEASE-1.9.md), and source partitions [A](docs/CORPUS-REPAIRS-1.9-A.md), [B](docs/CORPUS-REPAIRS-1.9-B.md), [C](docs/CORPUS-REPAIRS-1.9-C.md). Public status badges apply only to exact audited model bytes. Preserve additional user models during release.

## API and MCP

- `GET /api/models/catalog` is the small searchable index; `GET /api/models/{id}` fetches definitions. Legacy `GET /api/models` remains available.
- Model CRUD and XMILE import/export remain available under `/api/models`.
- `POST /api/simulate`, `/api/validate`, `/api/analyze/statistics`, `/api/analyze` and `/api/llm/{generate,modify}` serve the workbench.
- Connect an HTTP-capable MCP client to **https://stockandflow.live/mcp/**. Legacy SSE remains **https://stockandflow.live/mcp/sse**. `/mcp/info` reports transports.
- Local stdio: `.venv/bin/python -m app.mcp_server` from the repository directory.

Bring your own agent: `open_workspace` returns a private visible page, `inspect_workspace` confirms its state, `edit_workspace_elements` preserves unmentioned inputs, `update_workspace_model` replaces an explicitly intended full draft, `run_workspace` publishes the exact run, `set_workspace_view` shows the desired view, and `close_workspace` revokes the session. HTTP/SSE page tools require no server-side AI account. Expected revisions and browser acknowledgements prevent blind overwrites and false success claims. See [the page protocol and modeling lessons](docs/AGENT-WORKSPACES.md).

The nine existing MCP tools remain: `list_models`, `get_model`, `validate_model`, `simulate_model`, `compare_scenarios`, `analyze_model`, `export_model_xmile`, `generate_model_from_description`, `modify_existing_model`. Resources `systems://guide` and `systems://models/{id}` plus the `investigate_system` prompt guide evidence-based use. Numerical tools do not save models; optional AI tools return unsaved drafts. Local stdio supports these numerical/library tools; private page sessions require HTTP/SSE.

The engine rejects unresolved equations, ambiguous names, nonfinite inputs and unsupported semantics. Limits are 500 explicit elements, 100,000 intervals, 100,001 retained samples, one million retained scalar values and one million work units including hidden stages and method cost. Smoothing and fixed-duration material delays support Euler/RK4; random functions and fixed-history delays remain Euler-only. XMILE support is a scalar subset; arrays, nested models, queues, conveyors and explicit nonnegative constraints are rejected rather than silently lost.

Version 1.4 reconciled 63 public definitions through source restoration, mathematical checks and citation/limitation corrections. Version 1.5 adds 218 advanced tests across all 44 advertised function names, repairs pulse and extreme lookup behavior, and improves the existing workbench with command search, run context and desktop/mobile chart selection. No model definitions changed in 1.5. Known citation mismatches remain visible in inspection and MCP validation. See [the release evidence](docs/RELEASE-1.5.md).

Version 1.6 refines diagram elements and the studio interface, makes element renames preserve dependent equations, restores three source-backed lookup definitions, and fixes mobile fullscreen and input-focus behavior. The regression run passes 595 tests plus 18 subtests, with three documented identifier-compatibility expected failures. See [1.6 evidence and limitations](docs/RELEASE-1.6.md).

Version 1.7 reconciles all 134 prior public failures, refines Analytics and exports, and supports bounded fine time grids. The clean public regression suite passes 673 tests plus 18 preservation subtests, with three documented expected failures. See [1.7 evidence](docs/RELEASE-1.7.md).

Version 1.8 adds opt-in bounded Radau for stiff continuous systems, exact bounded binomial sampling, and readable root/blocked failure diagnostics. Independent review found and fixed missed time-driven lookup pulses; unsupported inputs fail explicitly. Radau output-grid comparisons are distinguished from tolerance convergence. See [engine contracts](docs/ENGINE-CAPABILITIES-1.8.md) and [independent review](docs/INDEPENDENT-REVIEW-1.8.md).

Version 1.9 also hardens flow accumulation, RK4 arithmetic, delayed history, scalar domains, initializer resolution and solver work accounting. Partial request settings preserve saved values, and failed runs export exact replay evidence. Radau rejects uncertified state events and lookup forcing; five saved defaults now use independently checked explicit grids. XMILE export translates verified standard functions and refuses lossy conversions. See the hardening evidence for [integration](docs/ENGINE-HARDENING-1.9-A.md), [equations](docs/ENGINE-HARDENING-1.9-B.md), [API/MCP](docs/ENGINE-HARDENING-1.9-C.md), [failure reproduction](docs/ENGINE-HARDENING-1.9-ROOT.md) and [solver repairs](docs/CORPUS-HARDENING-REPAIRS-1.9-B.md).

Version 1.9 adds explicit report-only categorical outputs and fixed-period recurrence contracts. Labels never enter numerical dynamics. Weekly/discrete models reject fractional periods or solver overrides that would change their meaning. JSON preserves both features; XMILE export explicitly rejects unsupported contracts. Large charts initially select stocks while retaining every series. See [engine contracts](docs/ENGINE-REPORTS-AND-DISCRETE-1.9.md).

## Development and operations

[Architecture](docs/ARCHITECTURE.md) · [Analytics](docs/ANALYTICS.md) · [Testing](docs/TESTING.md) · [UI direction](docs/UI-DIRECTION.md) · [UI QA](docs/UI-QA.md)

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests --ignore=tests/test_models.py
node scripts/check_frontend.cjs
node scripts/check_simulation_state.cjs
node scripts/check_workbench_v15.cjs
node scripts/check_series_controls.cjs
PYTHONPATH=. python scripts/check_mcp.py --stdio
PYTHONPATH=. python scripts/audit_library.py --full --tracked-only --output operations/library-full.json
```

Run the application before the MCP client check. Node.js is needed for actual JavaScript parser checks. API tests use disposable storage. The separate `tests/test_models.py` aggregate intentionally fails while unresolved library defaults remain; the full audit records each failure instead of treating it as a passing regression. Browser acceptance and alternate-engine/device limitations are recorded separately; responsive emulation is not proof of physical iOS/Android compatibility. Never synchronize `models/`, `models.db`, `.env` or Git credentials over production. Reviewed per-file model repairs require exact old/new hashes and backups; preserve all other model data.
