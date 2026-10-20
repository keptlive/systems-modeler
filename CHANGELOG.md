# Changelog

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
