# Independent review: dependency ordering

The integrated scheduler is approved at the source hashes below. No unresolved numerical-semantics, fallback, causal-error or work-accounting blocker was found. The change derives an immutable per-run order for a deliberately narrow scalar subset; it does not replace the evaluator, alter equations, select a solver or cache mutable model instances across runs.

## Review findings and resolved resource guards

The core eligibility rule is appropriate: only unconditional numeric arithmetic and explicitly listed eager pure functions can be scheduled. Conditional expressions, comparisons, booleans, stochastic/stateful/context functions, table calls, report expressions, unknown references and cycles retain the entire authored stage and its retry behavior. This prevents speculative dependency discovery from executing a dormant branch or changing stochastic call order. Table precedence is respected even when a lookup table is named `sin`.

Initialization and ordinary stages are planned separately. Ordinary stock values are known; during initialization, stocks with initializer equations remain graph dependencies. Declared `e` and `pi` override mathematical constants, while canonical aliases and quoted Unicode identifiers use the same parser/name rules as the evaluator. Reserved/colliding aliases fall back, leaving existing structural validation authoritative. A stable ready-node heap preserves authored priority among independent expressions. Arithmetic is neither reassociated nor simplified, and the existing finite/domain guards still run at each expression.

The integration hook retains fresh per-evaluation values/context and the established hidden-state discovery path. Reordered successful DAGs eliminate failed dependency attempts; therefore fewer retries and lower charged work are truthful. No attempt that actually occurs is exempted from existing charging. Failure records are restored to authored order before causal diagnostics, preserving exact root/blocked payload order in the checked cases.

Two related planner resource issues were resolved with the author during review:

- More than500 lookup-table declarations now cause planner fallback before canonicalizing table metadata.
- The two-million-character planning budget now includes element/table names as well as selected equations, before name canonicalization.

Both guards select the existing evaluator rather than reject a model or raise a new application limit. Their dedicated regressions pass. No implementation file was edited by this reviewer; the author made and refroze these coordinated changes.

## Independent verification

After the final guard, the reviewer reran:

`python -m pytest -q tests/test_dependency_order.py tests/test_execution_plan.py tests/test_execution_optimization.py`

Result: **83 passed in0.64s**, including all41 scheduler tests. The author separately reports a117-test scheduler/legacy-plan/hardening run; this review does not substitute that report for its own rerun.

An additional standalone differential experiment disabled only scheduling for the reference path and compared the actual integrated simulator with scheduling enabled:

| Independent probe | Cases | Result |
| --- | ---: | --- |
| Randomized pure DAGs with shuffled declarations, stock initializers and nonlinear pure arithmetic |30 models × Euler/RK4/Radau =90 runs | Exact time, state/auxiliary output, seed and report-value equality |
| Multiple domain/overflow/signature roots plus dependent equations in both authored directions |16 cases | Exact error code, message and full causal/reproduction payload equality |
| Lazy inactive invalid branches, comparison/boolean stages, smoothing, seeded random and STEP |6 cases | Planner returned fallback; exact integrated outcomes matched |

The random DAG experiment used fixed test seed62481 and independently generated DAGs; it did not reuse the scheduler test helper's model. Its eligible cases included computed stock initializers and both original and shuffled auxiliary order. The failure cases included division by zero, sqrt/log domains, EXP overflow, non-real powers, intermediate overflow, invalid MIN arity and ROUND signature. The fallback cases verified outcomes through the simulator rather than only inspecting a returned plan.

The checked-in tests additionally establish mathematical exponential-growth agreement, initializer cycles, mathematical-constant shadowing, composed/decomposed Unicode aliases, table/function collisions, unchanged lazy branches, seeded stochastic fallback, metadata/AST/edge limits and real fallback capacity errors. A reversed60-variable chain checks actual evaluator/callback counts:3,660 attempts/3,540 charged retries become120 attempts/zero retries for the two-sample fixture, with identical output. This measures eliminated work, not a synthetic graph metric.

## Performance and scope boundaries

The documented paired benchmark receipts were inspected and are candid. Planning can add overhead to tiny/already ordered Teacup and SIR examples; their observed warm times increase approximately1–9% in that experiment. The large improvement on a reversed60-variable chain is an intentionally adverse dependency case and must not be presented as a universal speedup. Simlin remains faster on the separately matched small scalar reference workloads. No overall speed/completeness lead follows from this scheduler.

A pure DAG may now finish within a work budget that its repeated authored-order retries previously exhausted. That is an intended consequence of doing less work, not a capacity increase. Sensitive stages still pay for actual retries and retain existing solver-feature restrictions. Timing and diagnostic-work metadata can change even when numerical outputs are exactly equal; comparing full serialized results must account for truthful work reductions.

No persistent schedule cache was added. Future function-list extensions, broader syntax eligibility, cross-stage state reuse or incremental model caching require a new semantic review. Existing full-suite results that started before the final metadata guards are historical evidence; the final targeted rerun above covers the reviewed files. Final release checks remain the integrating maintainer's responsibility.

## Reviewed source hashes

| File | SHA256 |
| --- | --- |
| `app/core/execution_order.py` | 0633452a7a9a5e7d0d3701ff2ea7b496063e6714e4596986f1d057a5ec694820 |
| `app/core/integration.py` | 29b6649c2771e1684c7298751647d65a6c04b4f54a016be9f4328908d75b2598 |
| `tests/test_dependency_order.py` | 6b216c924335007486f2249de1897ed894899e8aa7da77bb7c8af9f3b186f4e2 |

This review wrote only this public review document in the repository. It did not alter source equations, active library definitions, limits, runtime dependencies or deployment.
