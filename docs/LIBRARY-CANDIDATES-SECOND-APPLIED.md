# Second applied candidate batch

Admission update: all ten exact independently reviewed examples are now admitted in source. Approval hashes and destinations are recorded in `operations/library-admissions-second-20261024.json`. Earlier preparation notes follow; source admission does not imply empirical validity or deployment.

Ten candidates, no active-library writes. Source equations and authored closures/scenarios are separated in each description, MANIFEST.json and SOURCE-PROVENANCE.md. Full provenance and numerical receipts reside in `operations/library-candidates-second-applied/`.

| Candidate | Mechanism and useful experiment | Horizon / solver |
|---|---|---|
| Planar VTOL | Coupled translation, rotation, thrust clipping; authored attitude recovery |8s / RK4 .005s|
| DC motor | Current/rotor coupling, torque and back-EMF energy exchange |3s / RK4 .005s|
| Quarter-car | Two-mass suspension and tire damping driven by smooth road rise |10s / RK4 .002s|
| Exothermic CSTR | Arrhenius mass/heat coupling after cooling change |10min / RK4 .005min|
| Binary distillation |32 coupled liquid holdups, VLE and feed stage; reflux change |60min / Radau .1min output|
| Averaged boost | Explicit ideal-switch averaging; inverse initial voltage response |.5s / RK4 .0001s|
| Countercurrent exchanger | Three opposing fluid sections and three dynamic wall sections |20s / RK4 .01s|
| Kalman–Bucy | Observer plus evolving Riccati covariance; deterministic error scenario |30s / RK4 .01s|
| Van de Vusse CSTR | Desired intermediate competes with sequential destruction/dimerization |1h / RK4 .001h|
| Three tanks | Signed square-root communicating flows, exact discrete source plant |200 iterations / Euler1s discrete period|

Validation command: `.venv/bin/python -m pytest tests/test_library_candidates_second_applied.py -q` —14passed in10.63s after final candidate/unit changes. `.venv/bin/python operations/library-candidates-second-applied/record_evidence.py` regenerates full-horizon receipts, inspection and unit diagnostics. Rebuild is isolated to the candidate directory and preserves the declared source/adaptation choices.

All continuous candidates compare every stock at every output against independent tight DOP853 integration and half-grid refinement. Distillation uses a different reference integrator from default Radau. The discrete tank candidate compares every synchronous iteration against a separate NumPy plant map; it is deliberately not refined as if it were a continuous model. Maximum scaled full-series error across ten is8.493e-7 (Van de Vusse); error scaling is `max(abs(actual-reference)/max(1,max(abs(reference),axis=time)))`. This is numerical conformance, not empirical validation.

Independent checks add matrix-exponential solutions for motor, boost and exchanger; Hamiltonian block-exponential Riccati covariance;100random-state conservation/dissipation probes each for distillation component inventory, exchanger wall/fluid energy, suspension stored-energy decay, Van de Vusse elemental inventory, tank volume and CSTR reaction-cancelled enthalpy. Motor and converter power balances receive100random-state probes each. Tests also assert positivity/ranges, boost inverse response and final gain, covariance positive definiteness/steady solution and a distinct distillation separation change. All candidates pass input inspection. Seven have complete consistent symbolic units; VTOL, motor and Kalman–Bucy are explicitly incomplete, with no dimensional errors. The unit checker treats voltage, mechanical units and angles symbolically; incomplete is not promoted to a false pass.

The exact958active files were screened for ID, title/theme and equation fingerprints. EVIDENCE.json retains related names. Existing two-temperature heat exchanger lacks spatial counterflow and wall storage; existing Arrhenius/A→B/Robertson chemistry lacks the chosen open-reactor mass/heat or selectivity mechanisms. Existing SIRD-EKF is epidemic state estimation, distinct from an exposed continuous covariance Riccati experiment. Existing tanker turns do not duplicate flight translation/roll coupling. No active motor, quarter-car, distillation, boost or communicating-tank plant was found. Fingerprints alone do not establish novelty; independent admission review remains required. Other agents were informed to avoid biological mechanism overlaps.

Limitations are explicit: authored feedback is not certified, averaged boost omits switching/losses, exchanger is a chosen low-order discretization rather than a grid-converged device, distillation omits energy/pressure dynamics, isothermal Van de Vusse omits source jacket/controller, and observer covariance is an assumed-model design quantity. No article figures, prose, MATLAB or CasADi code are redistributed. Only two BSD reference implementations/licenses are retained. Mutable pages receive access-date citations; no invented pinned revision or blanket open license is claimed. See SOURCE-PROVENANCE.md for source-access limitations.
