# Advanced scalar-function review 1.5

This next-version review verifies numerical and language behavior of the existing engine, using independent reference formulas rather than successful corpus completion as evidence. The v1.4 release models and receipts are unchanged. No commits, deployment or external provider requests were made for this patch.

The suite tests every one of the 44 distinct function/alias names in the live SAFE_FUNCTIONS and CONTEXT_FUNCTIONS registries. An exact registry-to-matrix assertion fails if a new advertised name has no reviewed row. The corpus alone cannot establish this coverage: the independent corpus inventory finds 19 of these names absent from all 1,078 tracked model definitions. These synthetic tests complement, rather than replace, corpus runs.

## Confirmed defects and bounded repairs

| Defect reproduced before repair | Independent expected behavior | Change |
| --- | --- | --- |
| Decimal repeated PULSE at DT=.01 and interval=.1 produced extra samples at .11/.21 and missed other events; nonzero starts also misclassified boundaries | Exactly one active grid sample per nonoverlapping scheduled one-DT pulse; area equals magnitude | ULP-scaled snapping using local time/start/elapsed/DT arithmetic (not a distant repeat interval), capped at DT/4 so valid grids near large absolute origins retain active pulses. No fixed absolute epsilon. |
| RK4 PULSE(7,start) integrated only 35/6 over the first complete interval; STEP/PULSE leaked into the preceding interval | A one-DT pulse contributes 7 and an event does not act before its accepted grid time | Hold complete STEP/PULSE/RAMP primitives, including arguments, at the accepted left state during RK4. Ordinary TIME, algebra and hidden-stock derivatives remain stage-valued. |
| Holding only the clock broke STEP(1,TIME), whose argument changed at RK stages | Its accepted value is always 1; STEP(X,TIME) holds accepted X | Private accepted evaluation snapshot supplies argument values and preserves equation/call identity, including hidden-state arguments. |
| Midpoint between finite Y values -1e308 and +1e308 returned infinity; X endpoints spanning those extremes produced incorrect weights | Midpoint zero; nearby extrapolation x=1.01 gives 1.02e308 | Convex weights for interpolation, normalized coordinates for overflowing coordinate differences, weighted extrapolation for overflowing Y differences. When fast intermediate arithmetic still overflows, exact rational affine evaluation of the finite input floats supplies a bounded fallback; truly nonrepresentable results fail explicitly. |
| STEP(1,infinity), PULSE(1,infinity) and RAMP(1,infinity) quietly returned zero; negative pulse repetition became a single event | Explicit errors for invalid parameters | Validate finite arguments and require nonnegative pulse interval. |
| Invalid interpolation mode on a one-point table was silently accepted | Mode contract applies to every table size | Check mode before the constant-table special case. |

Only app/core/equations.py and app/core/integration.py changed. Existing signatures, advertised function sets, model definitions, integration limits and response schemas remain unchanged. The snapshot is private to numerical evaluation. Random draws and fixed-history restrictions are unchanged.

## Method contract and compatibility boundary

The [OASIS XMILE 1.0 standard](https://docs.oasis-open.org/xmile/xmile/v1.0/xmile-v1.0.html), sections 3.3.1 and 3.5, supplies the operator, delay, stochastic and test-input definitions. PULSE uses the XMILE signature **PULSE(magnitude, first_time[, interval])**, returns magnitude/DT for a one-DT window, and uses a single event when interval is omitted or zero. It is not Vensim's two-argument PULSE(start,width).

The [official Vensim Runge-Kutta documentation](https://www.vensim.com/documentation/rungekutta.html) explicitly holds STEP, PULSE and RAMP constant during an integration interval. This patch adopts that discrete test-input convention as the engine's stated method contract; OASIS function signatures do not themselves mandate that RK convention. The [Vensim PULSE manual](https://vensim.com/documentation/fn_pulse.html) confirms its different signature and midpoint comparison. We do not adopt the midpoint shift or infer a Vensim width signature from an ambiguous two-argument expression.

At accepted time t, evaluate a primitive and all arguments using that accepted state. RK4 derivative stages reuse this evaluation. TIME outside those three primitives still takes stage time. RAMP's optional third argument remains the existing engine extension: if end>start, cap at slope*(end-start); otherwise continue.

Consequences:

- RK4 retains fourth-order convergence on tested smooth ODEs, including simultaneous visible/hidden stocks and nonlinear logistic trajectories.
- A held ramp is a left-grid forcing approximation. Its integral converges at first order as DT shrinks, even with RK4; tests demonstrate that fact explicitly rather than claiming fourth order across discontinuities.
- Off-grid events appear at the first accepted sample inside their window. Tests show no early action, correct complete pulse area and convergence of an off-grid step with DT refinement. No automatic event splitting or adaptive integration.
- A horizon ending partway through a pulse may capture partial area, or no integrated area if its first active sample is the final output. Repetition intervals shorter than DT are not an event-count integrator; distinct pulses need an appropriate grid.
- Floating boundary classification handles roundoff-scale differences and supplies no arbitrary absolute time tolerance.

Recommended user-facing engine-contract text: “Euler and RK4 evaluate STEP/PULSE/RAMP at accepted simulation times and hold each complete test input over the following timestep. Other time-dependent equations use the integration method's normal evaluation times. PULSE takes magnitude, first time and optional repetition interval; it is not the Vensim start/width function. Reduce DT to resolve off-grid events. Fixed-history delays and stochastic functions require Euler.”

## Capability matrix

| Advertised names (all explicit matrix members) | Independent verification and scope |
| --- | --- |
| SIN, COS, TAN, ASIN, ACOS, ATAN, ATAN2 | Exact angle/quadrant values; full-series inverse identities and sin²+cos²; out-of-domain inverse functions fail. Radians. |
| EXP, LOG, LN, LOG10, SQRT, POW | Known values, inverse identities across a varied time grid, real-domain/overflow failures; square/power identities. LOG is a natural-log alias with the existing optional base extension. |
| ABS, SIGN, MIN, MAX, FLOOR, CEIL, ROUND, MOD | Negative/zero/positive inputs, bounds and full-series checks. MOD is floor modulus. ROUND retains Python nearest-even ties; an engine extension, not an asserted XMILE rounding rule. |
| IF, IF_THEN_ELSE | Function/statement forms, nested expressions, spaced Vensim spelling, Boolean numeric results, lazy invalid branches. Operator tests check exponent right association, unary precedence, equality and relational grouping. |
| STEP, PULSE, RAMP | Complete accumulated trajectories, areas, boundaries, decimal DT, negative/nonzero origins, large origins, tiny time units, multiple events, off-grid refinement, held arguments and stage-valued ordinary TIME. |
| LOOKUP, WITH_LOOKUP | Named/alias/quoted calls, unsorted inline tuple/list pairs, affine/triangular oracles, endpoint/interior/extrapolation values, continuous/discrete/extrapolate modes, malformed/duplicate/nonfinite data, one-point modes and extreme finite coordinates. Default JSON extrapolation unchanged. |
| DELAY1, SMOOTH, SMTH1 | Whole analytic step/ramp trajectories; default/explicit initial values; changed smoothing duration; visible-stock coupling; Euler seeded-noise discrete convolution. |
| DELAY3, SMOOTH3, SMTH3 | Whole third-order Erlang step curves for multiple initial values, plus default-input initialization ramp curves. |
| DELAY_N, DELAYN, SMOOTH_N, SMTHN | Whole fourth-order Erlang curves, varied initial values, default initialization; noninteger/excessive/changing order and invalid duration fail explicitly. |
| DELAY, DELAY_FIXED | Whole fixed-history ramp series at two grids, fractional delay and prehistory value. Sample-and-hold tested, not described as exact off-grid delay. RK4 unsupported. |
| RANDOM, RANDOM_UNIFORM, NORMAL, RANDOM_NORMAL | Known isolated seeded runtime sequences, aliases, affine time-dependent parameters, actual visible-flow accumulation, hidden-state discrete convolution, reordering/retries and inactive hidden branches. Invalid arity/seed/domain and RK4 fail. No cross-vendor bit identity asserted. |

Existing versioned engine suites add independent ordinary/hidden oscillator solutions, conservation with material in transit, initialization feedback, seeded multithread replay, process-global RNG isolation and fourth-order hidden-state convergence. All were rerun against this patch.

## Initialization, nonlinear cases and unsupported dialects

Initial stock equations resolve forward parameter/stock dependencies at the actual simulation start time, then remain initial values rather than being reevaluated as stock assignments. Tests use start=5 and two dependent stock equations and reject a genuine initial cycle. Hidden-state default initialization uses initial input; explicit initialization is tested for negative, zero and positive values.

The nonlinear logistic reference is K/(1+(K/X0-1)*exp(-r*(t-start))). Three parameter sets cover growth near low/high initial occupancy and negative growth. Both grids compare the complete trajectory; halving DT reduces RK4 error by more than a factor of ten. Mathematical evidence only, not physical-validity claims.

Unsupported PREVIOUS, INIT, EXPRND, LOGNORMAL, TREND, INTEG, arrays/subscripts, zero-argument RANDOM, five-argument truncated-normal dialects, one-argument STEP and four-argument DELAY remain explicit failures. No unsupported name is silently aliased and no missing scientific parameter is guessed. OASIS includes functions outside the advertised subset: this is not complete XMILE conformance.

## Corpus compatibility impact

Static inventory found **zero** tracked model definitions that both select default RK4 and call STEP/PULSE/RAMP. No stored default-RK4 test-input configuration requires a reference migration. Choosing RK4 through an override now follows the documented held-input contract.

Six tracked definitions contain PULSE: agri-food-supply-chain-robustness-agr, addiction-reward-circuit-hea, hares-and-lynxes-population-model-eco, humanitarian-supply-chain-blockchain-eco, penny-distribution-model-eco and capital-constrained-supply-chain-eco. All default to Euler. Decimal-grid output may change where floating modulo introduced duplicates or misses. The addiction expression appears to use start/width-style argument names: an unresolved source/dialect question, not permission to rewrite its equation. The separate corpus audit records current runtime results and observed invocation counts.

## Verification

Focused command: .venv/bin/python -m pytest -q tests/test_advanced_functions_v15.py — **218 passed**.

Frozen engine SHA256:

- app/core/equations.py:c6e396749ff0b149624673fcee5e08863fe20ac5b9564e98875abd8114e6e925
- app/core/integration.py:0de0993725c770bae1a5e4508bb0371ab4817c563f9764c9c50efb978c0a3276

The first matrix run reproduced existing defects before repair. Some higher-order Erlang reference checks required DT refinement to meet an independently chosen tolerance; these were discretization errors, not reasons to change equations or loosen tolerance.

Broad verification command:

    .venv/bin/python -m pytest -q tests/test_advanced_functions_v15.py tests/test_engine_review.py tests/test_engine_sources_v14.py tests/test_regressions.py tests/test_xmile_features.py tests/test_xmile_roundtrip.py tests/test_input_validation.py tests/test_math_sources_v14.py tests/test_healthcare_sources_v14.py tests/test_model_investigation.py tests/test_analytics.py tests/test_workspaces.py tests/test_repair_manifest.py

Result before the final reviewer edge cases: **509 passed**, one pre-existing Pydantic-settings unresolved lifespan annotation warning,45.94 seconds. The final reviewer pass added nine cases: six distant-repeat/off-grid first-pulse cases plus three extrapolation edge cases. Focused engine/XMILE compatibility after those repairs: **434 passed**, one existing warning,8.12 seconds, including all 218 advanced cases. The final full reference rerun completed: **518 passed**, one existing warning, 52.48 seconds. git diff --check passed for owned files.

This is bounded verification of the advertised scalar subset and selected combinations. It cannot exhaust floating-point inputs or prove all possible programs correct. No adaptive solver, stiffness detection, dimensional inference, unsupported dialect coercion or complete XMILE language implementation is added.


## Independent-review edge cases

Independent review found that including a repeat interval's ULP in the pulse tolerance could erase a valid first pulse even before any repeat: PULSE(7,.2,1e20) at t=1,DT=1 returned 0. The tolerance now reflects only local time/start/elapsed/DT arithmetic; the interval is not an error source before a repeat. Independent single-event comparisons at intervals 100, 1e20 and 1e300 and first times .2/.8 verify the entire rate and accumulated trajectories.

Review also found finite extrapolation whose intermediate product overflows: x=5 and points(0,-1e308),(1,-5e307) has affine value 1.5e308. The rare overflow fallback now uses exact rational values of the supplied finite floats to evaluate the affine expression, then converts to a float. Tests independently construct a rational reference and distinguish a genuinely out-of-range result. A subnormal X span with the identity table also extrapolates to 1e308 correctly. Normal table evaluations retain the fast float path.
