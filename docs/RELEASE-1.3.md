# Version 1.3 — reproducible runs and model investigation

The shared engine now supports seeded stochastic runs, RK4 integration of smoothing and fixed-duration exponential delay states, corrected logical/MOD parsing, and a bounded cost estimate that includes hidden states and RK4 evaluations. Random functions and fixed-history delays remain Euler-only; unsupported dialects fail explicitly. See ENGINE-REVIEW.md for the capability matrix.

The editor adds an Inspect action with searchable inputs, source links, element selection, full-horizon timestep comparisons and a downloadable report. Initial values computed by an equation are labeled clearly. Editing inputs clears stale results and invalidates pending analytics; late responses cannot attach old results to new equations. Existing manual editing, optional AI, saved runs, charts, library, imports/exports and mobile paths remain available.

MCP exposes 17 tools, including `investigate_model`, and the `systems://engine` resource. The agent and page share one exact run and its effective random seed. Scenario comparisons record and share a seed, making repeated comparisons reproducible. The preferred connection is https://stockandflow.live/mcp/; legacy SSE remains available.

## Model evidence

The complete audit of 1,078 tracked definitions produced **935 completed defaults and 143 explicit failures**, six additional completions and no newly failing defaults. Numerical completion is not scientific validation. A deeper sweep covered all 143 failures and seven finite-run concerns, recording complete trajectories across bounded step/method alternatives.

Four models were repaired against pinned original sources: SIR, SI, SIR Simple and Sales Agency Fit Adjustment. The repairs restore lost initial equations, flows, a reporting stock and a parameter. Existing element identities and unrelated fields remain intact. Canonical numerical fixtures, independent analytic solutions, conservation identities and a high-accuracy independent ODE reference cover the repairs. Source URLs and exact hashes are in MODEL-INVESTIGATION.md and `operations/model-source-repairs.json`.

Several unresolved inputs reference missing symbols or application-specific functions. Other completed runs exhibit negative physical quantities or significant step sensitivity. Those findings remain visible; changing a default merely to obtain a finite result would conceal them.

## Verification

- 246 regression tests passed, covering the engine, validation, XMILE, analytics, workspaces, investigation and fenced model repairs.
- JavaScript parsing and numerical frontend checks passed. Async regression checks cover result snapshots, model edits, late analytics completion and small time values.
- Real HTTP, SSE and stdio MCP checks passed. The live MCP-to-browser loop changed an inflow, preserved source/units, produced the expected final value of 110 and received browser acknowledgement of revision 4. It made no provider call or library write.
- Chromium desktop, tablet and phone layouts were exercised, including live inspection at 1280×800 and 390×844. Settings drafts, equation search/selection, stochastic seed receipts and stale-output removal were checked. Physical devices, Safari and Firefox remain unverified.
- Deployment checked all 1,092 data files. Exactly the four reviewed definitions changed; the remaining definitions and database were unchanged. The 13 production-only definitions were audited privately: 11 completed and two failed, for **946 completions and 145 failures** across the live library.

## Continuing work

Reconcile undefined symbols, missing graphs and nonstandard function calls with original sources; investigate domain and timestep findings without inventing equations; add independently justified engine capabilities with reference cases. Complete physical-device and alternate-browser acceptance. A clean numerical run, source fidelity, dimensional consistency and empirical validity remain distinct checks.
