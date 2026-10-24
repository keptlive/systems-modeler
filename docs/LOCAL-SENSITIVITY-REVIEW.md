# Independent review: native local sensitivity core

2026-10-24. **Approve the exact frozen core-only implementation below. No remaining review blockers.** This approval covers an internal read-only service, its tests and documented limitations. It does not approve or implement HTTP/MCP/UI exposure, a cross-process server quota, saved-model changes or parameter application.

## Exact reviewed SHA256

| File | SHA256 |
|---|---|
|app/core/local_sensitivity.py|`0ca710f7cc6a076636803df5aa3d74bdaea66429ddab66512a95371ce3ad035a`|
|tests/test_local_sensitivity.py|`2b56cc840e09e5f46cd0c48f030a9dc06c40f54fcb83ab802e7ede2f6f38a246`|
|docs/LOCAL-SENSITIVITY.md|`943c909fbe7bdfc4ead82834e7b2a0b24e698fd97363c54ef263e5bdf81a5735`|

The budget proof also depends on the reviewed existing engine: integration.py `29b6649c2771e1684c7298751647d65a6c04b4f54a016be9f4328908d75b2598`, execution_order.py `0633452a7a9a5e7d0d3701ff2ea7b496063e6714e4596986f1d057a5ec694820`, equations.py `7c7dff75a0a4c00ec62d347788e7dde32197a68c38b5140ca57f11df2e74e612`. Recheck the proof if evaluation or scheduling semantics change.

Final independent command: `.venv/bin/python -m pytest tests/test_local_sensitivity.py tests/test_dependency_order.py tests/test_execution_plan.py tests/test_execution_optimization.py -q` — **160passed in4.47s**, including all77local sensitivity tests. No full-suite run was started by this reviewer; release-wide testing remains separately coordinated.

## Contract and admission

The numerical object is one final stock's local partial with respect to one selected numeric literal variable at a time, all other parameter baselines fixed. Immutable IDs, ordered rows, explicit absolute steps, fresh validated model copies and reinitialized stock equations preserve the intended parameter experiment. Existing tuner clamps and analysis/chart state are not involved. Unit labels and raw derivatives are retained; no global influence ranking or confidence interval is manufactured.

Canonical parser/scheduler admission rejects structure, discrete/stateful/stochastic/contextual/lazy features, tables, reports, ambiguous names and cycles. Allowed autonomous arithmetic DAGs include variable division, so syntactic admission is explicitly not a domain or smooth-neighborhood proof. Runtime guards and per-row failures remain necessary. This is accurately documented; no silent fallback to another method or AI occurs.

The2MiB snapshot,100elements,2001points,4096AST-node and32768equation-character limits are mutually enforced. A bounded noncopying source traversal now precedes full serialization, covering otherwise unused metadata, source documents, collection breadth/depth, huge integers and cycles. Mutated invalid Model snapshots become typed admission failures. The source model is not edited. The limits bound source/trajectory structure, not operating-system RSS.

## Work reservation proof and independent probes

For N elements and S intervals, engine ordinary charge is O=(S*k+1)*N, with k=1 for Euler and k=5 for RK4. All admitted successful stages are pure topologically scheduled DAGs and require no retries. A failing stage has at most N pending equations; each progressing pass removes at least one and the stalled pass ends execution. N² conservatively covers extra attempts at the first failing stage. Other completed stages have no retries and no later stage executes after failure. Reserving R=O+N² for every one of1+4P possible runs before worker creation therefore bounds aggregate engine work for this grammar. It does not count CPU instructions or authorize arbitrary callback execution.

Independent late-failure DAG probes used lengths0,5,20,70, with an auxiliary1/(X-critical) that becomes singular during integration rather than at initialization. Euler criticalX1.1 and RK4 criticalX1.05 failed at a later/stage evaluation. Measured maximum engine charges for N4/9/24/74 were46/101/266/816 forEuler against reservations60/180/840/6290; RK4 charges206/461/1226/3776 against220/540/1800/9250. Equation attempt counts also stayed below each reservation. These probes supplement, rather than replace, the structural proof and supplied initialization/charge tests.

Accounting is candid: attempted runs consume conservative reservations even on failure, successful engine work is separate, interrupted work is unknown and charged the whole experiment allocation. No failed row receives a derivative or a fabricated zero. Baseline failure aborts; independent rows can continue after a perturbation failure within the pre-reserved allowance.

## Reproduced lifecycle findings and verified corrections

1. A result pipe readiness check followed by blocking recv could overrun the deadline. A spawned worker sending a four-byte header announcing a 100-byte payload, but only one payload byte, then sleeping, caused a.5-second request to raise incomplete-message OSError after1.34s. The corrected parent incrementally reads a bounded JSON frame through a nonblocking POSIX descriptor. The same independent probe now returns deadline_exceeded in about.505s; incomplete EOF becomes worker failure, and the next job succeeds.
2. Sending a large model directly through Process.start could block the synchronous spawn bootstrap while the child imported its main module. A standalone script with a two-second child import and an admitted200000-byte description overran a.5-second request to2.14s. The corrected small bootstrap references a uniquely created0600bounded JSON artifact; the child reads it under independently enforced parent control. The same probe now returns deadline_exceeded in about.504s with no remaining child. Artifact cleanup/permissions and absence of its path in successful results have regression coverage.
3. Checking snapshot size only after model_dump/json.dumps allowed unbounded caller metadata to allocate first. Cheap element gates and the bounded pre-dump walker close that path; supplied tests forbid model_dump and verify early rejection. Snapshot validation errors are normalized into LocalSensitivityError.

Termination, join/kill escalation, pipe/artifact cleanup and slot release were inspected. The semaphore admits one worker per calling Python process; this is deliberately not a multiworker server quota. POSIX-only admission is explicit. Normal multiprocessing/application startup prerequisites and bounded admission/provenance preparation are documented; infrastructure exceptions do not become successful reports. A future endpoint must supply a shared quota appropriate to its actual deployment topology.

## Independent numerical checks

In addition to supplied exponential/discrete-solver tests, independently checked X'=pX+q, X(0)=p², p=0.4,q=-0.3,T=1,dt=0.05 with both parameters selected. For N=20 steps and the method's stability polynomial R(p*dt), final X=p²R^N+q(R^N−1)/p; differentiating that expression includes both nonlinear initial-state sensitivity and forced dynamics. Euler derivatives were1.24039069750 and1.21486848995 against exact discrete 1.24039069245 and1.21486848995. RK4 derivatives were1.23545450398 and1.22956174215 against 1.23545449870 and1.22956174215. Maximum discrepancy was5.3e-9.

Actual-coordinate quadratic weights are correct for accepted unequal spacing, with materially distorted grids rejected before simulation. Scale-safe slope/weight arithmetic handles large finite coordinates. Dimensionless refinement/asymmetry diagnostics have no derivative-unit floor; supplied unit transformations retain classification. Smooth stationary points can still trigger asymmetry warnings, and matching two stencils cannot certify a derivative. Equal outputs yield a resolution warning rather than proof of global irrelevance.

Independent elasticity probes verified representable results1e-100 and1e10 despite intermediate product underflow/overflow. A further probe with p1e-300,D1e-300,F1e-100 produced exact elasticity1e-500: the final correction returns null with elasticity_underflow rather than a false true-zero score. True zeros from p=0 or D=0 remain zero. A documented dimensionless small-baseline warning now covers a nonzero denominator negligible relative to sampled outputs, preserves finite raw derivatives/elasticities, and is invariant under output-unit scaling. None of these heuristics supplies statistical uncertainty or a certified error bound.

## Release boundary

The corrected core is useful and bounded within its declared grammar/process scope. No changes were made to existing integration/equation semantics, saved data, tuner, scenarios, variance analytics or charts by this feature. Transport/UI exposure still requires deployment-wide concurrency admission, actual HTTP/MCP client tests and preservation checks. Forward sensitivity ODEs, global Morris/Sobol analysis, arbitrary objectives and unsupported model features remain separate work. This review authored documentation only; implementation fixes were coordinated with the author.
