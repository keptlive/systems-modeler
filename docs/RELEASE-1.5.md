# Stock & Flow 1.5 — verified capabilities and workbench polish

The corpus is now complemented by a function-level numerical contract. All 44 advertised function and alias names have explicit coverage in 218 advanced tests. Independent formulas check complete delay responses, nonlinear trajectories, pulse areas, stochastic accumulation, interpolation and method behavior. An independent reviewer found two additional edge cases; both were repaired and rechecked. Details and limits are in `ADVANCED-FUNCTION-REVIEW-1.5.md` and `INDEPENDENT-ENGINE-REVIEW-1.5.md`.

Decimal pulse boundaries, RK4 test-input holding, invalid time-input parameters and extreme lookup arithmetic are repaired. STEP/PULSE/RAMP are held with their complete arguments at accepted times. Ordinary time-dependent expressions remain stage-valued. PULSE uses magnitude / first time / optional interval, rather than the different Vensim start / width signature. The MCP engine resource and in-app guide state this contract.

The existing interface gains a command/element finder, model and run context, more consistent spacing and controls, longer title area, chart-series search and Stocks / All / Clear controls on desktop and mobile. Small mobile values no longer round misleadingly to zero. Existing editing, AI, analytics, saved models, import/export and agent workflows remain available. See `UI-DIRECTION-1.5.md` and `UI-QA-1.5.md` for the baseline, fixes and actual browser evidence.

## Verification

- 563 regression tests and 18 preservation subtests passed, with one existing Pydantic settings annotation warning. This includes 218 advanced cases and 13 corpus-contract harness tests.
- Four Node check scripts passed, along with real MCP clients over local Streamable HTTP, SSE and stdio. All 17 tools remain exposed.
- All 1,078 public model definitions were rerun at their complete default horizons with a recorded fallback stochastic seed: **941 completed and 137 failed**. This is unchanged from 1.4. No model definition was altered in 1.5.
- `CORPUS-TEST-CONTRACT-1.5.md` explains static occurrence, actual invocation, numerical completion and independently checked mathematics as separate measures. Neither function coverage nor a finite run establishes scientific validity or source fidelity.

The 137 public failures remain visible investigation cases. The preceding production audit also had two failures among 13 production-only models. Unsupported dialects, source ambiguity, missing units/calibration and model-domain problems are not hidden or coerced into successful runs.

Responsive browser checks cover desktop, tablet and narrow phone viewports. Physical devices, Safari and Firefox remain unverified.

## Production verification

Activated on October 20, 2026. All 13 changed runtime files matched the reviewed release; all 1,092 model/database files were unchanged. A fresh production-only audit completed 11 of 13 models, retaining two explicit failures: the full production corpus remains 952 completed / 139 failed. Both services sharing the host remained active with zero restarts reported by systemd's restart counter. No production dependency, credential or proxy configuration changes were made.

The staged code passed 433 tests using existing production dependencies and a temporary isolated test runner. An initial staging attempt lacked an unchanged analytics asset; completing the staged static tree resolved that harness failure. Real HTTPS MCP Streamable HTTP and legacy SSE checks passed with 17 tools, analytical results, errors, resources and prompts. Private deployment/recovery receipts are retained separately.
