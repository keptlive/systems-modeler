# Expression and advanced-function hardening, 1.9 B

The independent review found silent errors in fixed-delay phase, scalar-domain
evaluation, and initialization namespace resolution. The changes are confined to
the evaluator; the integration review supplies the declared-name context needed
for initialization. No library equations or parameters changed.

## Reproduced defects and corrections

| Reproduction before correction | Cause | Corrected contract |
| --- | --- | --- |
| `DELAY(TIME-start,4,-1)`, Euler DT 2, seven samples: origin 0 gave `[-1,-1,0,2,4,6,8]`; origin 1e16 gave `[-1,0,2,4,6,8,10]`. Every clock point is exactly representable. | An absolute-clock ULP tolerance exceeded several real timesteps and selected future history samples. | Binary search compares elapsed sample age against delay duration. Boundary roundoff is bounded below one timestep (DT/4). Sample-and-hold behavior is preserved. |
| `IF(1e309>0,1,0)`, `IF(1e308*10>0,1,0)`, `IF((-1)^.5,1,0)` returned 1; `MIN(1/1e-309,7)` returned 7. | Invalid scalar intermediates could disappear inside comparisons or functions before the simulator checked the final output. | Every reached scalar literal, reference, arithmetic result and function output must be finite and real. Errors have `non_finite_result` or `non_real_result` codes. Unselected conditional and logical branches remain lazy. |
| `IF(RAMP(1e308,0)>0,1,0)` at time 10, and `IF(PULSE(1e308,0)>0,1,0)` at time 0, DT .01, returned 1. | Context-function outputs bypassed ordinary arithmetic checks. | The same scalar check covers context-function outputs, TIME and DT. Native table objects and inline coordinate containers retain their existing special handling. |
| A variable named `inf`, `infinity` or `nan` with equation 4 could not be referenced reliably. | The numeric shortcut interpreted Python float-parser spellings as numeric nonfinite values before resolving model identifiers. | Only finite numeric shortcuts return immediately. The AST distinguishes an authored nonfinite literal from an ordinary declared identifier. |
| Stock `e`, initial 10, receives flow `Growth=e`: initial Growth was math.e and one Euler step ended at 12.718281828 instead of 20. | Before the stock initializer resolved, constant fallback cached the declared name as a mathematical constant. | Declared unresolved names shadow constants and trigger the normal dependency retry. Mathematical constants still work when no model quantity declares their names. This requires the integration context's full canonical declared-name set. |
| Infix `1 MOD 0` had a division-by-zero cause, while `MOD(1,0)`, `pow(0,-1)` and `LOG(1,1)` lacked it. | Function dispatch did not translate ZeroDivisionError consistently. | Equivalent function failures carry `division_by_zero` and function details. |

Invalid explicit random-seed errors retain the seed context and underlying cause
after the earlier finite check. No fallback value, clamp, parameter change, or
exception suppression is introduced. Finite lookup interpolation keeps its
existing exact-affine arithmetic fallback: internal implementation arithmetic is
distinct from an authored scalar expression.

## Independent checks

`tests/test_engine_hardening_v19_b.py` contains 55 cases:

- Clock-translation metamorphism at origins 0, 1e12 and +/-1e16, plus decimal and
  tiny-duration delay boundaries at four different scales.
- Reached nonfinite/complex values, lazy invalid unselected branches, function
  zero causes, explicit identifiers using float-parser spellings, and e/pi stock
  initialization under Euler, RK4 and Radau.
- First-, third- and eighth-order delay responses against an independent matrix
  exponential for the linear serial-stage ODE, using Euler and RK4.
- Material conservation for two serial delays: `Source + Sink + 2*Inner +
  3*Arrival = 100` to absolute tolerance 2e-12. Direct nested delay syntax equals
  separate auxiliary stages; endpoint output also matches the analytic two-stage
  step response. Both Euler and RK4 are checked.
- A table named SMOOTH composed inside DELAY1, checked at every sample against
  the analytic first-order response to a ramp. This guards function/table
  precedence and native object handling during hidden-state discovery.
- Seeded uniform/normal draws against separately constructed standard-library
  RNG streams, plus composed calls with equal explicit seeds. The equal-seed
  stream correlation is intentional, documented existing behavior.

The focused file and existing engine review, source-v14, input-v16, XMILE,
lookup-source-v16 and binomial-v18 suites completed with **272 passed, 3 expected
failures**. This is a focused numerical check, not a claim that the public corpus
or all scientific models are correct. The release-wide frozen corpus audit is a
separate gate coordinated by the release owner; changed outcomes from stricter
intermediate validation must be inspected individually.

## Limits retained explicitly

The three expected failures describe existing strict-XMILE gaps: punctuation in
quoted identifiers can collapse under legacy aliases, en-space aliases are too
permissive, and unquoted internal-dollar identifiers are unsupported. These were
not repaired by changing alias compatibility during this numerical review.

Fixed delay is sample-and-hold history on the accepted Euler grid, not continuous
interpolation or a general delay-differential solver. Fixed/history delays and
stochastic calls remain rejected for unsupported integration methods. Dynamic
material-delay duration/order remains unsupported; dynamic information smoothing
is a separate contract. Random parameter changes within a cached accepted time
and stochastic evaluation in conditional branches retain existing stream
semantics; this review does not certify distributional properties for arbitrary
state-dependent switching or native-software random-stream equivalence.

No new guarantee is made for repeat pulses whose interval is shorter than DT,
unresolvable event spacing, or arbitrary non-grid event times. The supported
test-input contract uses one-DT pulse windows and accepted-left-state RK4
evaluation. Strict finite checks validate reached authored scalars; they do not
prove dimensional consistency, positivity, convergence, or source fidelity.

Primary language reference: [OASIS XMILE 1.0, sections 3.3 and 3.5](https://docs.oasis-open.org/xmile/xmile/v1.0/xmile-v1.0.html).
In particular, XMILE MOD uses floored division (the divisor's sign), matching the
existing Python modulo implementation. It was not changed to Vensim MODULO's
different convention. [ISEE test-input documentation](https://ssl.iseesystems.com/resources/help/v3/Content/08-Reference/07-Builtins/Test_input_builtins.htm)
describes the one-DT pulse and volume/DT convention.

## Independent cross-review of request and failure boundaries

`tests/test_engine_crossreview_v19_b.py` adds 11 independent cases. Omitted timing
fields inherit the model's shifted horizon and tolerances. An omitted seed keeps
seed 0; explicit null generates a new seed; an explicit numeric seed replaces it.
Direct and REST results agree in each case. Genuine overflow runs under Euler,
RK4 and Radau all fail with finite JSON evidence rather than returning partial
results. SciPy emits expected overflow warnings for the intentionally extreme
Radau fixture; its failure remains an HTTP 422 response.

Cross-review exposed four defects fixed by the integration reviewer:

- The first continuity checker evaluated LOG as log10 while the engine uses
  natural log. `IF(X > LOG(100), X, 2)` has unequal limits 2 and ln(100) at its
  switch. The incorrect checker certified equality at 2.
- The first checker used Python comparison chaining. In XMILE `2<1<1` is true,
  so `IF(X>0,IF(2<1<1,1,0),0)` jumps by 1 at zero.
- Replacing chaining with a single left fold still mishandled relational versus
  equality precedence. `2=1<1` means `2==(1<1)` and is false; consequently
  `IF(X>0,IF(2=1<1,0,1),0)` also jumps by 1. The checker now delegates literal
  functions and conditions to the actual scalar evaluator after a pure-expression
  whitelist check, retaining exact rational arithmetic for polynomial algebra.
- A numeric stochastic run could succeed before report postprocessing failed.
  Its auto-generated seed was lost because report evaluation occurs outside the
  numeric runtime's exception scope. Report failure now carries the completed
  numeric result's effective seed into reproduction settings.

These counterexamples establish unequal analytic limits, rather than inferring
continuity from sampled trajectories. The revised bounded certificate expands
algebraic aliases and compares restricted branch expressions at each boundary;
it is a conservative accepted-syntax check, not a global proof of ODE accuracy,
existence, uniqueness, stiffness behavior or domain validity. Unknown boundaries
remain unsupported. State-dependent lookup forcing is conservatively rejected
until event localization can prevent missed narrow features.

The independent file passes all 11 cases; the combined cross-review, request and
root reproduction suites pass 51 cases. The existing JavaScript failure-report
check also passes after the release owner's correction to role-sensitive model
signatures and failed-snapshot invalidation. The downloadable report retains the
captured failed model and effective settings, independent of later in-memory
edits. No C/root runtime files were edited during this cross-review.
