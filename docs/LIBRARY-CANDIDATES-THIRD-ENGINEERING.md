# Third engineering candidate batch

Admission update: eleven exact independently reviewed examples are now admitted in source; hashes and destinations are in `operations/library-admissions-third-20261024.json`. Earlier preparation notes follow. Admission is not empirical validation or proof of deployment.

Eleven source-backed candidate reconstructions; no active files or runtime edits. Full equations, parameters, initials, settings and SHA256 hashes are in `operations/library-candidates-third-engineering/MANIFEST.json`. Provenance, source rights and adaptations are detailed in SOURCE-PROVENANCE.md; retained BSD sources/licenses have individual receipts. Authored scenarios are not represented as published benchmark trajectories or equipment calibration.

| Candidate | Distinct mechanism | Demonstrated horizon/settings |
|---|---|---|
| Lyapunov MRAC | Online state/reference gain adaptation with an exact Lyapunov derivative |100s,RK4 .02s|
| Magnetic levitation | Nonlinear inverse-square attraction and authored local voltage feedback |2s,RK4 .001s|
| Aircraft pitch | Longitudinal stability derivatives and pitch kinematics near trim |10s,RK4 .01s|
| Tethered kite | Coupled spherical steering and wind-dependent airspeed |120s,RK4 .05s|
| Tire-slip vehicle | Nonlinear tire slip/force, yaw and body-frame velocity coupling |12s,RK4 .005s|
| Battery thermal ECM | Charge depletion, RC polarization and cell/jig thermal coupling |600s,RK4 .5s|
| Compressor surge | Nonlinear pressure/plenum and flow instability near unstable operating point |60normalized time,RK4 .01|
| Bouc–Wen isolator | Internal hysteresis memory and dissipative structural restoring force |40s,Radau .02s output,rtol1e-8/atol1e-10|
| Crystallization moments | Seed growth, primary births and solute consumption with realizable moments |80normalized time,RK4 .02|
| Generator network | Three-node nonlinear sine-power transmission and rotor synchronization |40normalized time,RK4 .01|
| Semibatch polymerization | Conversion-dependent rates, mass accumulation, steel/jacket/external thermal loops |1h,Radau .002h output|

Independent tests compare every stock at every output against tight DOP853 integration. Explicit models also use half-step integration refinement; adaptive models use half output grid plus10times tighter tolerances. The Bouc–Wen derivative has absolute-value kinks: an affordable explicit grid showed about5e-6 scaled error, so its admitted default uses tested tighter adaptive integration rather than weakening a common3e-6 error criterion. All defaults and refinement runs stay within existing engine resource limits.

Additional independent checks include matrix exponentials for aircraft and battery; analytic battery charge depletion; exact MRAC Lyapunov identity; generator network internal-power cancellation and energy dissipation; Bouc–Wen storage/passivity identity; battery thermal balance; randomized kite steering geometry and polymer mass closure; crystal Hankel moment realizability, solute+solid conservation and independent birth-cohort characteristic integrals. Compressor equilibrium and unstable local eigenvalues, and levitation equilibrium/local stable poles, are independently rederived. No finite series alone is treated as scientific validation.

Reproduce: `.venv/bin/python -m pytest tests/test_library_candidates_third_engineering.py -q`. Numerical/source/inspection receipts: `.venv/bin/python operations/library-candidates-third-engineering/record_evidence.py`. Final numerical/admission run:17passed in18.88s; precise reference errors are retained in EVIDENCE.json. All candidate files require independent admission before counting.

Current numerical receipt has maximum scaled full-series reference error6.047e-7 (tire-slip vehicle); the other ten are below2e-7. Error scaling uses each stock's `max(1,max(abs(reference)))`. Ten models have complete consistent symbolic units. Aircraft stability-coefficient annotations remain incomplete, without dimensional errors. Normalized compressor, crystal and network units are explicitly dimensionless; these are not fabricated SI units. Physical temperature differences in battery are annotated with kelvin dimensions without claiming that25C equals25K as an absolute temperature.

Duplicate screening compares IDs, titles and direct equation fingerprints against every active and staged candidate file. A separate bounded static AST expansion substitutes parameter/auxiliary/flow DAGs into net stock derivatives, renames stock slots, folds finite constant arithmetic and canonicalizes commutative addition/multiplication. It also removes numeric coefficient values for a second structural comparison. DUPLICATE-SCREEN.json records1049active/staged source files,1047successful scalar expansions, two explicitly unexpanded cases and all matches; no exact or constant-abstracted match was found for these eleven. The refreshed receipt includes the active checkout after the approved second20 admission and all staged batches. Legacy flow endpoints are resolved through both stock IDs and stock names before derivative expansion. It does not prove equivalence under arbitrary state permutations, transcendental identities, initial-condition transformations or non-scalar flattening. Theme screening and peer review remain necessary.

Existing adaptive noise cancellation differs from model-reference state-gain adaptation; Whipple bicycle roll differs from tire-slip vehicle cornering; nonlinear VTOL flight differs from linear longitudinal pitch; the lumped grid frequency/governor model omits relative rotor phases and transmission topology; battery storage balances omit polarization and cell/jig heat; existing elastic oscillators lack Bouc–Wen internal memory; previous CSTR/batch chemistry lacks semibatch mass addition and polymer-dependent thermal loops. Science acquisition was coordinated to exclude its plasma/optics, friction, bubble, Akzo and phase-separation mechanisms.

Limits: local levitation feedback is not globally safe; kite excludes gravity/tether elasticity; vehicle retains source tire assumptions; battery freezes source dependencies and omits reversible heat; compressor is a surge subsystem without neural control or rotating-stall PDE; crystallization is an explicitly authored normalized isothermal scenario, not paper parameter reproduction; network is an authored topology, not a real grid; polymerization is a fixed-input source subsystem, not an industrial recipe/MPC trace. No production binding or new dependency was added.
