# Changelog

## 1.7.0 — 2026-10-20

- Diagnose all 134 previously failing public definitions in three disjoint source-review ledgers; repair or annotate 64 definitions while preserving model identities and authored inputs. Public audit: 992 completed / 86 failed, with no numerical regressions. Two new completions remain structurally incomplete and are explicitly flagged.
- Admit source-authored fine time grids up to 100,000 intervals; enforce one million retained scalar values alongside the existing method-aware work ceiling. No solver equations changed.
- Refine Analytics around one selected series, readable metrics and expandable comparisons; retain every analysis section. Repair fullscreen bindings, focus restoration, mobile scrolling, chart axis collisions and long legends.
- Export a styled SVG or PNG with the complete selected-series legend through an accessible preview dialog. Remove unrelated free-tool promotions from both site footers.
- Add independent source recurrences, conservation, convergence, capacity and DOM export checks. See docs/RELEASE-1.7.md for test scope and remaining scientific limitations.

## 1.6.0 — 2026-10-20

- Refine stocks, variables, flow valves, dependency curves, wrapped labels, selection, hit zones and fit geometry; preserve saved diagram positions and equations.
- Polish the workbench controls, assistant, properties, results, library and mobile sheets. Put the phone chart first; add a reversible assistant toggle and expandable final values.
- Commit element renames atomically across supported scalar references and named endpoints; reject ambiguity. Preserve valid initial values through blank/nonfinite drafts.
- Restore six original lookup tables across three teaching models. Compare complete source trajectories and the original Stella CSV while retaining source warnings and unsupported-constraint limits.
- Public default runs: 944 completed / 134 failed. Full regression: 595 tests, 18 preservation subtests, three explicit identifier-compatibility expected failures. Core engine unchanged; all 44 advertised names retain advanced regression coverage.

## 1.5.0 — 2026-10-20

- Verify all 44 advertised functions and aliases with 218 advanced tests, including independent delay, pulse, stochastic and nonlinear reference trajectories. Separate static corpus coverage, actual function invocation and scientific validity.
- Repair decimal pulse boundaries, RK4 test-input holding and extreme lookup arithmetic, including two independently discovered review cases. Document the accepted-time and XMILE pulse-signature contract in MCP and the guide.
- Add a keyboard command/element finder, persistent solver/run context, tighter workbench styling and desktop/mobile series search with Stocks / All / Clear. Preserve existing product paths.
- Fix small mobile numbers displaying as zero, hidden-series styling and mobile status overlap. Verify desktop, tablet and phone viewport workflows.
- Full public corpus remains 941 completed / 137 failed with no definition changes. Regression suite: 563 tests plus 18 preservation subtests; use Pytest 9 for its subtests fixture.

## 1.4.0 — 2026-10-20

- Reconcile63 model definitions against original implementations, mathematics and publisher records. Six previously failing public defaults now complete;137 remain explicitly unresolved. Two additional finite-but-incomplete source examples have their missing dynamics restored.
- Check illustrative epidemic trajectories against independent DOP853 references, growth against closed forms and pharmacokinetics against independent convolution, dose accounting and AUC. Explicit RK4 defaults resolve material Euler error in three epidemic examples without changing their time grids or coefficients.
- Correct Vensim conditional spelling, XMILE comments and comparison semantics; reject malformed function signatures and lookup points.
- Show known citation mismatches and model limitations in input inspection and MCP reports. Bibliographic corrections never establish source fidelity or calibration.
- Make legacy API/frontend tests assert outcomes, isolate test storage and use real JavaScript parsing. Add reproducible reference generation and per-model source/hash receipts.

## 2026-01-18

### Added
- Steps control input next to Run button
  - Allows setting number of simulation steps (10-10000)
  - End time calculated as start + (steps * dt)
  - Hidden on mobile (use Settings modal)

### Fixed
- Charts not updating when running second model in same session
  - Fixed `Charts.setResults()` to clear variable options before loading new results
  - Previously, old variable options persisted causing display issues

### Verified
- Simulation results mathematically correct (Euler integration)
- SIR model: population conservation verified, expected epidemic dynamics
- Exponential growth model: matches analytical solution

## Initial Release

### Features
- FastAPI backend with systems dynamics simulation
- Euler and RK4 integration methods
- PySD integration for XMILE compatibility
- 1691 pre-built models in 24 categories
- AI-powered analysis with Gemini
- Interactive D3.js charts
- XMILE import/export
