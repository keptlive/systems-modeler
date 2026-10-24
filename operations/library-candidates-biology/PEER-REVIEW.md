# Independent biology admission review

Reviewed October 24, 2026. **Approve the ten exact hashes below for admission as illustrative mathematical teaching examples.** This is not approval as calibrated biological forecasts, experimental reproductions, or complete spatial/biochemical models. Candidate files were not edited. Only this peer-review document was written.

## Scope and independent evidence

I read all ten actual JSON definitions, their descriptions, units, initial states, parameters, equations, solver settings and endpoint wiring; the manifest, PINTS notice, validation evidence, candidate tests and accompanying documentation. I independently inspected the active 923-file inventory, relevant active mechanisms and the retirement archive rather than accepting filenames as evidence of novelty.

Re-ran `pytest -q tests/test_library_candidates_biology.py`: **29 passed in 6.69 seconds**. The tests cover complete retained-time comparisons with independent DOP853 right-hand sides for the eight ODEs, exact recurrences for the two discrete examples, refinement, positivity, steady states and invariant domains. I verified that the evidence manifest's ten SHA-256 values match the actual candidate bytes.

Additional read-only probes, separate from that test module:

- No candidate ID collides with any of the 923 active IDs. All ten IDs are distinct.
- Each signed net derivative is connected only to its declared corresponding stock. No MIN/MAX/IF/random/clamp calls or zero-flow placeholders occur in the derivative equations. The representation is explicitly described as net derivatives, not physical species-to-species transport.
- At 100 independently sampled positive Droop states, the engine-derived inventory derivative dS/dt + X dQ/dt + Q dX/dt was at most 7.11e-15 in magnitude. This checks the actual transcribed equations rather than only the final trajectory.
- The covalent switch points inward at both fraction boundaries: f(0)=0.09900990099 and f(1)=-0.08910891089.
- Independent analytic Jacobians at the declared stationary states have eigenvalues -0.5±1.32287566i for Gierer–Meinhardt, -0.1±0.88881944i for Selkov, and -0.1±0.99498744i for Schnakenberg. Actual engine derivative values at those stationary states are zero.
- The first Leslie census is exactly (56,50,28), independently calculated from the stated age matrix. The first Nicholson–Bailey generation is (139.04388506159466,70.47805746920267), independently calculated from the escape probability exp(-0.7).

These probes establish internal mathematical/numerical consistency for the represented models; they do not validate the biological assumptions.

## Source and parameter assessment

| Candidate | Assessment |
| --- | --- |
| Goodwin | Exact three-equation repression form, hard-coded initial state, suggested coefficients and 0–100 horizon checked directly in the [PINTS model documentation](https://pints.readthedocs.io/en/stable/toy/goodwin_oscillator_model.html) and [published source](https://pints.readthedocs.io/en/stable/_modules/pints/toy/_goodwin_oscillator_model.html). The finer RK4 step is correctly identified as our verification choice. The benchmark is distinguished from a calibrated biological clock. |
| Repressilator | Six RNA/protein states and a three-repressor ring, with coefficients and asymmetric initial state explicitly illustrative. [Original publisher record](https://www.nature.com/articles/35002125) and the [BioModels source-derived record](https://www.ebi.ac.uk/biomodels/services/download/get-files/MODEL6615351360/3/BIOMD0000000012.pdf) establish lineage and distinguish dimensionless equations from dimensional Figure 1C reconstruction. Full Box 1/PDF access was blocked in this review session; I do not certify an experimental figure reproduction. The candidate makes no such claim. |
| Selkov | Equations independently matched to [Brechmann–Rendall equations 9–10](https://link.springer.com/article/10.1007/s00285-021-01560-y), including gamma=2, alpha=0.8 and the stable (1,1) regime. Correctly identifies its basic limiting model, not the five-species derivation. No claim of a limit cycle at this default. |
| Gierer–Meinhardt | The reaction terms agree with the minimal activator/inhibitor special case of the [original paper's 15a–15b](https://www.phys.ens.psl.eu/~hakim/BIBLIOM2ICFPCOURS/gierermeinhardt72kib.pdf), with diffusion removed, constant source distributions absorbed into coefficients and zero basal activator production. Parameters are illustrative; no tissue geometry or spatial pattern is claimed. An optional documentation improvement is to name the zero basal-production specialization explicitly. |
| Droop | Coherent single-nutrient closed-batch quota balance with uptake and growth decoupled. [Droop 1968](https://doi.org/10.1017/S0025315400019238) and [1974](https://doi.org/10.1017/S002531540005760X) citations are correctly identified. Primary full-text access was not obtained here; this approval covers the explicitly specialized illustrative balance, not a full reconstruction of the two-nutrient chemostat/luxury-uptake experiment. The documentation states that omitted regulation boundary. |
| Goldbeter mitotic cascade | Independently retrieved the actual [Physiome CellML exposure](https://models.physiomeproject.org/e/4c/goldbeter_annotated_1991.cellml) with urllib when browser retrieval failed. Parsed its three initial states (.01) and all coefficients: vi=.025, vd=.25, kd=.01, Kd=.02, Kc=.5, K1–K4=.005, V2=1.5, V4=.5, VM1=3, VM3=1. These match the candidate, including combining four equal saturation parameters. The stated horizon/output spacing/tolerances are our choices. Original DOI [10.1073/pnas.88.20.9107](https://doi.org/10.1073/pnas.88.20.9107) is the appropriate cascade lineage. |
| Leslie | Actual age-census map, not an ODE approximation masquerading as demography. [Original Leslie paper](https://jxshix.people.wm.edu/2009-harbin-course/classic/leslie.pdf) and [publisher record](https://doi.org/10.1093/biomet/33.3.183) support matrix age projection. Every numerical fecundity/survival/initial count is explicitly illustrative. The discrete-period contract prevents arbitrary solver/timestep reinterpretation. |
| Nicholson–Bailey | Correct random-search map, one offspring per parasitized host, unstable coexistence at the chosen multiplication factor. [Original publisher record](https://doi.org/10.1111/j.1096-3642.1935.tb01680.x) verifies citation; original full-text equations were not available in this session. Numerical values are explicitly illustrative and the recurrence is independently checked, not claimed as an original empirical table. |
| Goldbeter–Koshland | Correct opposing saturated forward/reverse reduced cycle and fraction boundary behavior. [Original paper record](https://doi.org/10.1073/pnas.78.11.6840) is the appropriate source lineage; full original text was inaccessible here. All numerical defaults are illustrative and quasi-steady enzyme kinetics is disclosed. The admission claim is the explicit reduced mathematical switch, not full enzyme-complex dynamics. |
| Schnakenberg | Correct standard well-mixed activator/substrate autocatalytic core. The [original paper](https://www.math.us.edu.pl/mtyran/dydaktyka/biomatematyka/schnakenberg_1979.pdf) was available in search-indexed primary text, while direct PDF fetching timed out. Numerical defaults are illustrative; no Turing/spatial or oscillatory-default claim is made. Its stable stationary point and reaction balance were checked independently. |

Source-access limitations are recorded deliberately: a DOI resolving to a correct title is not evidence that every page was read. Exact source-based numerical claims are strongest for PINTS Goodwin and the independently retrieved Goldbeter exposure. The other defaults are appropriately labeled illustrative. No parameter was silently promoted to an experimentally established value during this review.

## Distinctness and retirement boundary

The active Brusselator contains a B*X source into its second species; the proposed Schnakenberg instead has constant substrate feed and a different reaction network. The active circadian example has saturating mRNA/protein degradation and nuclear transport, unlike linear three-stage Goodwin turnover. The active toggle is a two-repressor transcriptional switch, unlike the six-state cyclic repressilator and the single covalent-modification fraction. The active Michaelis–Menten example represents explicit binding/complex/catalysis, unlike the reduced opposing-enzyme switch. The active Monod example couples growth directly to external substrate and dilution, unlike the internal-quota batch example.

The retired Goodwin, Droop, Gierer–Meinhardt, repressilator and glycolytic files inspected each have zero flows. They remain retired evidence. These candidates use new IDs, explicit dynamics and independent references; this approval does not authorize reactivating those old files. The retired Leslie concept also does not replace the actual discrete recurrence here.

## Rights and admission boundary

The saved descriptions and mathematical transcriptions do not redistribute article text, figures, page layouts, downloaded CellML or a third-party implementation. PINTS attribution and BSD-3-Clause notice are retained in NOTICE-PINTS.txt; the source documentation itself confirms that license. The Selkov article is explicitly cited with its CC BY 4.0 status. Formula lineage and numerical facts are distinguished from rights to copy a paper or model file. No permission to redistribute the consulted Physiome XML is inferred.

Approve the exact candidates below for illustrative library admission, preserving all descriptions, source links, parameter provenance, solver settings and discrete-period contracts. A changed candidate hash requires a new comparison; a numerical run alone does not extend this approval. No deployment, library write, retirement reversal or user-model replacement was performed in this review.

| Candidate | Approved SHA-256 |
| --- | --- |
| droop-batch-quota-biology.json | `4c66175aba579fe1eb53c3e9f1f889ff98fdd54d6e9ba55cd24985d08b6b3d3d` |
| gierer-meinhardt-well-mixed-biology.json | `ff2b9cb92fffba9a157a925c6f2f6414694c84d931ae25d7c41c57be568b389a` |
| goldbeter-koshland-dynamic-switch-biology.json | `aaf01d69f00177ac13a55b85ce264594753aa650d46b0f172d13d77c1c8adc96` |
| goldbeter-mitotic-cascade-biology.json | `a26eec28f4abc51daf760a6fa59c8bb4ce85046f7029569712536f2d48f3bcd3` |
| goodwin-feedback-oscillator-biology.json | `4d72cab1a435d1c8fb102a7347889703d80c85a5b0f64303fbfa558393ab87ed` |
| leslie-three-age-classes-biology.json | `8b511b2824e712f83782465c313532d52bb13208703ef8cc8f7fbec760ff82e7` |
| nicholson-bailey-parasitoids-biology.json | `652a9e8508bcb3c07fa81ac49681cfb268018e0c9a9b862a2b7b81cbb303e435` |
| repressilator-six-state-biology.json | `294be11c609ea96a6f39c91b76556335c0d1aad3a7da8caca7241cec9cfb8cde` |
| schnakenberg-well-mixed-biology.json | `a1828a13b607f39c706613b40134e0e01d0ddd27e4635a672b29ff958922b02f` |
| selkov-basic-glycolysis-biology.json | `d428bb9a8ec2b9ac2091d13902f1122226933164ce3d82c710ca4d0987f21793` |
