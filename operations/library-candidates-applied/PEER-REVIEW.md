# Independent applied-model admission review

Reviewed October 24, 2026. **Approve the ten exact candidate hashes below for admission as source-attributed mathematical/control teaching examples.** Approval preserves their stated scenario changes, unknown-unit disclosures, numerical grids, source attribution and limits. It does not certify calibrated hardware, physical safety, experimental data fidelity or an entire textbook figure reproduction.

Only this review document was written. No candidate, active library definition, retirement decision, user model or production file was modified.

## Primary-source authenticity and rights

I read all ten actual candidate definitions and the relevant equations in all retained primary files. Independently fetched each of the **13 source files plus LICENSE** from the author's repository at commit `dbbc2e1b4233dc148a3dc52c10d08e87881c1f15`; all 14 remote byte hashes match the retained local files. This checks authenticity against the pinned upstream, not merely consistency between a local source and local manifest.

The [pinned license](https://raw.githubusercontent.com/murrayrm/fbs2e-python/dbbc2e1b4233dc148a3dc52c10d08e87881c1f15/LICENSE) is BSD-3-Clause, copyright 2021 Richard Murray. The complete notice/disclaimer remains in sources/LICENSE alongside unchanged primary files. Source code redistribution is distinguished from rights to the textbook's prose, figures or layouts; no such materials are required by these candidates. No endorsement is inferred.

The equation sources are the pinned executable author examples. In particular, a source comment with a future date or inconsistent plot number is not being promoted to a bibliographic claim. The actual matrix/function and its pinned bytes are the evidence.

## Executed checks

Latest independent rerun:

```
.venv/bin/pytest -q tests/test_library_candidates_applied.py
18 passed in 25.05s
```

I also read MANIFEST.json, VALIDATION.json and docs/LIBRARY-CANDIDATES-APPLIED.md. The complete-state reference suite compares every retained default state against matrix powers, matrix exponentials, closed-form filters or separately handwritten DOP853 functions. Its largest recorded scaled discrepancy is 5.66026e-7, below the stated 2e-5 threshold. This threshold is an admission numerical error criterion, not biological/engineering calibration.

Additional independent probes, separate from the admission test module:

- **Bicycle:** re-derived all mass, gravity/stiffness and velocity-coupling matrices directly from the pinned bicycle.py numeric assignments using a restricted arithmetic AST reader. No imports, arbitrary statements, Python eval or source exec were run. Re-derived M, K0, K2 and C match the manifest to numerical roundoff; then constructed the first-order matrix at 7 m/s from the second-order equations. At 100 random states, engine derivatives differ from this matrix action by at most 7.82e-14. Its eigenvalues are approximately -0.475915, -1.234091±7.380451i and -16.020187, supporting the selected stable-speed scenario. Gravity is already present in K0; it was not multiplied a second time.
- **AFM:** independently reconstructed A, B and C from masses 0.15e-3/1e-3 kg and frequencies 40.9e3/41.6e3/120e3 Hz. At 20 random realization states, the scaled engine derivative difference is zero at printed precision. PiezoOutput matches the independently reconstructed C-vector output. No claim is made that all realization states are literal displacement coordinates.
- **Controlled pendulum:** at 100 random states, the exact identity dV/dt=-omega²*cos(theta)² for V=omega²/2+2*sin(theta)²+cos(theta)-1 agrees with actual engine derivatives within 2.78e-16. This is a local stabilization/dissipation lesson, not a global region-of-attraction claim.
- **Consensus:** the sum of derivatives at 100 random five-node states is at most 2.85e-14 in magnitude. The tested discrete map preserves the mean, contracts variance and matches exact matrix powers.
- **Cruise:** actual engine derivatives at the declared fixed-command initial equilibrium are approximately (1.23e-13,0). The controller realization produces the source transfer function (.5s+.1)/(s+.002). The small speed offset from 20 is consistent with the authored controller leak.
- **TCP:** independently solved the positive six-window equilibrium and recreated the original Python random.Random(6) perturbations. All declared initial states agree within 1.78e-15. The fixed model explicitly covers the first 500 ms, excluding the author's later change to four aggregates.
- **Air/fuel:** the candidate table contains the exact 101 author sample times and values. The .3-second sample grid and linear interpolation reproduce short ramps around the nominal reference steps; they are not falsely described as mathematically instantaneous jumps.

## Equation/scenario review

| Candidate | Result |
| --- | --- |
| sensor-consensus-five-node | Exact author Laplacian, gain and measurements. Its Euler/discrete-period declaration implements synchronous x[n+1]=(I-.1L)x[n]. This differs materially from active social two-fraction voter dynamics. |
| tcp-red-router | Correct six-window RED dynamics with N/M=10 in the shared queue rate and rho=.0002, capacity=10. Positive-queue default is tested; singular 1/Queue is preserved rather than clipped. It is not a generic M/M/1 queue or a full packet-level simulator. |
| ship-turning-path | Correct nonlinear sway/yaw force law plus the author's rotated position kinematics. Zero rudder and yaw=.1 scenario match one of the source trajectories. Nonlinear drag and spontaneous curved path distinguish it from fixed-speed point transport. |
| whipple-bicycle-stability | Pinned mass/geometry/inertia derivation and the matrix assembled from it are verified independently above. Stable speed 7 m/s, small initial roll and 10-second transient are explicitly chosen scenarios; the source example itself concerns stability/eigenvalues. |
| nonlinear-cruise-pi | Correct torque curve, mass/drag/rolling/gravity loads, throttle and torque saturation, leaky PI and 4-degree hill ramp. The initial operating point is explicitly recomputed for a fixed reference rather than quietly equating it to the source find_eqpt routine that may adjust the reference. |
| airfuel-cross-limit | Algebraic reduction yields air 4/(s²+8s+4) and oil 4/(s²+3s+4), matching the four output/output-rate states. MAX(Command,Fuel) and MIN(Command,Air) are the original cross-limit logic, not stabilizing modifications added after a failed run. |
| adaptive-noise-cancel | Plant, filter and gradient adaptation equations match the author code, including the demonstrated .01 adaptation setting. Deterministic two-tone input, zero desired signal and initial filter coefficient -.5 are explicitly our identification scenario; the source sampled unseeded white noise and nonzero desired signal are not claimed reproduced. |
| active-opamp-bandpass | A/B matrices and physical component values match the source. The selected zero-state unit step is an explicitly new transient test of the source frequency-domain circuit. Closed-form response confirms DC rejection and sign of the transient. |
| afm-piezo-modes | Modal state and output matrices match the author construction. The zero-state unit-step/300-microsecond transient is explicitly selected, not copied from a source frequency plot. Stiff modal magnitudes were not softened to make a run finish. |
| nonlinear-pendulum-feedback | Exact nonlinear force-feedback law with source gain 2. Illustrative .5-radian initial angle is explicit. The actual controller and Lyapunov lesson add content beyond the active passive single, coupled and double pendulums. |

I inspected the nearest active themes in the 923-model catalog: passive pendulums, passive RLC, social voter consensus, generic queue examples and grid-frequency controls. None implements these same mechanisms. ID/title/literal and canonical derivative fingerprint tests also pass; fingerprints are useful screens, not a mathematical proof that no algebraic equivalent exists anywhere.

## Units and resource boundaries

Four candidates report advisory dimensional consistency: normalized consensus, the SI-annotated cruise/controller model, active RC filter and normalized feedback pendulum. The other six report **incomplete**. Missing normalization/realization units remain visible; absence of a contradiction is not converted into a false dimensional pass. This is a retained limitation of their teaching/example status.

Every default remains within the existing element, interval, retained-value and work limits. Largest default interval count is 12,000, far below 100,000. Conservative all-element retained-value counts are at most 140,028, below one million. The current cruise trajectory reports **825,033 actual work units**, including **125,005 dependency retries**, under the one-million limit. It has limited refinement headroom: a finer requested grid may correctly fail, and this review does not authorize increasing budgets or silently shortening a horizon. Other default base-work estimates are at most 550,011.

Driven systems starting from zero have genuine changing trajectories and independent reference agreement. The existing all-stocks-zero advisory is retained rather than suppressed. Source-authored saturation/selection is distinguished from invented domain clamps; no unreported state reset or damping alteration was found.

## Exact admission approval

The hashes below match the frozen manifest. Preserve the source bundle, license, scenario descriptions and numerical settings when admitting. A changed candidate requires a fresh hash comparison. If the reviewed files are copied into the active catalog, staging duplicate assertions must be adjusted to recognize those intentional admitted copies rather than deleted or disabled globally.

| Candidate | Approved SHA-256 |
| --- | --- |
| sensor-consensus-five-node.json | `3ef61072ab7038b4b0e738e34661ca1b9b65faa5f84514ec492b682f53987285` |
| tcp-red-router.json | `4120299c8c5b464e447e96abf1d2d0ed0e89b0631447d2683610f33ca490fdf6` |
| ship-turning-path.json | `ccc74a62621d060388a6d58684d495d129142b80c5722933e842ec4507ce9f74` |
| whipple-bicycle-stability.json | `2249402002639df9a2fd41e04114655d103f44d3b2c5054fb22de8bc6d57bbf7` |
| nonlinear-cruise-pi.json | `d84f8a26ccd9d568f0b3d6ac6b729c7f7a6404bfdd7c9ff228293306135ca8dc` |
| airfuel-cross-limit.json | `e1428b02d15022bf2cdf520b177db20e0974b0b0f72af39fd7fc4e6c2d547652` |
| adaptive-noise-cancel.json | `63059fffe7d637267266946d71642255419bb8243ed92092a0013d07f6150b89` |
| active-opamp-bandpass.json | `968a906b64413f3a28df71e97efa07847cb61fd23e2dce84c2a9342c4e147915` |
| afm-piezo-modes.json | `18307e3c1504406322761f981645f1ff26f2e163edb68c332ba2e22c40d26233` |
| nonlinear-pendulum-feedback.json | `16805ee3e668ac2398aeae3d8afcb807a21eac4641221dc0f9b5ae79dd866322` |
