# Native expression execution optimization

The engine now caches immutable arithmetic execution plans, inspired by the value of compiling once demonstrated by the independent Simlin comparison. This is our own Python implementation. It has no external runtime dependency and does not call Simlin in production.

Plans bypass repeated AST visitor dispatch for constants, names, binary arithmetic and unary arithmetic. They retain the same operator functions, finite-value checks, division diagnostics and left-to-right evaluation order. Symbol spelling metadata is cached separately. Variable values, time, delay/smoothing state, lookup contents, random runtime and result buffers remain per evaluation. Both caches are bounded to 8,192 entries and equation text determines plan identity, so an edited expression receives a new plan.

Function calls, conditional branches, boolean/comparison expressions and unsupported nodes retain the established interpreter path. This deliberately preserves lazy IF, short-circuiting, graphical function resolution, random call identity, hidden-state discovery and precise error behavior. No algebraic simplification or reassociation changes floating-point arithmetic. Raw Python eval/exec is never used.

## Measured effect

Five-repeat median warm simulations on the existing independent reference harness produced these before/after seconds on WSL/Python 3.12.3. Inputs, methods and output trajectories were unchanged, and both full-series comparisons passed. Timings are local observations rather than a universal performance guarantee.

| Case | Before | After | Reduction |
| --- | ---: | ---: | ---: |
| Teacup Euler | 0.002686 | 0.002072 | 23% |
| SIR Euler | 0.056684 | 0.042926 | 24% |
| Teacup RK4 | 0.011051 | 0.008933 | 19% |
| SIR RK4 | 0.243020 | 0.186703 | 23% |

Simlin remains substantially faster on these scalar workloads. Our adaptive Radau capability and guarded numerical behavior are separate advantages; this change does not establish an overall speed lead. Parent integration work may further change timings, so final combined benchmarks must be rerun.

Validation: new differential tests compare cached plans to the retained interpreter, including exact exception type/message/code/details, overflow intermediates, unsupported syntax, lazy branches, alias ambiguity and mutable context isolation. The focused advanced-function, binomial, engine-hardening and regression run passed 441 tests. Final full-suite results are maintained by the integrating parent.

## Per-run integration metadata

Integration now snapshots equation queues, declared canonical names and lookup points/types once per numeric run. The immutable plan is reused through a scoped ContextVar for Euler, RK4 and Radau callbacks, and reset in a finally block. No mutable Model instance is used as a cross-run cache key; edits to the same instance are visible on the next simulation. Direct context/evaluation calls outside a simulation retain live-model behavior. Tables and declared names in the snapshot cannot be mutated.

Authored equation order and forward-dependency retry accounting remain unchanged. Topological reordering was deliberately deferred because it can change stochastic call order, dormant-branch handling, root errors and work budgets. The optimization removes repeated metadata construction without changing numerical scheduling.

A same-process nine-repeat comparison toggled only the metadata-plan factory, retaining the new expression plans for both paths. Complete serialized results and diagnostics were exactly equal. Median times were:

| Case | Live metadata | Per-run plan | Reduction |
| --- | ---: | ---: | ---: |
| Teacup Euler | 0.002430 | 0.001832 | 25% |
| Teacup RK4 | 0.010581 | 0.007569 | 28% |
| SIR Euler | 0.047980 | 0.038534 | 20% |
| SIR RK4 | 0.209462 | 0.162710 | 22% |

These measure the additional metadata optimization independently of expression dispatch. The isolated development receipt is `metadata-plan-benchmark.json`; final combined release benchmarks should use the checked-in reference harness. Twenty new plan tests compare exact planned/unplanned outcomes across all three solvers, forward chains, cycles, lazy references, stock initializers shadowing mathematical constants, seeded stochastic functions, smoothing, error cleanup and edited models. The accompanying focused suite passed 462 tests.
