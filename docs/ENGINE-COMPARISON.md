# Engine comparison: measured and implemented

Stock & Flow now executes its own scalar equations faster than its pre-optimization baseline, supports a bounded native structured JSON contract, and adds advisory units and feedback analysis. It does **not** establish an overall speed or completeness lead over Simlin. Simlin remains faster on the measured scalar workloads and has a more mature native array/module/import compiler. No production Simlin dependency or wrapper was introduced.

## Matched execution evidence

The final receipts are [Euler](simlin-reference-final-euler.json) and [RK4](simlin-reference-final-rk4.json). They retain all 15 repeated timing samples, first-run timing, parsing timing, source-file hashes, input hashes, settings, Python/platform/dependency versions and full-column trajectory comparisons. Both unchanged MIT-attributed SDXorg fixtures match over their complete horizons: Teacup 241 rows and SIR 3,201 rows, with `rtol=6e-6`, `atol=5e-6`. Time samples match within `1e-10` absolute tolerance. All output columns are compared; finite output alone is not the criterion.

Both engines use the same method, timestep, horizon and original equations; Simlin loop instrumentation is disabled. Timings include result materialization and exclude interpreter/process startup. “First” means the first run on the loaded model within this process; it is not a cold operating-system or fresh-interpreter benchmark. Repeated medians can benefit from native compilation reuse. The baseline receipts used five repeats before our expression and metadata optimizations; final receipts use 15 repeats. Local elapsed times vary with machine load, especially sub-millisecond native runs.

All times below are milliseconds:

| Model/method | Our baseline repeated | Our final first | Our final repeated | Simlin first | Simlin repeated | Our reduction from baseline |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Teacup Euler | 2.686 | 3.336 | 1.824 | 1.170 | 0.186 | 32% |
| SIR Euler | 56.684 | 37.295 | 37.610 | 2.318 | 0.465 | 34% |
| Teacup RK4 | 11.051 | 9.120 | 7.470 | 1.010 | 0.211 | 32% |
| SIR RK4 | 243.020 | 171.023 | 157.688 | 2.478 | 1.010 | 35% |

Simlin's repeated execution was approximately **10–156 times faster** on these two small scalar models. The measured gain is our 32–35% reduction from our own earlier baseline. These cases establish neither engine's performance across the whole model library, import formats, stiff systems, stochastic workloads, arrays or large modules. See [execution optimization](EXECUTION-OPTIMIZATION.md) for separate differential measurements and semantic guards.

## What the current code actually provides

| Area | Stock & Flow implementation/evidence | Comparison boundary |
| --- | --- | --- |
| Numerical solvers | Euler, RK4 and adaptive Radau, with explicit work/output limits and causal failure diagnostics. Existing stiff-system and method-feature rejection regressions remain. | Simlin's reviewed method enum provides Euler/RK2/RK4. Our Radau capability is an additional solver option, with restrictions: unsupported random/stateful/test-input functions and uncertified discontinuities are rejected. It is not an unrestricted upgrade for every model. |
| Execution | Immutable cached arithmetic dispatch plans and per-run immutable metadata snapshots reduce repeated Python work. Function/stateful/lazy branches retain established evaluation semantics. | Simlin uses compiled native bytecode/VM execution and incremental compilation, and wins the measured speed comparison. Our implementation is independent Python code. |
| Arrays/modules | The bounded JSON compiler expands declared dimensions, element equations/initial values, explicit scalar module ports and SUM of declared references, retaining source maps. Original structured source is saved separately from its scalar execution artifact. | This is a documented subset. Dimension mappings, module arrays, array-valued ports, cross-module material flows and rich XMILE/MDL array semantics are not claimed. Simlin's upstream implementation is broader and more mature. |
| Imports/preservation | Existing scalar XMILE, conservative scalar MDL work, explicit unsupported-feature rejection and original-source preservation remain the relevant boundaries. | Simlin has native MDL/XMILE/JSON readers and semantic/loss-aware project serialization. A successful import must not be confused with lossless support for every source feature. |
| Units | Native advisory dimensional checking can identify supported expression/unit inconsistencies and report unknown or unsupported evidence. | Simlin has engine-integrated inference and checking. Our checker is advisory and does not certify scientific validity or silently supply missing units. |
| Analysis/contracts | Existing typed reports, explicit discrete-period contracts, reproducible settings/source hashes and causal failure transport are tested application capabilities. Native feedback analysis reports bounded local response evidence. | These are concrete Stock & Flow features; equivalent Simlin application workflows were not exhaustively evaluated. Our local feedback sensitivity is not Simlin's quantitative Loops That Matter algorithm or proof of loop dominance. |

A model completing numerically does not establish empirical validity, dimensional correctness, calibration or adequate initial conditions. Neither compiler optimization nor a larger library supplies missing model evidence.

## Sources and attribution

Upstream source review is pinned to [bpowers/simlin commit 3f87e9024a580b86b65e3d0c5c3353660fc5426e](https://github.com/bpowers/simlin/tree/3f87e9024a580b86b65e3d0c5c3353660fc5426e). Relevant primary source entry points are its [engine architecture](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/CLAUDE.md), [integration methods](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/datamodel.rs), [unit checking](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/units_check.rs), [import losses](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/import_losses.rs) and [Python binding documentation](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/pysimlin/README.md).

Executed comparison uses the published `pysimlin==0.8.5` Linux/Python 3.12 wheel; it is not asserted to correspond byte-for-byte to the pinned source commit. Simlin is Apache-2.0; the independently generated historical Vensim output and SDXorg input fixtures retain the separate MIT notices under `tests/fixtures/sdxorg`. No upstream engine source was copied into our runtime. The reference wheel is installed only in an isolated development environment.
