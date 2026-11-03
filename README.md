# Stock & Flow

> **Experimental.** Stock & Flow is an experimental research project, not a production modeling tool.
> For real system dynamics work, use **[Simlin](https://simlin.com)** ([source](https://github.com/bpowers/simlin)).
> Simlin's engine is written in Rust, and Simlin is faster, more complete and much better than this project.
>
> This repository is still worth visiting for its **[library of 1,000 example models](#model-library)**.

A browser-based stock-and-flow modeler with Euler, RK4 and Radau simulation, AI-assisted model drafting, an example model library and a Model Context Protocol (MCP) server.

[Simulator](https://stockandflow.live) · [Model library](https://stockandflow.org) · [Usage and MCP guide](https://stockandflow.live/guide) · [Documentation](docs/README.md) · [Changelog](CHANGELOG.md)

## Model library

The library has 1,000 examples, 997 dynamic models and three labeled static calculators, in 26 subject areas from economics and climate to epidemiology, physics and ecology.

- Each model is one JSON file in [`models/<subject>/`](models/), with its stocks, flows, variables, time settings, units and source reference.
- Browse them at [stockandflow.org](https://stockandflow.org), or fetch them through the API: `GET /api/models/catalog` for the index, `GET /api/models/{id}` for one model.
- To use a model in another tool such as Simlin, export it as XMILE. Export covers a scalar subset and refuses conversions that would lose information.

A model that runs to completion is not a validated model. Check its source before relying on it. How the library was built and checked: [curation decisions](docs/LIBRARY-CURATION.md), [reconstructions](docs/MODEL-RECONSTRUCTIONS-2026-10.md) and the [failure register](docs/FAILURE-REGISTER-1.9.md).

Scalar expression repairs preserve arithmetic in MDL imports, nested graphical functions and seeded random identities through XMILE round trips. Vensim-specific operations retain their own semantics. See [expression support and round-trip validation](docs/EXPRESSION-ROUNDTRIP.md).

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 3250
```

AI drafting is optional. Provider settings are described in `.env.example` and `app/llm/`; keep keys out of Git. The numerical engine never sends equations to a provider, and every numerical tool works without one. `requirements-lock.txt` records the tested development environment.

## What it does

- **Editor:** diagrams, saved models, JSON and XMILE import and export, conservative Vensim MDL import, scenario comparison, four chart types, statistics and mobile panels.
- **Engine:** Euler and RK4, opt-in Radau for stiff systems, [arrays and reusable modules](docs/STRUCTURED-MODELS.md), [dimensional checks](docs/DIMENSIONAL-ANALYSIS.md), [feedback analysis](docs/FEEDBACK-ANALYSIS.md) and [local parameter sensitivity](docs/LOCAL-SENSITIVITY.md).
- **Checks:** **Settings → Check inputs** or `POST /api/validate` inspects names, references, syntax, initial values, flow endpoints, tables, settings and a short run. These checks do not establish scientific validity.
- **Limits:** 500 explicit elements, 100,000 intervals and one million retained values per run. Unsupported constructs, such as XMILE queues, conveyors and nested models, are rejected rather than silently dropped.

Simlin remains faster on every workload measured in the [engine comparison](docs/ENGINE-COMPARISON.md). [Pinned Simlin observations](docs/COMPATIBILITY-REFERENCE-2026-10.md) record where the two engines agree and where they differ. This project has no Simlin runtime dependency and does not claim full Simlin or Vensim parity.

## API and MCP

- **REST:** model catalog and CRUD under `/api/models`, MDL import at `/api/models/import/mdl`, and `/api/simulate`, `/api/validate`, `/api/compile`, `/api/units`, `/api/feedback`, `/api/analyze` and `/api/analyze/statistics`.
- **Hosted MCP:** connect an HTTP-capable client to `https://stockandflow.live/mcp/`. Legacy SSE is at `/mcp/sse`, and `/mcp/info` lists transports.
- **Local MCP (stdio):** `.venv/bin/python -m app.mcp_server` from the repository directory.
- **Tools:** `list_models`, `get_model`, `validate_model`, `simulate_model`, `compare_scenarios`, `analyze_model`, `export_model_xmile`, `generate_model_from_description` and `modify_existing_model`, plus [native engine tools](docs/NATIVE-ENGINE-MCP.md).
- **Agent workspaces:** over HTTP or SSE, an agent can open a private page, edit and run a model, and show the result. See [the page protocol](docs/AGENT-WORKSPACES.md).

Numerical tools never save models. AI tools return unsaved drafts.

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest -q
node scripts/check_frontend.cjs
node scripts/check_simulation_state.cjs
node scripts/check_workbench_v15.cjs
node scripts/check_series_controls.cjs
PYTHONPATH=. python scripts/check_mcp.py --stdio
PYTHONPATH=. python scripts/audit_library.py --full --tracked-only --output operations/library-full.json
```

Start the application before the MCP client check. The JavaScript checks need Node.js. Offline pytest collection is limited to `tests/`. The `test_*.py` files at the top level are manual provider probes, not part of the suite.

Every active library model must pass its full default run. Model repairs and retirements need exact file hashes and backups. Never sync model directories, databases, credentials or configuration over production.

[Architecture](docs/ARCHITECTURE.md) · [Testing](docs/TESTING.md) · [Operations](docs/OPERATIONS.md) · [All documentation](docs/README.md)

## License

The code is released under the [MIT License](LICENSE). Third-party model sources bundled under `operations/*/sources/` keep their own license files.
