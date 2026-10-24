# Independent Simlin reference harness

This is development evidence, not a production backend. Stock & Flow keeps its own engine, model JSON, editor and solvers. Run `scripts/benchmark_simlin_reference.py` in a separate environment with the project dependencies and optional `pysimlin==0.8.5`. The script exits 2 with an actionable message if the reference is absent. It accepts only Euler or RK4 and at most 100 timing repeats. The two fixed scalar fixtures are bounded by our normal simulation limits. Never apply it to untrusted arbitrary native projects without process isolation and timeout limits.

Source review pins upstream `3f87e9024a580b86b65e3d0c5c3353660fc5426e`. Executed comparisons use the published **0.8.5 wheel**, whose native binary is not asserted to be built from that exact source commit. The dependency is Apache-2.0; existing SDXorg fixtures retain their separate MIT attribution. No upstream engine code was copied into the application.

## Measured comparison

Evidence in `simlin-reference-euler.json` and `simlin-reference-rk4.json` records every timing sample, original input SHA256, exact settings, runtime versions and full-column conformance errors. Tests ran on WSL Ubuntu/Python 3.12.3. Both engines received unchanged fixture equations, matched integration method, horizon and timestep, with loop instrumentation disabled. Every output column and time sample matched within the documented historical-reference tolerance. Parsing, first simulation and repeated simulations are reported separately. These are small scalar models and elapsed times depend on machine load; they do not establish performance on every model.

The native Simlin VM was substantially faster on these cases. There is no evidence here that Stock & Flow runs these equations faster. Its adaptive Radau integration and the existing guarded numerical contracts remain useful capabilities beyond Simlin's fixed-step Euler/RK2/RK4 methods. Numerical capability, user-interface completeness and execution speed are separate claims.

## Improvements for our own engine

`integration.evaluate` reconstructs equation queues/context/error bookkeeping at every stage and resolves forward references by retry. `safe_eval` already caches parsed ASTs, so eliminating parsing alone will not remove the main per-equation visitor and dynamic-name overhead. Build a bounded, content-addressed execution plan containing dependency order, compiled scalar instructions and resolved slots; reuse only immutable plans, never delay, smoothing, random, initial-state or result buffers. Model equation/function/lookup edits must invalidate the affected plan; solver/time changes need separate execution configuration.

Preserve lazy conditional branches, exact failure causes, unknown-symbol diagnostics, finite checks, work accounting, stochastic call identity, lookup discontinuities, initial-value ordering and hidden-state stage behavior. Cyclic or branch-dependent dependency resolution needs the existing guarded fallback until its semantics have independent coverage. Benchmark plan compilation separately from repeated execution. Incremental compilation should follow after plan correctness, rather than cache mutable models by identity.

## Useful reference APIs

Pinned Python source exposes `Model.check_units()`, `Model.check()`, `Model.run(analyze_loops=True)` with quantitative loop scores and dominant periods, and `Model.simulate()` for stepwise native execution. `Project` can load MDL/XMILE/Simlin JSON, represent arrays/modules, serialize native JSON/protobuf, and export MDL/XMILE. These are reference capabilities; our scalar parser must continue to reject unsupported semantics explicitly. Any future native import must preserve original bytes and report conversion losses rather than flatten modules, dimensions or diagrams silently.
