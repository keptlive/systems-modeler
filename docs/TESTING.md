# Verification

Run in the repository root, without production credentials:

```sh
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q tests/test_regressions.py tests/test_xmile_features.py tests/test_engine_review.py tests/test_xmile_roundtrip.py tests/test_input_validation.py tests/test_analytics.py tests/test_workspaces.py
node scripts/check_frontend.cjs
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 13250
# In a second terminal:
PYTHONPATH=. .venv/bin/python scripts/check_mcp.py --stdio
PYTHONPATH=. .venv/bin/python scripts/audit_library.py --full --output operations/library-full.json
PYTHONPATH=. .venv/bin/python scripts/triage_library.py --audit operations/library-full.json --output operations/library-investigation.json
```

`check_mcp.py` uses real SDK clients and verifies initialization, discovery, tools, analytical results, errors, resources and prompts over Streamable HTTP, SSE and stdio. It never calls a paid AI provider or writes library files. Set `--url https://stockandflow.live` for the public transport checks; omit `--stdio` when only testing that deployment.

The legacy API test functions return `(success, message)` tuples, so merely collecting them with pytest does not establish correctness. Their runner must inspect those tuples. The previous model loader also missed categorized models; it now searches recursively. Full audit failures are investigation findings, not targets to fix by zero substitution or arbitrary equation changes.

Browser acceptance covers library search/details/import, model editing, settings and both integrators, saving/reloading copies, JSON/XMILE export/import, Chart/Analytics/AI Insights, chart controls/scenarios/fullscreen, mobile controls and library deep links/downloads. Verify visible results after each interaction and inspect console errors. Run one bounded real AI generation/modification check against the configured production provider, separate from numerical tests, and record its outcome without credentials.
