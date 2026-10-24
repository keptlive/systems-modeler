# Verification

Run in the repository root, without production credentials:

```sh
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests --ignore=tests/test_models.py -q
node scripts/check_frontend.cjs
node scripts/check_simulation_state.cjs
node scripts/check_workbench_v15.cjs
node scripts/check_series_controls.cjs
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 13250
# In a second terminal:
PYTHONPATH=. .venv/bin/python scripts/check_mcp.py --stdio
PYTHONPATH=. .venv/bin/python scripts/audit_library.py --full --tracked-only --output operations/library-full.json
PYTHONPATH=. .venv/bin/python scripts/triage_library.py --audit operations/library-full.json --output operations/library-investigation.json
```

`check_mcp.py` uses real SDK clients and verifies initialization, discovery, tools, analytical results, errors, resources and prompts over Streamable HTTP, SSE and stdio. It never calls a paid AI provider or writes library files. Set `--url https://stockandflow.live` for the public transport checks; omit `--stdio` when only testing that deployment.

API and frontend tests now use real assertions; API mutations run against a disposable model directory. Pytest 9 supplies the preservation suite's subtests fixture. The separately run `tests/test_models.py` aggregate intentionally remains red while unresolved corpus definitions fail: excluding it from the regression command does not classify those models as correct. The full tracked-library audit above records every failure. The model loader searches categorized directories recursively. Full audit failures are investigation findings, not targets to fix by zero substitution or arbitrary equation changes.

Browser acceptance covers library search/details/import, model editing, settings and both integrators, saving/reloading copies, JSON/XMILE export/import, Chart/Analytics/AI Insights, chart controls/scenarios/fullscreen, mobile controls and library deep links/downloads. Verify visible results after each interaction and inspect console errors. Agent-driven MCP operation is the default workflow; optional server-side AI requires a separately approved working provider credential.

Version 1.5 adds a 44-name advanced-function matrix with analytic reference trajectories, a traced corpus capability inventory and a small independently checked positive-model contract. See `ADVANCED-FUNCTION-REVIEW-1.5.md` and `CORPUS-TEST-CONTRACT-1.5.md`. A function's static presence, actual invocation, finite completion and scientific source fidelity are separate evidence categories.
# Version 1.3 additional verification

Version1.3 adds `tests/test_model_investigation.py`, `tests/test_repair_manifest.py` and `node scripts/check_simulation_state.cjs`. The full compatibility command is:

```sh
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_engine_review.py tests/test_regressions.py tests/test_xmile_features.py tests/test_xmile_roundtrip.py tests/test_input_validation.py tests/test_analytics.py tests/test_workspaces.py tests/test_model_investigation.py tests/test_repair_manifest.py
node scripts/check_frontend.cjs
node scripts/check_simulation_state.cjs
PYTHONPATH=. .venv/bin/python scripts/check_mcp.py --url http://127.0.0.1:13250 --stdio
```

Use `scripts/audit_library.py --full --random-seed 42 --output operations/library-full-v130.json` for a reproducible audit. Preserve earlier evidence and write each release to a new output file. The diagnostics CLI checks failed definitions and finite-run concerns at original/finer grids and optional RK4; it never writes definitions. Four source-backed repairs have independent reference/analytic checks and a hash-bound change receipt.
