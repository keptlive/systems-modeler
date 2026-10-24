# Native engine research roadmap

Reviewed October 24, 2026 against local source at base commit `01a4362` plus the current uncommitted native-engine integration. This is a research and implementation sequence, not a claim that the proposed capabilities exist or that another package has been benchmarked here. Only primary project documentation, source and research papers are used. No production changes, dependency installation or engine replacement occurred.

## Current evidence and boundaries

The engine already has safe cached scalar AST evaluation, Euler, RK4, explicitly selected Radau, hidden delay/smoothing state, seeded stochastic execution, reports, bounded execution, timestep investigation, native structured lowering, advisory dimensional analysis, retained-source scalar MDL import and opt-in local feedback response. The new immutable per-run evaluation plan caches metadata; it does not yet replace dependency retries with a compiled schedule. Files inspected: `app/core/integration.py`, `equations.py`, `adaptive.py`, `limits.py`, `structured.py`, `mdl_parser.py`, `feedback_analysis.py`, `units.py`, API routes and MCP tools.

The existing `app/llm/tuner.py` already runs plus/minus 20% parameter experiments and optional paid-AI tuning. The gap below is a deterministic, explicit numerical sensitivity/calibration contract with budgets and data provenance, not the absence of all sensitivity functionality. Native local Jacobians are not quantitative loop attribution. Native JSON arrays/modules do not establish XMILE array/module interoperability.

Three read-only probes were executed in a fresh Python process:

| Probe | Observed result | Interpretation |
| --- | --- | --- |
| Sixty reversed-order auxiliary declarations: x0=1, xi=x(i-1)+1; two retained samples | 3,660 calls to the scalar evaluator; x59=60 | Verified scheduling overhead opportunity; no wrong numerical result |
| dX/dt=STEP(1,0.15), X(0)=0, end=1, dt=0.1 | Euler ends at about 0.8; continuous event-aware solution is 0.85 | Existing documented grid-held input semantics; new event semantics would require explicit opt-in |
| Same STEP model under Radau | Explicit unsupported_method_features rejection | A deliberate capability boundary, not permission to remove the guard |
| MEAN(x[D]) over a native array | Explicit unbound-dimension failure | Reduction support is narrower than arbitrary array operations; it is not silently computed |

No additional reproducible release blocker was found during this read-only integration inspection. This is narrower than a security or complete numerical audit. Existing structured/MDL/MCP regression suites and frontend probes remain the acceptance evidence; this document does not supersede the integrating maintainer's full-suite results.

## Recommended sequence

Effort estimates are engineering days for a bounded initial implementation plus focused tests, assuming one experienced maintainer. They exclude production rollout and scientific review. Each estimate is judgment, not a measured promise.

| Order | Deliverable | Value and scope | Estimate | Dependency |
| --- | --- | --- | --- | --- |
| 1 | Safe dependency schedule and benchmark manifest | Faster existing runs without changing authored equations | 3–5 days | Current evaluator oracle and work-budget regression |
| 2 | Deterministic parameter-sensitivity tool | Answers which explicit assumptions matter, without paid AI | 3–5 days | Reproducible scenario/run receipts |
| 3 | Native array reductions and structured XMILE subset | Makes current structured projects more useful and portable | 5–10 days | Stable source model/compiler boundary |
| 4 | Scheduled event mode, then segmented stiff integration | Handles off-grid interventions with explicit semantics | 5–8 days, then 5–10 | Event contract and discontinuity tests |
| 5 | Bounded calibration plus identifiability evidence | Fits declared observations without pretending parameters are uniquely known | 5–8 days, then 5–10 | Sensitivity and observation schema |
| 6 | Optional numeric VM/JIT experiment | Potential throughput gains for repeated smooth deterministic models | 5–10-day measured prototype | Schedule/IR and benchmark acceptance |
| 7 | Genuine scalar LTM research prototype | Explains changing loop influence, distinct from local stability | 10–20+ days | Instrumented execution/history and bounded graph analysis |

### 1. Dependency schedule before JIT

Our reverse-chain probe establishes excessive retries, not a blanket performance diagnosis. Build a typed internal plan with resolved symbol slots, separate initialization and rate schedules, dependency provenance, and the original scalar evaluator as oracle. Initially schedule only an unambiguously acyclic numeric subset. Keep branch-dependent/lazy references and unresolved-cycle diagnostics on the existing path: evaluating an inactive branch can introduce division errors or spurious algebraic cycles.

Simlin's pinned VM resolves modules into indexed runtime structures, while its documented incremental design separates symbol identity from final slot layout. That supports the architectural idea of stable identity plus a cheap assembly pass; it does not prove our workloads need Rust or an incremental database. [Pinned VM](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/vm.rs), [incremental compilation design](https://github.com/bpowers/simlin/blob/main/docs/design/2026-02-21-incremental-compilation.md).

Acceptance: compare complete trajectories and error causes on forward/reverse chains, lazy IF, time primitives, initializer dependencies, duplicate aliases, random callsite streams, hidden states and each solver. Charge instruction/evaluation work consistently rather than raising capacity merely because retry overhead disappeared. Record cold parse, compile, warm execution, peak memory and result materialization separately. First success criterion: near-linear dependency work on the reverse-chain fixture, unchanged answers and explicit rejection behavior. This is an optimization project; no numerical bug is established by the probe.

### 2. Deterministic sensitivity, then gradients

Add an independent numerical tool accepting an immutable source model, explicit numeric parameter IDs/cells, finite bounds/perturbations, named output metrics, solver settings and an aggregate evaluation budget. Start with central finite differences and a second perturbation size; report derivative agreement and zero-baseline handling. Preserve the existing AI tuner as a separate user path. Synthetic analytic case: X'=kX has dX(t)/dk=tX(t); an additive parameter initially equal to zero must still receive a meaningful absolute perturbation.

PySD documents a translation-to-Python AST architecture and integration with external analysis packages; its advanced usage is a useful workflow reference, not evidence that a specific calibration algorithm is built into our application. [PySD architecture and limitations](https://pysd.readthedocs.io/en/master/), [advanced usage](https://pysd.readthedocs.io/en/master/advanced_usage.html).

For global sensitivity, evaluate a separate optional SALib adapter only after the batch runner can budget every failed and successful run. Its sampler/analyzer workflow leaves model execution to the caller. Do not label the existing one-at-a-time 20% scan Sobol sensitivity. Test an independent analytic interaction function and sampling-seed replay; disclose assumptions about input distributions and dependence. [SALib workflow](https://salib.readthedocs.io/en/latest/user_guide/basics.html).

Later forward sensitivities would integrate S'=f_x S+f_p, including initial-condition derivatives. SUNDIALS CVODES supplies a primary reference for forward and adjoint sensitivity capabilities; adding it as a runtime dependency is a separate packaging and reproducibility decision. Events and resets require their own derivative rules. [CVODES introduction](https://sundials.readthedocs.io/en/latest/cvodes/Introduction_link.html).

### 3. Expand arrays and interchange in narrow, tested slices

First add explicit MEAN/MIN/MAX reduction nodes to our structured expression grammar, then literal slices and dimension mappings only with a documented shape contract. Avoid further regex growth as array expressions become richer: parse a typed reference/reduction AST and lower it into our own scalar IR. Keep module inputs read-only, outputs explicit and stock-flow connections local until a deliberate cross-module material-flow design exists.

Next import/export the supported XMILE dimension/equation subset into the retained native source representation, rather than importing a flattened execution snapshot. A first two-region stock test must preserve dimension order, member names, default/override equations, initial values, units, and exact flow endpoints across export/import. Still reject unsupported mappings, module arrays, conveyors or queues with actionable diagnostics. Nonempty visual connectors remain a current restriction until regeneration is explicitly supported.

The OASIS standard is the authority for interchange semantics. PySD and Simlin can serve as independently version-pinned readers on shared fixtures; agreeing engines can still share an assumption. BPTK's current primary README advertises multidimensional models and a Python/Rust backend split, which makes it a useful conformance reference, not a drop-in implementation contract. [OASIS XMILE 1.0](https://docs.oasis-open.org/xmile/xmile/v1.0/os/xmile-v1.0-os.html), [BPTK primary repository](https://github.com/transentis/bptk_py).

Acceptance: hand-expanded independent reference trajectories, shape-invalid cases, semantic source round trips and explicit loss inventories; structured browser edit/save/reload/compile/run plus MCP. Preserve source code and notices for any imported sample.

### 4. Events and stiff discontinuities

Introduce a new opt-in event contract instead of changing legacy STEP/PULSE/RAMP timing. Stage A: known scheduled times that split an integration interval, with explicit before/after evaluation, simultaneous-event order, retained-output policy and budget. Stage B: scalar continuous root conditions with direction, terminal/reset behavior, hysteresis or retrigger policy, and a maximum event count.

Analytic tests: off-grid unit STEP integrates to 0.85 by t=1; x'=1 crossing x=0.35 localizes at 0.35; a reset model documents whether the event appears once or twice in retained output; two same-time resets have deterministic order. Include a grazing root, multiple crossings within one proposed step, an initial-time root and a Zeno-like repeat that must hit a budget.

SciPy's event interface detects continuous roots with direction/terminal controls but warns that multiple roots within a step may be missed. Its t_eval requests outputs rather than constraining internal step boundaries. SciML's distinction between continuous root-finding callbacks and discrete callbacks is a design reference for detection versus state modification. [solve_ivp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html), [SciML callbacks](https://docs.sciml.ai/DiffEqDocs/stable/features/callback_functions/).

Only then allow a bounded scheduled-forcing subset under Radau: integrate separately to every declared forcing boundary, retain the pre-event state, apply the declared intervention and restart. Do not simply remove current time-lookup/discontinuity rejection or set a small max_step and declare correctness. Test a very narrow forcing pulse and stiff decay with a known piecewise exact solution. State-dependent nonsmooth boundaries require independent event localization/certification; smoothing the user's equation is not a substitute. Preserve existing Radau budget accounting, tolerances and no-fallback behavior.

### 5. Calibration is an observation contract plus an optimizer

Add observations with explicit series names, time units, timestamps, missing-data rules, uncertainty weights, model/data hashes and immutable source. Reject automatic unit matching or nearest-time joins. Stage one can require observation times on the retained grid. A fit result should return parameter proposals, residuals, assumptions, termination reason, failures and total simulation work, without silently saving changed equations.

SciPy least_squares provides bounded residual minimization and robust losses. Its complex-step derivative option requires analytic continuation, so it is inappropriate for our general comparison/lookup/real-only evaluator. Begin with finite differences and strict run limits; do not treat max_nfev alone as the complete application budget because derivative probes and integrations consume work too. [least_squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html).

Tests: recover k from noiseless exponential decay with known X0; show biased residuals from deliberately wrong units; distinguish integration failure, exhausted budget and optimizer convergence; leave source unchanged. An optional seeded global search can explore multiple minima, but SciPy documents its larger evaluation demands; it should not become a hidden default. [differential_evolution](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html).

Identifiability must accompany stronger claims. In X'=-(a+b)X, perfect X(t) observations determine a+b, not a and b separately: equal sensitivity columns and an optimizer's successful termination cannot establish unique parameters. Start with scaled sensitivity singular values/rank warnings, explicitly numerical and local. Profile likelihood is a later bounded reoptimization tool; formal structural identifiability requires a separate restricted-model method. Test a+b versus independently observable two-parameter cases. [Raue et al., original identifiability paper](https://doi.org/10.1093/bioinformatics/btp358).

### 6. Optional VM/JIT experiment

After the plan/IR exists, prototype an explicit numeric backend for pure deterministic arithmetic, lazy branches and indexed arrays. Compile validated IR, never execute raw uploaded Python or generated arbitrary source. Version the backend in receipts and require explicit selection initially; unsupported constructs must fail clearly. A later per-submodel fallback would need proof of matching evaluation order, state and randomness semantics.

BPTK currently describes compiled Rust execution with Python fallback; that is evidence that multiple backends are feasible, not evidence that adopting its fallback policy preserves our contracts. Numba documents nopython restrictions and floating-point changes under fastmath. A Numba prototype should keep fastmath disabled and avoid reassociation that changes overflow/nonfinite or cancellation behavior. [BPTK architecture](https://github.com/transentis/bptk_py), [Numba performance and fastmath](https://numba.readthedocs.io/en/stable/user/performance-tips.html).

Gate on measured application workloads: reverse-chain auxiliaries, 100-cell arrays, nonlinear smooth ODEs and repeated calibration runs. Include cold compilation so a small interactive model is not penalized for a warm-run-only claim. Keep the Python evaluator as a supported oracle. No speedup target is asserted before measurement; if serialization/solver work dominates, stop the JIT experiment and optimize the measured bottleneck.

### 7. Genuine LTM, separately named from local feedback

The current local stock-rate Jacobian/eigenvalue analysis answers local response/stability questions. LTM scores historical changes through individual causal links and loops; it cannot be manufactured by renaming Jacobian entries. Begin with a scalar, deterministic, fixed-step research tool with explicit previous/current values and ceteris-paribus link evaluation.

The original paper is the method reference. Pinned Simlin code separates causal-graph/SCC/circuit enumeration from execution instrumentation with synthetic historical score equations; its budget-aware graph design highlights why exhaustive loop enumeration is unsafe on dense feedback graphs. [Original LTM paper](https://doi.org/10.1002/sdr.1658), [pinned graph implementation](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/ltm/mod.rs), [pinned instrumentation](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/ltm_augment.rs).

Acceptance: single reinforcing growth, single balancing decay, logistic growth with changing influence, zero-change links, cancellation near turning points, repeated references to the same dependency, and disconnected stock partitions. Report undefined/near-zero denominator scores rather than replacing them with confident zeros. Verify against independent published examples and pinned reference output. Limit nodes/circuits/evaluations and report truncation. Defer arrays/modules, hidden state, stochastic models and adaptive-step attribution until their score semantics are specified. This is a research feature with substantial interpretation risk, not an overnight UI label change.

## Licensing and source discipline

| Reference | Verified notice | Rule for our work |
| --- | --- | --- |
| Simlin engine | Apache-2.0 in pinned source headers | Attribution/license/NOTICE review if code is reused; architectural inspiration does not authorize stripping notices |
| SDXorg sample corpus | Separately MIT-licensed, retained locally | Preserve sample-level provenance; do not assume all third-party Simlin test data has the engine license |
| PySD | MIT | Retain notice for copied substantial code/fixtures; independently validate translated semantics |
| BPTK-Py | MIT-style permission notice | Preserve exact copyright/permission text for copied portions; inspect Rust/transitive dependency notices separately |
| SciPy | BSD-3-Clause | Preserve notices for redistribution and review bundled components separately |
| Numba | BSD-2-Clause | Optional dependency only after LLVM/llvmlite and distribution review |
| SALib | MIT | Keep optional adapter and sampling version/seed in receipts |
| SUNDIALS | BSD-3-Clause | Optional solver integration requires binding/build and transitive dependency review |
| OASIS specification and research papers | Specification/paper rights are separate from software licenses | Cite concepts; create original fixtures or retain explicit fixture rights; no blanket copying permission inferred |

Primary notices: [PySD](https://raw.githubusercontent.com/SDXorg/pysd/master/LICENSE), [BPTK](https://raw.githubusercontent.com/transentis/bptk_py/main/LICENSE), [SciPy](https://raw.githubusercontent.com/scipy/scipy/main/LICENSE.txt), [Numba](https://raw.githubusercontent.com/numba/numba/main/LICENSE), [SALib](https://github.com/SALib/SALib/blob/main/LICENSE.md), [SUNDIALS](https://raw.githubusercontent.com/LLNL/sundials/main/LICENSE).

Online main/stable pages were inspected on the review date and can change. Pin the exact package/source revision before reusing code or fixtures. Research references above justify experiments and semantic requirements; they do not establish cross-engine numerical equivalence, calibration validity, or a production dependency decision.

