# Independent admission review: second applied batch

Reviewed October24,2026. **Approve all ten exact file hashes below**, within their stated teaching/adaptation scope. No candidate JSON, tests, runtime or active-library data was changed by this reviewer. Approval establishes an attributable mathematical example with checked default numerics; it is not empirical calibration, hardware certification or scientific validation of every parameter choice.

## Independently executed checks

The scoped suite independently completed **14 passed in11.40s**. All retained stocks/times are checked against independent handwritten DOP853 equations or the independent synchronous tank map, with half-grid and analytic/conservation probes. Maximum reported full-grid scaled discrepancy8.493e-7 is a numerical error measure, not empirical accuracy.

An additional1,000 random-state probes (100/model, physical domains where required) evaluated the actual saved models through the canonical expression engine and compared stock derivatives against separate numeric equations. Maximum normalized discrepancy8.20e-14. This covers wiring away from the default trajectory, signed communicating flows and piecewise road forcing.

Independently reconstructed pre-step equilibria gave CSTR residual7.82e-14 and all32 distillation-balance residual1.51e-15 at ratio0.7. Actual quarter-car outputs after the road rise matched an exact matrix propagator, final error2.52e-10. Actual engine covariance at21times over0–10s matched the Hamiltonian block-exponential Riccati solution, maximum discrepancy3.66e-10.

Default executions respect unchanged engine limits. Explicit ordinary-work estimates range3417–450018 (quarter-car largest); distillation adaptive diagnostics report160072 work units. These are default checks, not assurances for arbitrary parameter/horizon changes.

## Primary sources and rights

Independently retrieved the university [motor](https://www.ece.ualberta.ca/~tchen/ctm/examples/motor/motor.html) and [suspension](https://www.ece.ualberta.ca/~tchen/ctm/examples/susp/susp.html) pages, [APMonitor CSTR](https://apmonitor.com/pdc/index.php/Main/StirredReactor), [APMonitor GEKKO distillation branch](https://apmonitor.com/wiki/index.php/Apps/DistillationColumn), and [Harvard observer/Riccati equations6.31–6.32](https://hankyang.seas.harvard.edu/OptimalControlEstimation/output-feedback.html). Relevant equations/constants agree. Source motor inertia labels and CSTR comments contain inconsistent units; the documented canonical inertia interpretation and coherent CSTR numerical convention are explicit adaptations.

Pinned do-mpc [CSTR](https://github.com/do-mpc/do-mpc/blob/9d5a8df0e4d6acac899bf0a65ffd4c30a6e2e4cc/examples/CSTR/template_model.py), [tank plant](https://github.com/do-mpc/do-mpc/blob/9d5a8df0e4d6acac899bf0a65ffd4c30a6e2e4cc/examples/triple_tank_ekf/template_model.py) and [tank scenario](https://github.com/do-mpc/do-mpc/blob/9d5a8df0e4d6acac899bf0a65ffd4c30a6e2e4cc/examples/triple_tank_ekf/main.py) were independently retrieved. Source sp=5*1e-5 equals5e-5, with drain factor0.8, initial state(2,2.8,2.7), inflows0.0001 each, and synchronous1-second map; the candidate agrees.

The direct CTMS boost URL returned403. Primary CTMS search retrieval provided ON/OFF Kirchhoff balances and capacitor operation through [this indexed URL](https://ctms.engin.umich.edu/CTMS/index.php/example%3DMotorSpeed?aux=Activities_BoostcircuitA). The saved ideal-switch average is an explicitly authored closure, independently consistent with inductor/capacitor balances; it does not claim to reproduce the particular switched experiment.

Retained BSD materials were independently downloaded from pinned revisions and compared byte-for-byte:

| Source | SHA-256 |
| --- | --- |
| python-control examples/pvtol.py | 912e657459c5522103924a1863f67dfcd67f5706a4c34f61ba371f284dd11be7 |
| python-control root LICENSE | c60bd121183225d2e215b8a582b11da6012da70fd7e1bc9d647cda4dc3c71aa6 |
| ScalableTestSuite Thermal/HeatExchanger.mo | c0889aa5631399469965ba020031508777f9093ea8a7b3a9e4423d487578efbb |
| ScalableTestSuite root LICENSE.md | 9fa0630e818803304d45f4f247df8fa541e3edc7a2482a95ec8e353f4ad8178c |

Their complete BSD notices accompany the files. Other sources supply mathematical references; source prose, figures and MATLAB/CasADi implementations are not bundled. do-mpc LGPL code licensing is identified without claiming it automatically licenses all scientific content. The saved scalar equations and prose are original transcriptions/adaptations. No blanket open license is asserted for university pages. Preserve source attribution and retained notices with the package.

## Novelty and dimensional scope

Screened958 active JSON models and other staged batches by identity/title/equations, then inspected relevant mechanisms. The active two-temperature exchanger lacks counterflow sections/wall states; tanker/pendulum examples lack this VTOL plant; simple chemistry lacks the selected coupled thermal reactor or competing selectivity pathways; SIRD-EKF does not expose this continuous Riccati experiment. No active motor, quarter-car, distillation, boost or communicating-tank plant was identified. First-applied and biological/environmental batches use different mechanisms. Fingerprints are conservative checks, not proof under arbitrary transformations.

Seven models report consistent symbolic units. VTOL, motor and Kalman–Bucy explicitly report incomplete metadata (19,10,18 unknown items respectively), with zero dimensional errors. **They are not approved as dimensionally certified models**: unknown metadata stays visible. Their physical laws were independently reviewed. Completing annotations is a useful follow-up; these hashes retain the honest current scope.

No mandatory corrections remain. Declared limits include omitted distillation energy/pressure dynamics, omitted boost switching/losses, chosen low-order exchanger discretization, deterministic observer error and uncertified authored feedback. Changed settings/source claims require fresh checks and hashes.

## Exact reviewed files

| File | SHA-256 | Decision/reason |
| --- | --- | --- |
| planar-vtol-coupled-flight.json | 8785c2792b29e898ac4a8cf1b6b7cfa716e77b4a373762765c0d2328af96cb29 | Approved: exact pinned six-state plant/constants/force limits; authored attitude-recovery gains and hover lift. No position-regulation claim. |
| dc-motor-armature-speed.json | a7cc858348a010cd0033eed4403d2cb960d454854beadfb5ef6d485da19452f1 | Approved: source plant/constants, zero state and1V input; back-EMF/torque coupling checked by energy and matrix solutions. |
| quarter-car-road-suspension.json | 9ac4d42783759fa3d55b3b70f34f75a44495debb2c97e11a66fd1e1cd206ca66 | Approved: all source plant constants; authored smooth road protocol includes tire damping road velocity. Exact post-rise propagation and dissipation checked. |
| exothermic-cstr-cooling.json | 33442a6193ae6db8210074ab5f139664413bacf5305222af1dce84a2304aea90 | Approved: source numerical mass/heat laws and300K coolant equilibrium; declared coherent unit convention and authored shift to295K. |
| binary-distillation-thirty-two.json | 6241fbc62baf40a870f66da52591d14aa705e18440704ad6e18ee21e5c445aa7 | Approved: GEKKO source balances/holdups/volatility, independently verified ratio0.7 profile, post-step ratio3. Legacy APM branch correctly excluded. |
| averaged-boost-duty-response.json | f1a92ded07523ec1c542ed58db480ad3b6533d19b7b7a913bc8be0e70ee8490a | Approved: explicit authored ideal-switch average, with correct inverse response/DC gain/power balance. Switching/loss effects excluded. |
| countercurrent-exchanger-wall-storage.json | 58e9bded4109cc12aa752fa99c334b48f3e9c83241463766ff216b55a46c2eae | Approved: pinned midpoint-film/counterflow/wall equations; authored nine-state capacities/conditions. Effective wall J/K label resolves source ambiguity. |
| kalman-bucy-riccati-tracker.json | 073c738e5071464ba1d922a53c8e48333c3f833f95ad51963cec132cc29eae9a | Approved: correct continuous observer/Riccati specialization; deterministic error and design covariance interpretation explicit. No stochastic-confidence claim. |
| van-de-vusse-selectivity.json | 9e9aa9dca65cde41a89d2e9f5fe4beee4208ef145168d0d2528359f3bcd3a825 | Approved: source Arrhenius laws at403.15K, authored dilution/products closure, correct half-rate dimer stoichiometry and elemental balance. |
| three-tank-nonlinear-hydraulics.json | 54ed9e1b5218956f02cc8af21457e2db115c329245d2d42298617c4993f17367 | Approved: exact source hydraulic coefficients, true initials/inflows and synchronous1-second map. Discrete conformance, not continuous-grid convergence. |
