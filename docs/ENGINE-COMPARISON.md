# Stock & Flow and Simlin: tested capabilities and measured limits

Updated October 24, 2026 for the 22-module Stock & Flow engine with typed native array reductions and a 996-model source catalog. Stock & Flow retains its independent Python engine, editor and model format. It offers useful bounded modeling and analysis tools; these results establish no overall speed or completeness lead over Simlin. Simlin is faster on every shared scalar timing case measured here. Neither a larger catalog nor numerical completion establishes scientific validity.

## What the performance numbers mean

Three different comparisons should not be combined:

- **Earlier optimizations of our own engine:** the historical [Euler](simlin-reference-final-euler.json) and [RK4](simlin-reference-final-rk4.json) receipts show 32–35% lower repeated execution time than our earlier implementation on Teacup/SIR. The measured native Simlin reference was still approximately 10–156 times faster. These are receipts for their recorded older engine hashes, not a fresh speedup attributed to today's array adapter.
- **Dependency scheduling:** a deliberately reversed 60-variable chain reduced actual evaluator attempts from 3,660 to 120 and charged retries from 3,540 to zero in a two-sample test, with identical outputs. The longer timing fixture also improves substantially. Tiny/already ordered Teacup and SIR runs instead incurred roughly 1–9% planning overhead in that separate experiment. Fewer actual retry charges are truthful work savings, not a higher work limit. See the [scheduler measurements](DEPENDENCY-ORDERING.md) and [independent semantic review](DEPENDENCY-ORDERING-REVIEW.md).
- **Current engine versus the reference wheel:** the fresh results below bind every current core-file hash. They answer only the two shared scalar fixtures and methods shown; the array adapter itself has no measured cross-engine speed advantage.

### Fresh matched scalar runs

The matched runs were repeated after the namespace parser was frozen; the raw current [Euler](simlin-reference-current-euler.json) and [RK4](simlin-reference-current-rk4.json) receipts retain all 15 timing samples, parse/first/repeated phases, unchanged input hashes, methods/time settings, Python/platform/dependency versions and complete-column error summaries. All 241 Teacup and 3,201 SIR time samples/columns match within the established fixture tolerances: values `rtol=6e-6`, `atol=5e-6` and time `atol=1e-10`.

Times are milliseconds; ratios are our warm median divided by Simlin's warm median, so a larger ratio means Simlin was faster on that case.

| Unchanged fixture/method | Our first run | Our warm median | Simlin first run | Simlin warm median | Ratio |
|---|---:|---:|---:|---:|---:|
| teacup / EULER | 4.972 | 1.770 | 0.777 | 0.185 | 9.58x |
| SIR / EULER | 35.463 | 36.321 | 2.089 | 0.487 | 74.52x |
| teacup / RK4 | 11.316 | 7.440 | 0.983 | 0.210 | 35.39x |
| SIR / RK4 | 154.410 | 154.867 | 2.737 | 2.369 | 65.37x |

Both engines receive the original scalar XMILE equations, method, horizon and timestep; loop analysis is disabled. Times include result materialization and exclude process startup. Parsing is timed separately. “First” means first simulation of an already loaded model in this process, not a fresh interpreter or cold operating system. Both paths have warm caches; Simlin can reuse native compilation while our simulator builds its per-run plan. The established harness measures one engine's repeat group followed by the other, rather than alternating pairs. Short timings and machine load limit the precision of ratios. There are no confidence intervals, full-library cross-engine timing, stiff/random/large-module speed results or general performance ranking here.

The executed reference is the existing isolated `pysimlin==0.8.5` Linux/Python 3.12 wheel, with native-library SHA-256 `57e27f8f9ee323c4879b9c7eadfae5ba0daf90d7aa72b79c9effa1c7f9d10d10`. Architecture inspection separately pins Simlin commit `3f87e9024a580b86b65e3d0c5c3353660fc5426e`; wheel/source equivalence is not asserted. The [comparison evidence index](engine-comparison-evidence-20261024.json) binds the exact harness, 22 current core modules and raw receipts. No reference dependency is installed in the production application.

## Tested feature matrix

“Tested” below describes bounded Stock & Flow cases. The Simlin column describes inspected primary-source capabilities unless an executed shared fixture is explicitly identified; it is not an exhaustive comparative product audit.

| Area | Stock & Flow: exercised behavior | Scope and Simlin comparison |
|---|---|---|
| Scalar numerical execution | Euler/RK4 trajectories, explicit work/output limits, causal failure and finite-value checks; Teacup/SIR shared fixtures compare every column/time. | Pinned Simlin methods include Euler/RK2/RK4. Shared-fixture agreement does not establish whole-language equivalence. |
| Stiff integration | Explicit adaptive Radau option, stiff references and rejection of unsupported method features. | No matched stiff-system Simlin benchmark here. Random/stateful functions and uncertified discontinuities restrict our Radau path; it is not an automatic fallback for every model. |
| Native arrays/reductions | Declared ordered dimensions, per-cell equations/initial values and SUM/MEAN/unary array MIN/MAX. 33 executed reference samples for four reductions match; tests cover solver trajectories, overloads, ordering, source retention and budgets. | Our [typed reduction contract](ARRAY-REDUCTION-ADAPTER.md) excludes arithmetic reduction operands, slices, mappings, wildcards and containers. Simlin's typed [builtin signatures](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/builtins.rs) and array implementation cover broader cases. 33 samples are numerical comparison, not general XMILE parity. |
| Native modules | Explicit local scope, scalar ports, stable source maps and preserved editable source separate from flattened execution artifacts. | No module arrays, array-valued ports, parent capture or cross-module material flows. Compile-time expansion bounds do not waive the lower execution limits. |
| XMILE/MDL interchange | Supported scalar XMILE import/export; the MDL importer retains its original MDL source and diagnostics, and native structured JSON retains its editable source separately from execution artifacts. | Ordinary XMILE currently has no general original-XML inspection/source envelope, and namespace-aware import is limited to its [reviewed compatibility profiles](XMILE-NAMESPACE-REVIEW.md). No general XMILE losslessness or comprehensive loss reporting is claimed. Native JSON support does not imply array/module interchange. Simlin exposes native projects and serialization; inspect each conversion's supported semantics. |
| Units | Advisory expression/unit checks report consistent, incomplete or unsupported evidence; errors/unknowns stay visible. | [Our checker](DIMENSIONAL-ANALYSIS.md) is not scientific certification or a substitute for missing units/calibration. Simlin has engine-integrated unit checking/inference. |
| Feedback analysis | Bounded graph/local-response diagnostics against explicit trajectories. | This is not Simlin's quantitative Loops That Matter scores, exhaustive loop enumeration or loop dominance. See [feedback scope](FEEDBACK-ANALYSIS.md). |
| Local parameter sensitivity | Tested final-stock derivatives, analytic references, HTTP/MCP/UI access and shared quota/cancellation/deadline behavior. | Restricted smooth deterministic scalar Euler/RK4 grammar and explicit steps; no global sensitivity, automatic calibration or arbitrary-model guarantee. [Transport contract](LOCAL-SENSITIVITY-TRANSPORT.md). Equivalent Simlin workflows were not exhaustively compared. |
| Application/data preservation | Editable source, saved models, import/export, charts, scenarios, library access and existing MCP transports remain available; the source catalog contains 996 reviewed/legacy examples. | Catalog size and interface convenience are separate from execution speed, interoperability and scientific validity. A successful default run is not a validated forecast. |

## Experiments we declined to integrate

The baseline for these experiments is our actual cached arithmetic-closure evaluator, not an uncached AST visitor. Both prototypes stayed offline; neither became a production option.

| Experiment | Independent measured result | Decision |
|---|---|---|
| Arithmetic instruction stack | Seven paired warm repeats: scalar/fallback cases about 5.7–13.5% slower; complete SIR about 11.5% slower and Teacup 3.9% slower. [Raw repeats](benchmark-arithmetic-stack-rejected.json). | Keep the existing evaluator. This narrow Python stack experiment is not an implementation of Simlin's native VM and does not refute native compilation. |
| Prebound canonical aliases | Seven paired full-model repeats, including binding/bridge setup: capability trap 7.8% slower, labor 1.7% slower, optical control 4.3% slower; short World3population case 4.1% faster. SIR/Teacup controls show no general benefit. [Independent repeats/setup/allocations](benchmark-symbol-binding-rejected.json); [author repeats/environment](benchmark-symbol-binding-author.json). | Keep the existing resolver. Host variation changes the magnitude; isolated short-case gains cannot justify common-path regressions. Live-key/mutation/error guards must not be removed to force a win. |

The final binding experiment passed 65 supplied tests plus independent generated expression, mutation, concurrency and solver checks. Its initial metadata-discovery guard was tightened before final measurement. A single traced Python-allocation peak is not RSS/native memory or a statistical memory advantage. Passing parity tests is necessary for an optimization, but does not make a slower, more complex implementation worthwhile. A different owned/value-container or native execution design would need separate review and useful end-to-end evidence.

## Reference and rights boundaries

Primary architecture references are the pinned [integration-method data model](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/datamodel.rs), [bytecode/typed offsets](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/bytecode.rs), [unit checking](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/units_check.rs), [import-loss diagnostics](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/import_losses.rs) and [Python API](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/pysimlin/README.md). They support architectural/capability descriptions, not current benchmark conclusions about unexecuted features. [Python's profiler guidance](https://docs.python.org/3.12/library/profile.html) distinguishes instrumentation from wall-time benchmarking.

Simlin's engine has an Apache-2.0 notice; the SDXorg inputs/historical reference outputs retain their separate MIT attribution. Other collections do not inherit those licenses by association. No upstream engine implementation was copied into our runtime. The [reference harness](SIMLIN-REFERENCE.md), [source-preserving structure contract](STRUCTURED-MODELS.md) and [research roadmap](ENGINE-RESEARCH-ROADMAP.md) provide detail; this page updates the existing comparison rather than replacing those specifications.
