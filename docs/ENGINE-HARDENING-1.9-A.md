# Numerical engine hardening: independent review A

Reviewed the staged 1.9 engine from commit `cc010ae`. This review changed integration scheduling, accounting and the supported adaptive-input contract, with no saved-model changes. The engine remains a numerical evaluator: successful completion does not establish scientific validity.

## Reproduced silent errors and repairs

**Declared `e`/`pi` before initialization.** With stock `e=10` initialized by an equation and incoming flow `Growth=e`, a one-step Euler run returned `12.718281828459045` instead of `20`. Pending flows were evaluated before equation initializers; the evaluator substituted the mathematical constant and never retried the apparently successful flow. RK4/Radau also retained the wrong initial flow even when their final stock was correct. Simulation contexts now carry all declared names. Agent B's evaluator rejects an unresolved declared symbol before considering the mathematical constants. Lazy conditional dependency resolution remains supported; variable order is not prescribed. B's independent tests cover both constants, initializer/auxiliary declarations and all three methods.

**Adaptive solver skipped an entire pulse.** The following deterministic model returned a successful zero integral under SciPy 1.18.1 when calling the former unguarded Radau path:

```text
X(0)=1; Y(0)=0
X'=X
Y'=IF(X>2 AND X<2.001,1,0)
start=0; end=5; dt=.1; rtol=1e-9; atol=1e-12
```

The exact final `Y` is `log(2.001/2)`, approximately `0.00049987504`; the old result was `0`. A continuous lookup with points `(0,0), (2,0), (2.00025,1), (2.00075,1), (2.001,0), (1e10,0)` also returned `0` for `Y'=Lookup(X)`, despite its positive integral. A simpler constant clock `X'=1` skipped a pulse of width `.1` with only 44 RHS evaluations over `[0,20]`.

These are missed features, not physical instability. Saving more output samples does not force internal solver steps. SciPy documents `t_eval` as storage times, error control as a local estimate, and the possibility of missed event crossings within one step. See the primary [solve_ivp documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html). No new `max_step` heuristic or tolerance change is presented as a guarantee.

Radau now rejects uncertified stock-dependent switches in the transitive stock-derivative dependency closure. It also rejects stock-dependent lookup forcing in that closure until table knots can be localized reliably, including continuous interpolation. This does not claim that every such lookup gives an incorrect trajectory. Discontinuous diagnostic variables and diagnostic-only lookups remain available at retained output times. The prior TIME-switch restrictions remain in effect.

The guard preserves continuous `MIN`/`MAX`/`ABS` and certifies a limited class of IF branches with matching boundary values. Alias expansion, rational polynomial comparison, continuous elementary atoms and scaled boundary substitution recognize zero-crossing feedback and the source pipe-friction transitions. Constant functions and conditional truth use the actual scalar evaluator, including natural `LOG` and XMILE comparison precedence. Unknown denominators/domains, chained state comparisons and unproved boundaries fail closed. Expansion depth/node count, polynomial degree/terms and rational coefficient size are bounded. This check proves only the supported boundary equality; it is not a global ODE-domain, existence, uniqueness or error certificate.

Independent adversarial cases exposed and fixed two early proof mistakes: using base-10 `LOG` rather than natural log, and treating XMILE comparisons as Python chains or a simple left fold across mixed equality/relational precedence. A third test rejects a state comparison chain whose intermediate Boolean creates boundaries absent from adjacent scalar equalities. The final tests retain all these counterexamples.

**Uncharged dependency retries.** A reverse-ordered chain of 500 auxiliaries can require 125,250 scalar evaluator attempts for one retained state, whereas the old budget charged 500. Integration now charges every repeated attempt before executing it. Radau includes retries alongside every initial/RHS/Jacobian/output model evaluation. Euler/RK4 reserve their initial evaluation as well as integration work, and reduce the stochastic-trial budget by retry work. The existing element, interval and work limits remain; no new element cap or fixed dependency ordering was introduced. Work units bound per-element evaluations, retries, hidden-stage work and stochastic trials, rather than claiming to count every AST node or floating-point operation.

**Unreproducible failed random runs.** Numeric failures now retain the effective random seed in `EquationError.details.random_seed`, including an automatically generated seed. A report-stage failure retains the successful numeric run's seed as well. Root's failure wrapper propagates this into its reproduction settings. Successful RNG semantics are unchanged.

**Flow cancellation erased real dynamics.** All three methods returned `X=[0,0]` for `X(0)=0`, external inflow `1`, and a subsequent self-loop flow of `1e20` from X back to X over one unit interval. Sequential accumulation computed `1-1e20+1e20=0`; the exact derivative is `1`. Both stock-derivative accumulators now use `math.fsum` over signed flow terms. Independent self-loop/opposing-flow and element-order permutations check every method against `X(t)=t`.

**RK4 weighted-sum overflow.** A constant derivative `1e308` over the single interval `1e-308` has the finite exact increment `1`, but `2*k2` overflowed before multiplying by the small interval. RK4 now scales stage weights before compensated summation, including hidden stages. Exceptional subnormal rates use a bounded four-term rational combination of the actual input floats, so dividing a tiny rate by six cannot erase an increment restored by a large interval. Tests separately cover large rates, subnormal rates and small terms between cancelling RK stages. The last test checks the exact prescribed RK quadrature, without claiming that a single step accurately resolves that discontinuous forcing.

## Saved-model impact at the review freeze

Scanning all saved Radau models against the new guard identified exactly these five definitions before Agent B's separate solver/source investigation:

| Model ID | Exposed adaptive-contract issue |
| --- | --- |
| `grid-frequency-stability-ene` | `Reserve Deployment`: nonmatching jump at the frequency deadband |
| `traffic-flow-dynamics-soc` | `Queue_Dissipation`: discontinuous discharge multiplier |
| `milgram-small-world-soc` | `Step_Count`: stock-triggered unit/zero rate |
| `greenshields-traffic-flow-model-tra` | `Queue_Growth`: stock-triggered nonzero/zero rate |
| `world2-forrester-original-cla` | Fifteen stock-dependent lookup auxiliaries in stock-derivative paths |

The pipe model's friction force is certified at Reynolds numbers 2000 and 4000; its diagnostic flow-regime integers do not restrict the solver. Continuous auction experience gains, DMP vacancy creation, thermoregulation MIN/MAX feedback and diagnostic carbon airborne-fraction branches remain permitted. This inventory separates newly exposed unsupported inputs from the earlier source-repair failure register. Any subsequent changes to those model defaults require their own source and convergence receipts.

## Independent verification

The focused command completed **195 passed**:

```text
.venv/bin/python -m pytest -q \
  tests/test_engine_hardening_v19_a.py \
  tests/test_engine_hardening_v19_b.py \
  tests/test_engine_crossreview_v19_b.py \
  tests/test_radau_v18.py tests/test_capacity_v17.py \
  tests/test_report_outputs.py tests/test_independent_review_v19.py
```

The tests include exact Euler/RK4 exponential step polynomials on a partial final interval, analytic Radau decay, simultaneous two-reservoir conservation, retained flow/stock consistency, a coupled visible/hidden smooth system solved independently by characteristic roots, fourth-order refinement, lazy forward initializer permutations, explicit narrow-pulse/lookup rejection, diagnostic allowance, adversarial boundary proofs, retry work interruption, and generated-seed replay. The hidden-state final errors at `dt=.1,.05,.025` were approximately `1.2561e-7, 9.3692e-9, 6.3190e-10`, converging toward fourth order. The historical Radau stock-switch test now preserves a continuous matching-limit positive case and separately rejects its former nonmatching branch.

Expected warnings in the focused run came from intentional overflow-failure probes and an existing Pydantic settings warning. The parent owns the final complete suite, all-model audit and release decision. No deployment or push was performed by this review.
