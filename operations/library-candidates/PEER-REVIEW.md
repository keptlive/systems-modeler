# Independent admission review: five mechanistic candidates

Reviewed October24,2026 against the candidate bytes below. **Approve these five for the parent's admission decision**, subject to retaining their source/license notices, normalized-benchmark labels, solver settings and tests. This review does not publish or move any model. The five short chaos/neuron transients in the same staging folder are outside this review and remain deferred. There is no numerical/scientific exemption for any admitted model.

## Reviewed bytes and decisions

| Candidate | SHA-256 of exact JSON | Decision and distinct contribution |
|---|---|---|
| `robertson-autocatalytic.json` | `9639c49fd98b1aa3b9577af83ae10750cc69d73b5613a736311d1f499c5da842` | Approve: stiff autocatalytic three-species benchmark with an independently conserved total, not the active reversible two-species reaction. Source rates(.04,3e7,1e4), state(1,0,0), horizon1e11 match. |
| `hires-photomorphogenesis.json` | `822a9a5da8208046f5992f0b3c8a931876d0468a10984e30ae4a0f3ba17e80eb` | Approve: eight-state HIRES reaction network, stateU1=1,U8=.0057, source twelve coefficients and horizon321.8122 match. Source term in U1 is a constant .0007. |
| `nonlinear-sequential-chemistry.json` | `d38fd06c87d26fc11088ba6b52839b1b21a9acefcff04b39aa267891e59c20e7` | Approve: first-order A→B followed by second-order B consumption, source state(1,0,0), horizon20. Different dynamics from reversible A↔B and enzyme binding; an independent Bessel-form reference is available. |
| `euler-rigid-body.json` | `1921866051bc025317ea17541b2290fdeaacd249fd62d610209292889631da60` | Approve as a normalized mathematical rotation benchmark. Effective coefficients(-2,1.25,-.5), source state(1,0,.9), horizon20 match. Coefficients must not be presented as moments of inertia or dimensional experimental parameters. Two quadratic invariants distinguish it from the retained translational/pendulum examples. |
| `pleiades-seven-body.json` | `d75229a34a6b9e40ac093d84dba07c82366e45b935edf168d1c4f1b90006cf57` | Approve: all seven planar masses interact and move, including fourteen integrated velocity coordinates; not the existing restricted three-body problem. Source mass factors1–7, all28 initials and horizon3 match. Unsoftened gravity is preserved. |

## Source and rights verification

The pinned [SciML executable source](https://github.com/SciML/DiffEqProblemLibrary.jl/blob/e5c3f5aff3b6921ca79b0862ebae896c7580666e/lib/ODEProblemLibrary/src/ode_simple_nonlinear_prob.jl), [sequential chemistry source](https://github.com/SciML/DiffEqProblemLibrary.jl/blob/e5c3f5aff3b6921ca79b0862ebae896c7580666e/lib/ODEProblemLibrary/src/nonlinchem.jl) and [MIT license](https://github.com/SciML/DiffEqProblemLibrary.jl/blob/e5c3f5aff3b6921ca79b0862ebae896c7580666e/LICENSE.md) were independently fetched during this review. Their bytes exactly match the retained files under `sources/`, not merely a prose citation. SHA-256:

- `ode_simple_nonlinear_prob.jl`: `6ebee1cc1b89def23a2076ad8721cfcf8d4db62a56f9d3e6684e0098f2f81eb3`
- `nonlinchem.jl`: `cfb81d7d4186293306786b5026716925f85286932afa0e2766f4f8d88d1fb5ab`
- `LICENSE.md`: `ff9cf8454bda41c2a8016f8c77d6f10fef943ea39a76901d9936159e587fd617`

The full ChrisRackauckas2016 copyright, permission conditions and disclaimer are retained. Upstream paper attributions remain secondary to this inspectable, licensed executable specification; this review does not claim access to every cited original paper. [Hairer's HIRES implementation](https://www.unige.ch/~hairer/testset/stiff/hires/equation.f) was separately read and confirms the constant source term. The upstream SciML docstring's extra U4 factor is a documentation error; the saved candidate follows executable code and Hairer's source. A Bari Pleiades PDF fetch timed out in this review; no independent inspection of that PDF is claimed here.

## Numerical and semantic checks performed

`python -m pytest -q tests/test_library_candidates.py` completed with **19 passed in19.97s** on this checkout. The full staging test file includes the five deferred transients, but passing those tests is not their admission decision. Reviewed tests compare all saved state series against independently handwritten derivatives using tighter BDF/DOP853 tolerances; they do not call the authored equation parser to generate reference derivatives. They also test the two chemistry totals, HIRES U7+U8=.0057, rigid-body quadratic invariants, the chemistry Bessel formula, Pleiades linear momentum/barycenter motion and fixed-step convergence. Those checks are materially stronger than finite output alone.

Additional read-only spotchecks performed for this peer review:

- At ten deterministic noninitial random states per candidate, the canonical evaluator's assembled stock rates agreed with independent numeric equations. Maximum relative-scaled discrepancies were ≤2.19e-16; no omitted velocity integration, wrong force direction, source multiplier or flow sign was found.
- Robertson was rerun on0–.1 with saved step1e-4 and tighter Radau settings to inspect the fast transient hidden by its long default output grid. Every saved state agreed with tight independent BDF within4.19e-13 absolute; intermediate species peak was approximately3.64872e-5. The default uniform grid's omission of this transient is prominently disclosed and is not evidence that the transient is absent.
- For Pleiades, independent total-energy drift over the default run was approximately3.83e-6 and angular-momentum drift1.01e-7. Closest separation among saved states was approximately.03454; this does not bound between-output closest approaches. Existing momentum and barycenter tests also pass. No softening or collision clamp was introduced.
- Native dimensional analysis returned `consistent` for all five under their explicitly normalized, dimensionless coordinate/time declarations. This verifies the declared mathematical convention, not recovered physical units or experimental calibration.

The active923 inventory, relevant physics/chemistry definitions and conservative duplicate-fingerprint tests were inspected. No semantic duplicate of these five was identified. In particular, the active reversible A/B reaction, full Michaelis–Menten binding, Brusselator/Oregonator, pendula/springs and restricted-three-body definitions are different mechanisms. Fingerprints alone do not prove algebraic inequivalence; this conclusion also uses the source equations and state interpretations.

## Resource and scientific limits

Observed default simulations in the additional peer run took approximately.20s Robertson,.18s HIRES,.05s chemistry,.14s rigid body and6.30s Pleiades on this host. These are observations, not performance guarantees. Adaptive diagnostics charged32,373 equation-work units for Robertson,49,792 for HIRES and731,248 for Pleiades, each below the explicit1,000,000-unit engine budget. Pleiades has the narrowest margin; changing its tolerances, state, output grid or horizon can legitimately hit the budget and must return the existing capacity diagnostic rather than gain an exemption. Fixed-step examples remain within the existing bounded grids and show refinement agreement.

The labels correctly describe normalized mathematical benchmarks and explicitly disavow calibration/forecast validity. Signed rotational/position/velocity coordinates are valid; they should not receive positivity clamps. Reaction positivity and invariant checks are useful mathematical evidence but do not turn these source test problems into biological or chemical predictions. The Robertson output grid is appropriate only with adaptive internal integration; interpreting its saved dt1e9 as a stable Euler step would be wrong. Pleiades is a nonstiff physical equation set solved here by adaptive Radau for practical error/work control, not because its source is claimed to be stiff.

Approval is specific to the reviewed hashes. Recheck source equivalence and numerical evidence after material equation, parameter, initializer, solver or horizon changes. No candidate JSON, test, active library file, engine or production state was edited during this peer review.
