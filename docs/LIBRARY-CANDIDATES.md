# Ten attributable library candidates

## Admission update — October 24, 2026

Five independently reviewed mechanistic examples are now admitted; the five short chaos/neuron examples remain deferred. Exact source bytes, approval hashes and destinations are recorded in `operations/library-admissions-20261024.json`. The preparation notes below describe the earlier candidate stage. Deployment status is recorded separately; admission is not empirical certification.

These ten definitions are **candidates outside active discovery**, under `operations/library-candidates/`. They do not change the 923-entry active library or its curation manifest. Admission requires the parent's review; the count is not a reason to admit a weak example. All ten complete their source horizons with the current engine, pass input inspection without issues and pass advisory dimension checks under explicitly dimensionless mathematical benchmark conventions. They are not calibrated predictions.

## Source, rights and reproducibility

The executable source of record for this batch is the [MIT-licensed SciML DiffEqProblemLibrary](https://github.com/SciML/DiffEqProblemLibrary.jl/tree/e5c3f5aff3b6921ca79b0862ebae896c7580666e), pinned to `e5c3f5aff3b6921ca79b0862ebae896c7580666e`. The three original source files and complete copyright/license notice are preserved under `operations/library-candidates/sources/`. `MANIFEST.json` records each original source URL, pinned revision, source-file SHA256, citation, every equation, source initial state, parameters, horizon and our numerical settings. Candidate JSONs expose parameters as editable auxiliaries and signed derivative flows into state coordinates; no positivity clamps or added feedback were introduced.

These are translations of the licensed problem definitions, not claims to reproduce the original authors' executable files. The original paper citations are retained where supplied, with primary computational evidence linked to the pinned source. Several publisher landing pages returned403 during checking; their full paper contents were not treated as read. The executable source specifies exact defaults and remains inspectable. The [Hairer testset](https://www.unige.ch/~hairer/testset/testset.html) independently corroborates Robertson and HIRES. Its [HIRES equation source](https://www.unige.ch/~hairer/testset/stiff/hires/equation.f) confirms the first equation contains constant `+0.0007`: the SciML docstring incorrectly prints `+0.0007*y4`, while its executable function is correct. We use the executable function, not that typo. The [Bari Pleiades description](https://archimede.uniba.it/~testset/report/plei.pdf) independently confirms the28-state equations, masses, source initials and horizon.

## Candidate decisions

| Candidate file | Distinct contribution and source convention | Saved horizon / method |
| --- | --- | --- |
| `nonlinear-sequential-chemistry.json` | First-order A→B followed by second-order B→C; total conserved and a Bessel-function closed form. Liu et al., Nonlinear Dynamics68(2012)17–21; not another generic reversible A/B model. | 0–20, RK4, dt0.02 |
| `robertson-autocatalytic.json` | Autocatalytic three-species stiff benchmark, rates0.04,3e7,1e4 and initial(1,0,0). Conserved total. Uniform saved grid does not resolve the fast initial transient; Radau's internal integration does. | 0–1e11, Radau, saved dt1e9 |
| `hires-photomorphogenesis.json` | Eight-state HIRES high-irradiance-response reaction benchmark; distinct from generic enzyme/growth models. Initial U1=1,U8=0.0057; U7+U8 conserved. | 0–321.8122, Radau, saved dt0.3218122 |
| `euler-rigid-body.json` | Effective Euler rotation coefficients(-2,1.25,-0.5), initial(1,0,0.9), two independent quadratic invariants. These coefficients are not moments of inertia. | 0–20, RK4, dt0.01 |
| `pleiades-seven-body.json` | Planar mutual seven-body gravity, masses1–7; unlike the retained restricted three-body system, all bodies move and interact. Exact source initial positions/velocities, no softening. | 0–3, Radau, saved dt0.002, rtol3e-8,atol3e-11 |
| `thomas-cyclic-sine.json` | Cyclic trigonometric coupling with damping0.208186, unlike polynomial Lorenz dynamics. Thomas1999; source initial(1,0,0). | 0–1 source transient, RK4, dt0.002 |
| `dadras-quadratic-flow.json` | Distinct quadratic cross-coupling and damping, parameters(3,2.7,1.7,2,9), source initial(1,0,0). Dadras/Momeni2009 source article identifier retained. | 0–1 source transient, RK4, dt0.002 |
| `chen-three-state.json` | Positive Y self-feedback and(c-a)X coupling distinguish it from the retained Lorenz system; not a renamed Lorenz parameter variant. Chen/Ueta1999, parameters35,3,28. | 0–1 source transient, RK4, dt0.0005 |
| `rossler-three-state.json` | One bilinear nonlinearity and linear X/Y rotation differ from Lorenz/Chen; Rössler1976, parameters0.2,0.2,5.7. | 0–1 source transient, RK4, dt0.002 |
| `hindmarsh-rose-source.json` | Slow adaptation adds a third state beyond the retained FitzHugh–Nagumo neuron. Hindmarsh/Rose1984; source defaults preserved including r0.01,I5. | 0–1 source transient, RK4, dt0.001 |

The five one-unit flows intentionally retain the source library's short horizon and are labeled **transients**. They do not claim to show a full chaotic attractor, bursting cycle, Lyapunov spectrum or long-term stability. They provide distinct local dynamical structures, but a reviewer may reasonably prefer a smaller batch over multiple short mathematical flows. Aizawa was excluded because the upstream citation incorrectly points to Lorenz; existing Lorenz, Brusselator, Oregonator, FitzHugh–Nagumo, Lotka–Volterra and Van der Pol variants were excluded as duplicates. No unverified variant was added just to increase the count.

## Independent evidence and limits

`tests/test_library_candidates.py` passes **19 tests**. It compares every saved state value over each complete horizon against independently handwritten derivatives, using tight DOP853 references for explicit models and tight BDF references for our Radau cases. Reference tolerances are rtol2e-11/atol1e-13; admission bounds are rtol3e-4/atol2e-5. `VALIDATION.json` records actual maximum absolute/normalized errors, output rows, input issues, advisory dimensional reports and work diagnostics. These tolerances are computational accuracy criteria, not physical uncertainty bounds.

Additional tests check the nonlinear chemistry Bessel closed form, exact total mass for both chemistry chains, HIRES U7+U8, the rigid-body quadratic invariants, and Pleiades total linear momentum/center-of-mass motion. Step halving improves full-series RK4 error for chemistry, rigid body, Chen and Hindmarsh–Rose. The last refinement starts at dt0.008 because its finer default is already near the tight reference's error floor.

Deduplication checks compare IDs, normalized flow-equation fingerprints and conservative stock-derivative AST fingerprints with canonical stock symbols and substituted numeric parameters against all923 active definitions. Themes and equations were manually checked as described above. Fingerprints are not a proof of algebraic inequivalence or a comprehensive scientific taxonomy. Candidate tests deliberately fail if the same definitions become active; when admitting them, update the staging/admission tests to recognize the reviewed active copies rather than silently admitting duplicates.

Solver/output grids are our documented numerical choices; source equations, parameters, initial states and horizons are unchanged. Pleiades uses adaptive Radau because close approaches need resolution within the current work budget; its physical equations are nonstiff and no claim is made that stiffness requires this method. No active library file, production data, engine, curation manifest or public count was modified for this batch.
