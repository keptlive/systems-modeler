# Native engine MCP tools

All four additive tools are read-only, make no paid AI calls and never save to the library. Existing MCP tools and HTTP/SSE/stdio transports remain available. Model-based tools require exactly one of `model_id` or `model_json`, following the existing selector convention.

| Tool | Inputs | Result |
| --- | --- | --- |
| `compile_model_structure` | Model selector | Scalar execution model, source map and diagnostics; original project is not replaced |
| `check_model_units` | Model selector | Advisory errors, warnings, unknown units and inference evidence after native expansion |
| `analyze_model_feedback` | Model selector, required `result_json`, optional `sample_count` 1–16 and `relative_step` 1e-7–1e-2 | Local stock-rate response at supplied trajectory states; no full simulation |
| `import_mdl_model` | `mdl_text` | Draft `model` and `diagnostics`, with exact source and warnings in `model.source_document` |

`model_json` accepts an object or JSON string, bounded to 2 MiB of UTF-8 JSON. `result_json` accepts the complete SimulationResult object or JSON string, bounded to 8 MiB and one million numeric values. JSON must contain finite numeric values. MDL input is bounded to two million UTF-8 bytes. Existing compiler, unit-analysis, feedback and simulation budgets still apply.

Feedback requires a trajectory from the exact model and effective time settings supplied. It does not run a hidden simulation to create missing results. Declared provenance hashes are checked; absent provenance remains explicitly unverified. Local Jacobian evidence does not establish Loops That Matter dominance, causal validity or scientific correctness.

MDL import is a draft operation; save through an explicitly authorized workflow if desired. Read every warning, retain source_document and review unsupported semantics. Unsupported source returns an MCP error rather than a partial draft. Source code is never executed.

Native tool failures use the existing MCP ToolError channel and JSON `failure` envelope, with compiler/import diagnostics when available. Tool discovery exposes readOnlyHint=true and destructiveHint=false. `systems://engine` advertises the native capabilities and their scope.

Verification includes Python-level read/write traps, FastMCP registration/dispatch, and an actual MCP SDK stdio client handshake invoking all four tools. See `tests/test_engine_mcp.py`.

