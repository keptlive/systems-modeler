# Applied library candidates: ten feedback and transport systems

## Admission update — October 24, 2026

All ten examples are now admitted after independent numerical and source review. Exact source bytes, approval hashes and destinations are recorded in `operations/library-admissions-20261024.json`. The preparation notes below describe the earlier candidate stage. Deployment status is recorded separately; admission is not empirical certification.

This batch is staged under `operations/library-candidates-applied/`, outside active model discovery. It does not change the active library, its curation manifest, public counts or production data. The ten candidates offer explicit feedback/network/transport mechanisms rather than more logistic, SIR, one-compartment or passive oscillator parameter variants. They require independent admission review.

## Primary source and reuse rights

All model equations come from Richard Murray's [Feedback Systems second-edition Python repository](https://github.com/murrayrm/fbs2e-python/tree/dbbc2e1b4233dc148a3dc52c10d08e87881c1f15), pinned to `dbbc2e1b4233dc148a3dc52c10d08e87881c1f15`. The author's [software page](https://fbswiki.org/wiki/index.php/Software) identifies this repository as the supporting example software. The repository is **BSD 3-Clause**, copyright2021 Richard Murray. Its complete license and13 unchanged source files are retained in the candidate `sources/` directory. No endorsement is implied.

`MANIFEST.json` records every source URL, revision, source-file SHA256, candidate-file SHA256, equation, initial condition, parameter, scenario and numerical grid. Derived bicycle matrices and AFM state/output matrices are recorded as reproducible evidence. Original source remains separate from the translated Stock & Flow JSON. No python-control runtime was added to the application; source matrix derivation used an isolated development environment, while admission tests use existing NumPy/SciPy and our engine.

The source files include executable equations and parameters, which are the reference here; their plot-number/date comments are not independently validated bibliographic claims. CTMS examples whose university pages returned403 were not used to invent missing values. A preliminary scalar queue example was excluded because the current catalog already covers generic queue dynamics; the retained TCP model includes interacting windows and a router feedback law instead.

## What is new and what is illustrative

| Candidate | Mechanism and distinction from active catalog | Initial/scenario and full saved horizon |
| --- | --- | --- |
| `sensor-consensus-five-node.json` | Synchronous discrete five-node Laplacian averaging, distinct from the retained two-fraction social voter model. Exact source graph/gain, mean-preserving and variance-contracting. | Source measurements10,15,25,35,40; gain0.1;40 iterations; Euler/discrete period1 is the recurrence contract, not an ODE approximation. |
| `tcp-red-router.json` | Six TCP congestion-window aggregates representing60 sources coupled to a shared router queue through RED feedback. This is not a renamed M/M/1 queue. | Source equilibrium, seed6 perturbations and half-equilibrium queue; first0–500ms source phase retained. The later source-count change is omitted explicitly because it changes model dimension. RK4,dt0.1. |
| `ship-turning-path.json` | Five-state nonlinear tanker sway/yaw plus position/heading, with authored nonlinear drag and turning instability. | Source zero rudder,initial yaw0.1,other states0;0–100 normalized time;RK4,dt0.02. |
| `whipple-bicycle-stability.json` | Four-state bicycle roll/steer coupling using source mass/inertia/geometry matrices, rather than passive pendulum motion. | Author matrix at chosen stable speed7m/s; our small roll0.01rad,zero other states,10s horizon;RK4,dt0.005. Linear small-perturbation assumptions remain. |
| `nonlinear-cruise-pi.json` | Torque curve, aerodynamic/rolling/gravity loads, actuator saturation and leaky PI controller under a hill disturbance. | Source1600kg,gear4,20m/s reference and4-degree slope ramp at5–6s;0–25s,RK4,dt0.005. Our exact equilibrium is computed for the fixed20m/s command; the source equilibrium routine is allowed to adjust that command. |
| `airfuel-cross-limit.json` | Coupled air/oil PI/process blocks with min/max cross-limit selectors, preserving excess air during load changes. These selectors are authored control logic, not added stability clamps. | Source zero states and101 command samples over0–30s, with source linear interpolation retained;RK4,dt0.0025. Sample-grid ramps are retained instead of claiming ideal steps. |
| `adaptive-noise-cancel.json` | Dynamic plant/filter identification with two adaptive parameters and gradient feedback, beyond a fixed filter. | Source equations/alpha0.01; our deterministic two-tone excitation,zero desired signal,initial filtera=-0.5,b=0 and0–200s. This explicitly replaces the source unseeded white-noise realization;RK4,dt0.02. |
| `active-opamp-bandpass.json` | Two-RC active op-amp band-pass with DC rejection, distinct from the retained passive RLC circuit. | Source100/5000ohm and100microfarad components; our zero-state1V step over0–3s;RK4,dt0.0005. Source file itself plots frequency response. |
| `afm-piezo-modes.json` | Four-state AFM piezo modal realization with source coupled resonances and measured-output Cvector, rather than another free mass-spring oscillator. | Source masses/frequencies; our zero-state unit step over300microseconds;RK4,dt50nanoseconds. Source states are realization coordinates, not all literal displacements. |
| `nonlinear-pendulum-feedback.json` | Authored nonlinear force feedback stabilizes the upright equilibrium and dissipates an explicit Lyapunov quantity. A reviewer may exclude it if the control lesson adds insufficient value beyond existing passive pendulums. | Source gain2; our angle0.5rad,zero rate and20normalized time;RK4,dt0.005. No global region-of-attraction claim. |

Parameters and equations come from the primary author code. Where a file supplies only frequency-response or stability plots, our initial conditions, input and horizon are explicitly illustrative test protocols. A default simulation is not a calibrated vehicle, aircraft, vessel, circuit or safety controller. Actuator/torque saturation and min/max selectors appear only where the author specifies them; singular TCP queue dynamics are guarded by admission evidence, not clipped.

## Numerical and structural admission evidence

`tests/test_library_candidates_applied.py` passes **18 tests**. Every state value over each complete default horizon is compared against an independent reference:

- Exact matrix powers for synchronous consensus.
- Matrix exponentials derived from second-order mass/damping/stiffness equations for bicycle motion.
- Closed-form active-filter response.
- AFM eigensolution cross-checked against direct matrix exponentials at nine times, plus independent Cvector output evaluation.
- Independently handwritten DOP853 derivatives for TCP, ship, nonlinear cruise, cross-limit air/fuel, adaptation and feedback pendulum. The reference uses rtol2e-11/atol1e-12; source command interpolation is separately reproduced.

The full-series admission error metric is the maximum per-state absolute error divided by `max(1, max(abs(reference_state)))`; its limit is2e-5. Actual errors, row counts, issues and work diagnostics are recorded in `VALIDATION.json`, not substituted by a finite-output badge. The worst observed scaled error in the batch is approximately5.7e-7 for cross-limited air/fuel. The nonlinear cruise default uses825,033 of the one-million work budget; a finer grid may correctly be rejected by existing capacity checks.

Behavior checks establish mean conservation and variance contraction, positive TCP queue/window convergence, curved ship path, bicycle roll decay, cruise recovery after the hill, air-leading-fuel ordering, adaptive error reduction, filter DC rejection, and pendulum Lyapunov loss. Step halving improves complete trajectories for the filter, AFM and controlled pendulum; the latter refinement begins atdt0.02 because the saved default is near the reference error floor.

Structural inspection is valid for every candidate. Zero initial states in the driven filter, AFM and air/fuel models trigger the existing `all_stocks_zero` advisory, but their complete trajectories change and independent references match. This warning is not suppressed or confused with inert dynamics.

## Units and duplicate boundaries

Four models have coherent explicit advisory dimensions: normalized consensus, SI-consistent cruise/controller signals, the active RC filter, and the source-normalized feedback pendulum. The remaining six deliberately report **incomplete**, with unknown metadata retained. They have no reported dimension contradiction, but that is not a dimensional-consistency pass. In particular, AFM realization-state units and the source-normalized tanker parameters were not guessed from their names.

IDs, titles, literal flow fingerprints and conservative stock-derivative AST fingerprints were checked against the active923. Canonical fingerprints rename stocks and substitute numeric auxiliaries; they are not a proof of algebraic inequivalence. Manual comparison examined the closest active themes: social voter fractions, M/M/1 queues, passive RLC, ordinary pendulums and grid frequency control. None implements these same network/controller/vehicle mechanisms. The independent peer review is recorded separately in `operations/library-candidates-applied/PEER-REVIEW.md` when available.

If admitted, the staging duplicate assertions must be updated to recognize the reviewed active copies; copying them into the catalog without adjusting the admission harness is expected to fail its no-duplicate assertion. No active file, count or curation decision was changed by this candidate work.
