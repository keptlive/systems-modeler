# Changelog

## 2026-01-18

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
