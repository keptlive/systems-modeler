# Independent review: fourth science candidates

2026-10-24. Reviewer ci_repair_resume, independent of author legacy_repair_resume. **Accept all three exact candidates as mathematically supported, distinct illustrative additions for a separately authorized future admission.** This review approves no active adoption, public copy, count change or deployment. Parameter choices are authored illustrations, not empirical calibration or reproductions of source experiments.

## Frozen package and decisions

Manifest SHA256 b7a8ab9a9ed413b45f27d19c695971569eebbe9a3b561a7f884e34a6ae9bf920 binds every source/evidence/test artifact. Independently verified all bound bytes and final candidate hashes:

| Candidate | Decision | SHA256 |
|---|---|---|
| Free Chaplygin sleigh: nonholonomic alignment | Accept | 11ecc9e03478a01f5e635a25d74025d3795f9ad45e76e39c50b2d6eb58c0b73e |
| Foucault pendulum: small-angle gyroscopic precession | Accept | d732b3244a66b361aae4c56ec121397314932f0cb1aa8de949b4a8054f3dd45b |
| Driven two-level atom: optical Bloch relaxation | Accept | 597cc3eb8b4bfb7745b1fb45fa65f91ca0c61ff3278b6cd84b83c30fd5686401 |

Requested and verified two metadata corrections before approval: all three now declare the seconds time unit, and the sleigh description qualifies default alignment and its zero/negative-offset exceptions. No numerical equation was changed by these corrections. All three independently return consistent symbolic units with no errors or unknowns; the checker retains its warning that scale/calibration/scientific validity is not established.

## Independent mathematical and numerical assessment

Independently reran the final authored suite: **19 passed in 4.05s**. Its analytic limits, conservation, matrix comparisons and refinement tests are stronger evidence than finite defaults; Euler finiteness alone is not invariant/positivity preservation. Separately executed 36 parameterized cases with seed2907 and156 full-series or positivity checks, all passed. These independently executed scratch checks changed no production or candidate files.

- **Sleigh:** independently integrated arbitrary initial speed/spin/heading with positive mass/inertia and signed offset using SciPy DOP853 at tight tolerances; all five candidate state series matched. The zero-force reduction of source eq2.1 yields u'=a*w^2, w'=-m*a*u*w/(J+m*a^2), heading'=w and the mass-center coordinate rates including offset terms. Differentiating the stated kinetic energy cancels exactly. Effective inertia must stay positive; zero offset is a spinning limit, not alignment. Negative offset changes the preferred speed sign. Ideal nonholonomic reaction does no work; no claim of frictional energy dissipation, general chaos or slip dynamics is warranted. The title accurately identifies the free special case rather than the source paper's forced potential variants.
- **Foucault:** compared all four states under random signed rotation, positive natural frequency and arbitrary initial displacement/velocity against an independent4x4 matrix exponential. The skew velocity coupling contributes zero power, so the displayed quadratic energy is conserved. The supplied complex solution, zero-rotation and rotation-reversal tests agree. This is the linear horizontal Coriolis approximation with an accelerated illustrative rotation; displacement must be small relative to a chosen length. The title/description do not imply a calibrated Earth-latitude apparatus. Omitted centrifugal/vertical terms and finite-step drift remain real limits.
- **Optical Bloch:** independently formed the full complex2x2 Lindblad generator as a4x4 superoperator, evolved random physical mixed initial density matrices and signed drive/detuning with nonnegative decay, and compared all three candidate component series. Reference eigenvalues remained nonnegative to numerical tolerance. This independently checks component signs/factors beyond merely repeating the authored real3x3 system. The basis, Hamiltonian, collapse operator and coherence convention are explicit; trace and Hermiticity are built into the representation. Physical initial-state constraints and Gamma>=0 are essential. The continuous law's positivity does not guarantee any arbitrary Euler/RK4 timestep preserves it. Rotating-wave/Markov assumptions and absence of extra dephasing/cavity/many-body effects are honest limitations.

## Primary sources and rights

Independently retrieved [Kuznetsov's primary paper](https://arxiv.org/pdf/1909.01130), checked basic equations2.1 and energy2.2, including the distinction between knife-edge speed and mass-center coordinates. The candidate is its free-force limit, not a reproduction of its potential-well experiments.

Independently retrieved [QuTiP's primary Lindblad documentation](https://qutip.readthedocs.io/en/stable/guide/dynamics/dynamics-master.html), equation3 and its approximation discussion. The candidate components follow by original matrix algebra with its explicitly declared H and collapse operator; no QuTiP runtime parity or source-code reuse is claimed. The source supports the generator, not a newly calibrated atom.

Manchester's direct author-page retrieval timed out twice in this review; its indexed primary result displayed the relevant coupled equations. Independently retrieved [UNSW's primary Foucault derivation](https://www.animations.physics.unsw.edu.au/jw/pendulumdetails.html), equations9.1*/9.2* and complex equation11, corroborating the candidate signs and factors. This alternate verification does not pretend successful full Manchester retrieval. The UNSW later approximation/typographical prose is not substituted for the exact candidate matrix solution.

The package contains original JSON, tests and short mathematical derivations, with source links rather than bundled publication pages, PDFs, figures or software implementations. No blanket license to the source publications is inferred from public access; this review asserts no new third-party redistribution rights or empirical/scientific certification.

## Duplicate screening and admission limits

Independently enumerated all993 Git-tracked model JSONs. Reproduced exact ordered file/id/SHA256 fingerprint785e21a28ec499dd161d509c80958f1d45d029b426ca7b6baea71d29f25dcc69 using the documented git order and compact sorted-key JSON. The named-concept metadata scan returned zero active matches. Inspected all eight closest active definitions' equations. Sleigh geometry/no-slip alignment differs from Euler rigid-body and driven ship dynamics; atomic density-matrix coherence/emission differs from Gilbert spin, Kerr field and laser carrier/photon models; restoring gyroscopic precession differs from free Lorentz motion or existing scalar/position-coupled pendula. Shared generic oscillator mathematics alone does not make these mechanisms duplicate user examples. Historical admission/curation indexes were identified in the dedupe artifact; this is a bounded baseline review, not proof against all conceivable equivalent representations.

Future admission must revalidate baseline hashes, preserve all993 existing definitions/private user data and source IDs, run scoped API/MCP/browser/default checks, archive an explicit admission manifest, and receive its own sanitized public/CI/staging review. No retirement aliases are needed for these new IDs. Accepting these candidates is not permission to force a count target or replace other examples.
