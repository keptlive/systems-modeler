# Engine capabilities and failure causes —1.8

The engine now has three explicit additions: stiff deterministic ODE integration with Radau, bounded binomial random samples, and failure reports that distinguish primary errors from blocked dependents. These additions do not establish model validity. No saved model is automatically switched, repaired, clamped, downsampled or given a replacement denominator.

## All86 baseline failures covered

`operations/engine-failure-coverage-v18.json` replays every failed default in the1.7 public audit from original Git bytes pinned to `c3ac31b`. Original hashes are checked before execution, so other agents' concurrent model repairs cannot alter the evidence. Every row contains the authored settings, source-review diagnosis, actual first failing time, primary equation(s), blocked dependency chains, finite stock snapshot, and static reference evidence.

All86 original defaults still fail when replayed without input changes. The engine separates:

| Immediate mechanism | Models |
|---|---:|
| Numerical/non-real/domain failure needing numerical and source investigation |65|
| Actual missing declared input or function |8|
| Authored namespace collision |3|
| Runtime algebraic dependency cycle |3|
| Unsupported authored STEP/RANDOM signature |3|
| Unsupported scalar-language expression |2|
| Malformed equation syntax |1|
| Request capacity |1|

These are immediate mechanisms, not a claim that all65 numerical cases share a scientific cause. A mathematically sound stiff ODE can fail under explicit Euler, while malformed units, depleted compartments, positive feedback, incompatible histories or undefined reporting quantities can also produce overflow/domain errors. Model-side source reviews and independent references decide which remedy is justified.

For example, the fishery failure previously led with “Unknown variable: Harvest” in revenue. The primary failure is non-finite Harvest, with fish biomass around−1.56e147 and fleet around−6.82e213. Revenue, profit and fleet decisions are blocked by that failed rate; their names are already declared.

## Root-cause payload

`EquationError` retains ordinary string behavior and adds optional `code`/`details`. `failure_payload(error)` returns a JSON-ready description. Stalled equations use:

```json
{
  "code": "unresolved_equations",
  "category": "invalid_equations",
  "time": 0,
  "root_errors": [{"element": "Rate", "element_id": "...", "equation": "1/0", "code": "division_by_zero", "message": "Division by zero"}],
  "blocked_errors": [{"element": "Output", "code": "blocked_dependency", "waiting_for": "Rate", "dependency_path": ["Output", "Rate"], "root_cause": {"element": "Rate", "code": "division_by_zero"}}],
  "stock_values": {}
}
```

Messages put primary failures first and show authored equations with readable quoted names, rather than internal encoded parser tokens. Actual runtime missing-symbol edges identify blocked dependencies and cycles. Static references are not used to invent a cycle through an inactive IF branch. Multiple independent primary failures remain visible. No extra equation branch is evaluated for diagnosis.

Capacity errors carry `code: capacity_exceeded`, `category: capacity`, `resource`, `requested`, and `limit`. Unsupported method/input combinations use `unsupported_method_features` and `unsupported_capability`. Investigation rows include the payload under `failure`; root integration adds an HTTP field while preserving the existing detail string.

Validation also warns about disconnected stocks and models with no stock-changing flow. These are warnings: intentionally fixed stocks remain legal. A stock equation initializes a stock and does not supply its derivative.

## Explicit Radau contract

Select `time_settings.integration_method = "radau"`. Euler and RK4 remain unchanged. The already-required SciPy implementation uses Radau IIA, an implicit fifth-order method intended for stiff problems. Its internal grid adapts; the result retains every requested output time exactly, including a partial final interval. For this explicit method, DT is output spacing and remains the value seen by DT/TIME_STEP equations.

| Setting | Default | Constraint |
|---|---:|---|
| `rtol` |1e-6|1e-12 through0.1|
| `atol` |1e-9|positive finite|
| Output intervals |authored grid|at most100000|
| Retained scalar values |all outputs|at most1000000|
| Work units |every actual model evaluation × element count|at most1000000|

Each initialization, RHS call, finite-difference Jacobian probe and retained algebraic-output evaluation is charged. SciPy's nfev alone omits Jacobian probes, so it is not the budget counter. Results expose `integration_diagnostics` containing tolerances, nfev/njev/nlu, actual model evaluations and charged work. Exhausting the budget or solver failure returns an error and no partial substitute trajectory.

Random functions, all delay/smooth functions, and STEP/PULSE/RAMP are initially unsupported with Radau, including calls in inactive branches. Explicit time-triggered comparisons/IF conditions and discontinuous FLOOR/CEIL/ROUND/SIGN/MOD or discrete arithmetic are rejected, including transitive algebraic aliases to TIME. TIME-driven graphical functions are also rejected across discrete, continuous and extrapolating interpolation: this includes `table(TIME)`, `LOOKUP(table,TIME)`, `WITH_LOOKUP(TIME,points)`, algebraic TIME aliases, and TIME-dependent inline points. Even a continuous narrow triangular table feature can fall entirely between the adaptive solver's internal evaluations; the retained output grid does not constrain those internal steps. The current method does not split integration at table knots, so rejecting these inputs prevents a successful but silently missed forcing pulse. Stock-driven graphical functions and stock-dependent feedback IF remain allowed. This conservative check is not a proof that every accepted RHS is smooth or a guarantee that every domain-restricted Newton trial succeeds.

Standard XMILE export cannot represent this exporter’s Radau method/tolerances, so it fails explicitly with a JSON-preservation instruction. Existing Euler/RK4 XMILE paths remain available; JSON preserves the complete Radau settings.

Investigation of a Radau model still compares its full-horizon DT, DT/2 and DT/4 output grids, but reports `output_grid_comparison_only` with unchanged rtol/atol explicitly recorded. This does not refine internal adaptive steps or test tolerance convergence. Differences can reflect retained-output interpolation; equations referring to DT can also change the supplied mathematical system. Euler/RK4 retain their integration-timestep comparison interpretation.

Independent tests check a stiff manufactured solution X=cos(t), its accumulated integral Y=sin(t), a time-constant1 relaxation over a million-unit horizon with1000-unit retained spacing, and the conserved three-species Robertson kinetics. Solver budget, Jacobian cost, exact output times, method rejection, tolerance validation, JSON preservation and MCP overrides are tested. Scientific calibration is a separate model task.

Primary references: [SciPy solve_ivp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html), [INdAM–Bari Robertson test problem](https://archimede.uniba.it/~testset/problems/rober.php).

## Explicit RANDOM_BINOMIAL extension

`RANDOM_BINOMIAL(n,p[,seed])` returns an integer-valued real number with binomial law. It is an explicit extension, not an interpretation of unsupported RANDOM(). Trial count must be an integer from0 through1000000; p must lie in[0,1]. Invalid fractional counts are rejected rather than truncated, and probabilities are never clamped.

The bounded implementation sums exactly n independent Bernoulli trials from NumPy PCG64 uniform values. It uses n trial work units for each new callsite/accepted-time sample, combined with the existing integration budget. Initial and final output draws count too. The temporary random array is bounded; only each callsite's latest sample/parameters persist.

One sample is cached per callsite and accepted time, so dependency retries do not redraw. Identical expressions at different source positions have distinct streams. Explicit seeds override the run seed; changing a seed or binomial parameters within one accepted time is rejected. Replay assumes the recorded engine/runtime/NumPy version. RK4 and Radau reject this stochastic primitive.

Tests check exact binomial probability masses against combinatorial probabilities, fixed-seed replay, distinct callsites, retry accounting, degenerate probabilities, parameter rejection and combined budget interruption. A Wright–Fisher-form example stays on the finite allele-count lattice and preserves absorbing boundaries without clipping. One update per generation is a model-time contract: halving DT creates a different stochastic process and is not ordinary pathwise convergence.

Primary references: [NumPy binomial law](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.binomial.html), [NumPy bounded uniform sampling](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.random.html).

## Source-language boundaries and performance

[XMILE3.5.2](https://docs.oasis-open.org/xmile/xmile/v1.0/os/xmile-v1.0-os.html) specifies RANDOM(minimum,maximum[,seed]);3.5.4 specifies STEP(height,start_time). [Vensim's STEP manual](https://www.vensim.com/documentation/fn_step.html) likewise requires two arguments. No evidence supports inventing zero-argument RANDOM or one-argument STEP semantics. XMILE3.2.3 also defines scalar values as real numbers, so strings and complex results remain explicit failures.

Parsed ASTs and equation preprocessing were already cached. This pass additionally memoizes pure canonical identifier normalization with8192 bounded entries, bypassing cache retention for names longer than1024 characters. This removes repeated Unicode/regular-expression work without changing namespace precedence, case folding, ambiguity checks or numerical arithmetic.

## Verification

The combined engine/feature/input/investigation/XMILE/capacity suite completed **267 passed,3 expected failures**. The expected failures are the existing strict-XMILE identifier gaps; one existing Pydantic forward-reference warning remains.

- `tests/test_failure_diagnostics_v18.py`: primary versus blocked causes, lazy branches, cycles, readable names, capacity payloads, constant-stock warnings and Unicode cache preservation.
- `tests/test_radau_v18.py`: independent stiff references, transport/settings, work accounting and missed-pulse rejection.
- `tests/test_binomial_v18.py`: distribution, replay, caching, cost and lattice/boundary checks.
- Existing engine, validation, investigation, XMILE and capacity regressions are retained. Model/source repairs, complete library audit and real MCP transport checks are coordinated separately by the parent task.
