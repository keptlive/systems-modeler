# Independent review: third science candidates

Reviewed October24,2026. **Approve all11 exact candidate files below for admission as the explicitly scoped educational/numerical examples presented.** No unresolved blocker was found. This review does not authorize admission/deployment; no active definitions or candidate bytes were changed. Only this peer-review document was written.

## Independent verification

Final frozen suite:

```
.venv/bin/pytest -q tests/test_library_candidates_third_science.py
35 passed in 13.19s
```

I inspected the handwritten reference equations against the candidate expressions and source formulations. Every retained state sample is compared independently: DOP853 for10 systems and BDF for the Akzo Radau example. Nine explicit systems pass coarse-grid refinement; both adaptive systems improve with tighter tolerances. Input inspection and consistent symbolic unit reports pass all11. Analytic/invariant checks are material independent evidence, not just successful finite output.

Separately sampled100 states per model, using domain-respecting radii, positive contact ages, positive Akzo square-root arguments, signed composition and normalized spin vectors. Native saved equations were evaluated and stock derivatives reconstructed from actual endpoint links. Across1100 sampled states, the largest max(1,|actual|,|reference|)-normalized derivative discrepancy was7.50e-15 in the pressure-cancellation-sensitive bubble acceleration; others were at most2.56e-16. Additional instantaneous balance residuals: Chapman oxygen atoms6.94e-18; spin length derivative1.08e-16; Cahn-Hilliard mean2.23e-16; piston total-energy rate8.11e-13 SI; laser pump/quanta rate2.28e-13. These are floating-point residuals, not calibrated physical error bars.

Key independent checks reviewed:

- Bubble: reference radius balances ambient and Laplace pressure; polytropic gas energy, radial-fluid kinetic energy, surface/ambient work and accumulated viscous loss balance. The default is a small positive-radius oscillation, not a violent-collapse calculation.
- Polytrope: centre-series coefficients through sixth order satisfy the regular expansion; exact n0 and n1 controls and the n3 surface/mass constants are checked. The horizontal coordinate is dimensionless radius, explicitly not time.
- Chapman: each of the four reactions preserves oxygen atoms; the independent stationary-state algebra and final approach are checked. Fixed illumination and effective normalized rates preclude a quantitative atmospheric forecast.
- Spin: closed-form precession/relaxation, unit-length preservation and decreasing magnetic energy check the Gilbert factor and sign.
- Lorentz: closed-form crossed-field velocities/positions and kinetic-energy/electric-work identity check charge sign, gyromotion and perpendicular drift; parallel motion remains free.
- Kerr: independently derived cubic stationary intensities and trace/determinant show two stable branches and a middle saddle; simulations initialized near both stable branches approach them.
- Friction: differentiating the logarithmic friction law reproduces quasistatic spring loading; the aging law gives the stated steady point and exact stiffness stability boundary. Positive speed is represented logarithmically; no stick/reversal/inertia claims.
- Piston: pressure-volume adiabat and full energy including external damper heat are conserved. Dissipation is explicitly outside the gas and not silently returned to it.
- Akzo: algebraic y6=Ks*y1*y4 is uniquely substituted, not integrated. All five original differential expressions and square-root domain remain intact; the published180-minute endpoint and an independent BDF trajectory agree. This does not demonstrate a general DAE solver.
- Phase-field ring: periodic Laplacians preserve mean; the discrete free-energy derivative equals minus the sum of chemical-potential edge differences squared. Linear spinodal growth and nonlinear energy decrease supplement solver agreement.
- Laser: explicit carrier/photon transfer and loss-accounting state preserve total supplied quanta; a separately solved threshold/stationary solution and turn-on overshoot are checked. Normalized parameters are illustrative.

Every numerical evidence SHA-256 independently matches its candidate file. The source defaults/adaptations in manifest.json and descriptions agree with the equations. No positivity clamp, hidden random input or reset was found. Settings beyond reviewed domains require another error/work audit.

## Primary-source access and rights

Independently read relevant sections/equations from [Brennen Chapter2](https://media.library.caltech.edu/CaltechBOOK:1995.001/chap2.htm), [NIST OOMMF guide](https://math.nist.gov/oommf/doc/userguide12b4/userguide.pdf), [Godey et al Eq4](https://bpb-us-e1.wpmucdn.com/blog.umd.edu/dist/3/661/files/2019/07/2014_PRA_Stability_Analysis_LLE.pdf), [FEniCS governing equations](https://docs.fenicsproject.org/dolfinx/main/python/demos/demo_cahn-hilliard.html), [PhotonForge carrier/photon equations](https://docs.flexcompute.com/projects/photonforge/en/latest/guides/Directly_Modulated_Laser.html), [OpenStax adiabatic closure](https://openstax.org/books/university-physics-volume-2/pages/3-6-adiabatic-processes-for-an-ideal-gas), the [NASA1978 report AppendixD](https://ntrs.nasa.gov/api/citations/19810008106/downloads/19810008106.pdf), and [Washington polytrope derivation Eqs62–63](https://archive.int.washington.edu/PHYS554/2011/chapter4_11.pdf). The last also explicitly supplies n3 surface6.89685 and mass2.01824.

The homogeneous Kerr specialization correctly omits the spatial derivative; the finite phase-field ring is original spatial discretization, not copied FEniCS code. Spin damping uses the documented Gilbert/Landau-Lifshitz conversion. Laser coefficients specialize the density equations with confinement1/no compression; its cumulative loss variable is original accounting. OpenStax-derived laws are attributed to Ling/Sanny/Moebs, Rice University, CC BY4.0; NASA provenance is retained. No third-party implementation, article prose, figures, PDF or XML is included.

Direct Akzo host requests timed out or failed routing. Primary indexed [CWI Chemical Akzo report](https://archimede.uniba.it/~testset/report/chemakzo.pdf) text independently exposed the full differential/algebraic equations, rates18.7/.58/.09/.42, K34.4, Ks115.83, transfer3.3 and reservoir.9/737; indexed [full report endpoint table](https://archimede.uniba.it/~testset/report/testset.pdf) corroborated the180-minute reference. I do not claim a fully retrieved PDF. Original rate-state articles/Pipping fulltext were not completely retrievable in this review; the indexed primary repository record and cited aging-law source are attributed, and I independently derived the admitted log-speed equations/stability algebra. This is an explicitly illustrative positive-sliding closure, not a reproduced fault experiment. Other illustrative closures/defaults are likewise plainly separated from claimed source values.

These mathematical transcriptions/adaptations and reference implementations are original. Public source access is not asserted to grant general reproduction rights to publisher/university text. Existing rights notes are appropriate to the actually redistributed material.

## Distinctness and usefulness

Executed identity/title/literal-equation and expanded alpha-normalized stock-derivative checks scan the active catalog and every other staged batch, including the second20 and third engineering definitions. No matches were found. Mechanism inspection supplements these conservative screens; they are not a theorem against all reparameterizations/state reorderings.

The conserved Cahn-Hilliard transport mechanism differs from active nonconserved Allen-Cahn relaxation; continuous contact-age friction differs from threshold elastic rebound. The piston couples adiabatic thermodynamics to mechanics beyond generic spring variants. The charged-particle state includes gyromotion/electric work, not a renamed Coriolis/Ekman example. Chapman reactions differ from generic urban ozone effects. Driven complex Kerr phase response differs from scalar Schloegl chemistry. The bubble, polytrope, magnetic moment, exact eliminated stiff chemical benchmark and carrier/photon laser each expose useful, source-grounded mechanisms not duplicated in inspected active/staged equations. None is a renamed retired stub.

## Exact approved candidate bytes

| File | SHA-256 |
| --- | --- |
| adiabatic-gas-piston-third-science.json | `8585e40aab94989ab109683abf03b6555cd26eae7478cafef33d51f18373af92` |
| akzo-nobel-eliminated-constraint-third-science.json | `5f7ff0b7bb22401cf9d0092a3dfdc026c42a4c9674cf8f3bc95eff35c8dea677` |
| cahn-hilliard-periodic-ring-third-science.json | `b1165562f373788876dcf3e2a53c2ca86d3c61215f49f3a1d0db0b75303929af` |
| chapman-oxygen-photochemistry-third-science.json | `ef3ac99de50bfd70d0c760ca4a660dc3f5544c014cd4926bcec8abf05d69bb82` |
| gilbert-single-spin-third-science.json | `5ab430725fbd901b2852959948931af5e2196209e926bbaba4e6ddbdbbb67050` |
| kerr-cavity-quadratures-third-science.json | `5cc0e4d4d9b6f073ca596fe07cf024f3cc0c7129679fd9babe01c57a38fd962e` |
| lane-emden-polytrope-third-science.json | `063aab2b6ffd802dc2aa3b365d683e20f462c79116ee4db5e47e994124fa8ca9` |
| lorentz-crossed-fields-third-science.json | `39a39059f488210f1c0a0d1a3723aa428a78cdc7dfae80e8c81ea483b9cad903` |
| rate-state-stable-sliding-third-science.json | `2217f18f5dd16896d6a7b448d06f018cdacda8d51ed0fd2ae5963430a6235b6e` |
| rayleigh-plesset-bubble-third-science.json | `664ad68a5864b197aec309f541b5679e604e085e607996661039cd9b8e04ca55` |
| semiconductor-laser-turn-on-third-science.json | `1f7d5d9ca3ca56e45371b7f60a04cc21f58d9d9d87dea4f338a86f753841d37c` |

Approval applies to these bytes and their documented defaults/scope, not arbitrary parameter extensions or claims of physical calibration. Substantive edits require a new comparison.
