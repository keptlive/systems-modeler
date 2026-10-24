# Conservative dependency ordering

`app/core/execution_order.py` derives an optional execution schedule for the existing scalar evaluator. The immutable per-run metadata plan in `integration.py` now uses this schedule when eligible; `equations.py` remains unchanged. Unsupported stages retain the original authored order and retry evaluator.

## Contract

`derive_execution_order(model, initial=False)` returns an immutable tuple of `(name, equation)` pairs, or `None` to retain the existing authored stage order and dependency retries. Empty eligible stages return `()`. The function parses metadata only: no model equation is evaluated, source is not modified, and no additional simulation or external service runs.

Pass the numeric scalar execution model after structured lowering and report separation. The ordinary authored stage is variables followed by flows. The initialization stage adds stock initializer equations after those expressions. During ordinary evaluation every stock is an available state value. During initialization only stocks without initializer equations are initially available.

The planner reuses the canonical equation preprocessor/parser, identifier decoding, alias normalization and reference discovery. Declared `e` and `pi` are graph dependencies and take precedence over mathematical-constant fallback. Quoted Unicode identifiers use the same canonical matching as the evaluator. Canonical collisions or reserved TIME/DT/TIME_STEP element aliases force fallback.

A stable Kahn topological sort chooses the earliest authored position among currently ready expressions. It never rewrites equations, substitutes values, folds constants or selects a solver.

## Eligible subset and fallback

Eligible expressions contain finite numeric literals, names, eager arithmetic/unary operators and an explicit list of established pure mathematical functions. Bare TIME, DT and TIME_STEP remain runtime inputs. Function eligibility is an explicit list rather than automatically inheriting future evaluator features.

The entire selected stage returns `None` when it contains a conditional, comparison, boolean expression, random call, hidden-state delay/smooth, context/time primitive, lookup/table call, unknown reference/function, nonnumeric/report expression, unsupported syntax, ambiguous alias or dependency cycle. Even a table named `sin` that shadows a normally pure function prevents reordering. Unlowered arrays/modules and report variables also force fallback.

This conservatism preserves lazy branches and stochastic call order. A model with `IF(1,3,missing/0)` must continue to return 3 through the original evaluator; its inactive branch must not become a mandatory dependency. Initializer cycles fall back independently from ordinary stages, where the same stocks may already be known values.

Resource limits are the current 500-element bound, 500 lookup-table declarations for planner metadata, two million total selected-equation plus declared element/table-name characters, 100,000 AST nodes and 100,000 dependency edges. The canonical parser also retains its existing per-expression limits. Invalid syntax, unsupported semantics or exhausted planning bounds cause `None`; they do not replace the established runtime validation/error channel.

## Accounting and integration requirements

The derived tuple is used only in the existing immutable per-run evaluation metadata snapshot. Preserve the current evaluator, initialization discovery, per-element base charges, actual retry charges, capacity errors, source hashes and fallback paths. An optimized schedule legitimately eliminates failed dependency retries; it must not invent evaluator work or remove work charges for attempts that still occur.

Do not persist a schedule as authored source or cache it using only Python object identity across mutable edits. Any future persistent cache needs source/semantic versioning, actual equation and alias dependencies, explicit solver-state boundaries and bounded memory. This helper has no persistent cache.

Tests compare the integrated plan against an explicitly disabled scheduler and independently instrument the actual evaluator and retry-budget callback. Accounting assertions describe attempted work rather than a synthetic graph-operation count. Causal errors are returned in original authored order even when eligible expressions were scheduled, preserving the root/blocked error payload. Existing fallback-capacity tests explicitly select the authored path; they still prove that real failed retries exhaust a bounded budget.

## Verification

`tests/test_dependency_order.py` covers:

- Stable order and unchanged source.
- Complete trajectory equivalence under Euler, RK4 and Radau, with an independent exponential-growth reference.
- Stock initializer dependencies, initially known stocks, declared mathematical-constant shadowing and quoted composed/decomposed Unicode aliases.
- Exact fallback error evidence for unknown references/cycles and unchanged causal root/blocked attribution for a domain error.
- Seeded stochastic fallback and inactive invalid lazy branches.
- Named-table/function collisions, report/structure exclusions, syntax and planning limits.
- Actual evaluator attempts and charged retries for a reversed 60-variable chain.

For `x0=1; xi=x(i-1)+1` declared in reverse order, with two retained samples, the existing path makes **3,660 evaluator attempts and 3,540 charged retries**. The test-wrapped schedule makes **120 attempts and zero retries**, with identical complete output. This is a dependency-work improvement on that fixture, not a claim about every model.

## Integrated benchmark and regression evidence

A local comparison on October 24, 2026 kept the existing immutable metadata plan enabled in both modes and disabled only dependency scheduling for the baseline. Each mode warmed once, then seven serial baseline/scheduled pairs were interleaved. Timings include per-run schedule derivation and result materialization. AST caches were warm; this is not a cold-compilation benchmark. The repository's WSL Python environment and unchanged original SDXorg fixture definitions were used.

| Workload/method | Samples | Baseline warm median | Scheduled warm median | Complete output |
| --- | --- | --- | --- | --- |
| Teacup / Euler | 241 | 0.001794 s | 0.001947 s | Exactly equal |
| Teacup / RK4 | 241 | 0.007393 s | 0.008021 s | Exactly equal |
| SIR / Euler | 3,201 | 0.035808 s | 0.036459 s | Exactly equal |
| SIR / RK4 | 3,201 | 0.145836 s | 0.147493 s | Exactly equal |
| Reverse 60 / Euler | 11 | 0.104097 s | 0.003510 s | Exactly equal |
| Reverse 60 / RK4 | 11 | 0.490927 s | 0.007688 s | Exactly equal |

Reverse-order dependencies deliberately stress retries. Tiny or already well-ordered models can be slightly slower because planning costs exceed removing one or two initialization retries. These measurements do not establish a universal speedup. The reverse-60 run reduced charged work from 20,130 to 660 for Euler and 93,330 to 3,060 for RK4; no eliminated retry is still charged. The normal deterministic result omits optional retry diagnostics when there are no retries.

The existing optional cross-engine benchmark also ran with the integrated scheduler, using isolated pysimlin 0.8.5, five warm repeats, identical methods/grids and loop analysis disabled. The source architecture review pins Simlin commit `3f87e9024a580b86b65e3d0c5c3353660fc5426e`; the published 0.8.5 wheel is not asserted to have been built from that exact commit. The receipts identify the executed distribution and dependencies separately:

| Fixture/method | Our warm median | Simlin warm median | Conformance |
| --- | --- | --- | --- |
| Teacup / Euler | 0.001963 s | 0.000216 s | All columns/times within fixture tolerance |
| SIR / Euler | 0.041670 s | 0.000822 s | All columns/times within fixture tolerance |
| Teacup / RK4 | 0.007160 s | 0.000343 s | All columns/times within fixture tolerance |
| SIR / RK4 | 0.154512 s | 0.001190 s | All columns/times within fixture tolerance |

Simlin remains substantially faster on these small cases. This scheduling change is an improvement to our own engine's dependency work, not a claim to replace or outperform that reference. Timing differences between the paired baseline experiment and separate cross-engine run reflect ordinary process/load variation.

Evidence files in this development session: `/tmp/dependency-order-baseline-comparison.json`, `/tmp/dependency-order-euler.json`, `/tmp/dependency-order-rk4.json`. The cross-engine files record source hashes, exact settings and runtime versions. No reference runtime was installed in production.

Regression run: **767 passed, 3 existing xfailed**, covering scheduling, canonical equation behavior, execution optimization, engine hardening, all three methods, capacity and actual retry accounting, random/binomial/stateful fallback, discrete contracts, native structure/MDL/units/feedback, XMILE interoperability, API/workspaces and real MCP SDK dispatch. That run included 39 scheduler tests. Independent review then added a conservative planner-only lookup-table count/name-text metadata bounds and their regressions; the final focused scheduler/legacy-plan/hardening run passed 117 tests, including all 41 scheduler tests. Cross-engine receipts were regenerated afterward and their source hashes match the final core files. Expected overflow-fixture/SciPy and Pydantic warnings remain visible. Full-suite run: **2,720 passed, 3 existing xfailed, 18 subtests passed** in 284.33 seconds. This run began before the final planner-only table-count guard; the focused 117-test run above covers that final guard. No full-suite failure was hidden or converted into a pass.

Engine source receipts now include `execution_order.py`. No persistent schedule cache, arbitrary code execution, source-equation mutation, automatic solver fallback or capacity-limit increase was introduced.
