# Independent review: second biology batch

Reviewed October 24, 2026. **Approve the ten exact candidate files below as attributed educational mathematical examples with their explicit adaptation boundaries.** This is scientific/numerical admission review, not authorization to publish or change active models. No unresolved blocker was found. Only this peer-review document was written.

## Numerical verification

Independently ran:

```
.venv/bin/pytest -q tests/test_library_candidates_second_biology.py
26 passed in 16.84s
```

The suite compares every retained state sample with handwritten numeric references: LSODA for Tyson/Vilar, DOP853 otherwise, plus a matrix exponential for reversible persistence. I inspected those references against the saved equations rather than accepting a successful test count alone. Source values and explicitly illustrative defaults are distinguished in descriptions/manifest. All ten default unit reports are consistent. Every state varies, output is finite and nonnegative within numerical tolerance, and default requests stay within unchanged work bounds.

Additional independent probes evaluated saved native equations at 100 seeded random positive states per model, reconstructed each stock derivative from declared flow endpoints, and compared against the handwritten right-hand sides. Across 1,000 states, maximum max(1,|actual|,|reference|)-normalized discrepancy was 2.22e-16. Independent random-state pool checks gave maximum absolute residuals: Tyson cdc2 4.18e-16; both Vilar promoter pools exactly zero; Becker-Doering weighted monomer mass 3.55e-15; competitive enzyme three moieties 2.23e-16; Frank monomer equivalents 1.91e-17. This supplements trajectory comparison with off-trajectory stoichiometry checks.

I checked the relevant algebra: Becker-Doering dimer formation consumes two monomers and the finite last cluster has no outgoing sink; enzyme binding retains enzyme/substrate/inhibitor pools separately; Frank inactive pairs carry two monomer equivalents. Schloegl's derivative has two stable roots separated by an unstable one. Chemotaxis's stationary activity is 1/3 for the chosen methylation feedback, with a ligand-dependent methylation equilibrium. Exact symmetry remains symmetric in the deterministic chiral system. Persistence is the two-mode linear matrix, not genetic resistance or stochastic survival.

Adaptive costs in the bound evidence remain material: Tyson325542, Vilar826056, immune451537 work units. Extending Vilar's horizon/tightening tolerances can exhaust the existing budget. Long tiny immune tails require the documented strict absolute tolerances; agreement here is not evidence for calibrated population predictions. No hidden clamps/resets or removed dynamic source terms were found; the explicitly stated zero-term specializations are algebraic.

## Primary-source and default checks

- Independently fetched and parsed the complete [pinned Tyson CellML revision](https://models.physiomeproject.org/workspace/tyson_1991/rawfile/882447deebe540870a53c5971525d12208fca27b/tyson_1991.cellml). Six initial concentrations0.001, source coefficients, CT dependence, preMPF activation and cdc2 conservation match. Source-zero k2/k5 terms are removed exactly.
- Independently fetched and parsed the complete [Li-Rinzel CellML exposure](https://models.cellml.org/exposure/be7a891ac95b45c9b651f88821b6d2b4/li_rinzel_1994.cellml). Initial C=.2,h=.8 and retained rates match. The source uses millisecond0.001 factors; their removal consistently changes rates to seconds. Setting epsilon=0 removes plasma flux and makes c0 constant. The candidate does not claim the source's epsilon=.01 case.
- Read Eq1 and Fig1 caption in the [original Vilar paper](https://computableplant.ics.uci.edu/emj/classes/277C_04/papers/networks/villar_barkai.pdf). All15 rate defaults and promoter-only initial occupancy match; complex loss releases repressor, which is explicitly retained. Deterministic cycles alone do not establish the paper's stochastic noise-resistance result.
- Read Eq1–3/Table1 in the [author-hosted Kussell paper](https://kishony.technion.ac.il/wp-content/uploads/sites/403/2025/07/Kussell_2005.pdf). Antibiotic wild-type growth/decay and reversible-switch rates match; normalized starting proportions are illustrative.
- Independently retrieved the [Vellela–Qian primary article](https://pmc.ncbi.nlm.nih.gov/articles/PMC2838355/?pdf=render) via urllib after browser challenges. Fig1's bistable reservoir/rate defaults match the saved cubic. Stochastic switching is explicitly excluded.
- Read the [Tu–Shimizu–Berg primary article](https://pmc.ncbi.nlm.nih.gov/articles/PMC2551628/): MWC free-energy contributions, activity-dependent methylation, monotone feedback and ligand-independent adaptation support the candidate mechanism. Its linear feedback and affinity defaults are explicitly illustrative, not that paper's fitted Tar parameters.
- Checked the [UNT/NACA translation record](https://digital.library.unt.edu/ark:/67531/metadc62899/) for Becker/Doering. The finite five-size closed truncation and rates are our explicit adaptation, not a reproduced supersaturated-vapor calibration.
- The [NASA investigators' research account](https://astrobiology.nasa.gov/nai/annual-reports/2015/uiuc/project-1-the-origin-of-homochirality/index.html) supports autocatalysis and mutual antagonism as the Frank framework. It also discusses materially different stochastic mechanisms. The candidate plainly identifies its finite-precursor inactive-pair system as an adaptation; it does not reproduce NASA's reaction closure or claim spontaneous deterministic symmetry breaking.
- The [competitive-inhibition publisher record](https://doi.org/10.1080/25765299.2020.1844369) was indexed, but full publisher access returned403 in this review. I independently derived the six-species ordinary competitive-binding mass-action equations and three moieties; all numerical defaults are illustrative. I do not certify a full original-paper read or its slow/fast reduction analysis.
- Direct retrieval of the [original immune author-hosted PDF](https://main.kirschnerlab.med.umich.edu/lab/pubs/80370235.pdf) failed certificate/timeout checks. The indexed later author-hosted [Kirschner-Panetta formulation](https://malthus.micro.med.umich.edu/lab/pubs/Tsygvintsev_et_al.2012.nf.pdf) exposes the same unscaled three ODEs. I checked recruitment, logistic tumor growth, saturating killing/IL2 production and source-zero specialization algebraically. All parameters are explicitly illustrative; no original calibration or clinical result is certified.

These access limitations are compatible with approval as the candidly labeled educational adaptations presented. They must not be rewritten as reproduced original experiments.

## Distinctness, rights and quality

The executed inventory/fingerprint checks screen the active958 definitions and all other JSON model definitions under operations, including the concurrent second-applied batch, for identities/names, literal flow equations and conservative expanded alpha-normalized stock derivatives. No collisions were found. These checks are supplemented by mechanism inspection; they are not a general algebraic-equivalence theorem.

Tyson retains phosphorylation/binding and a conserved cdc2 pool beyond the active Goldbeter activity cascade. Vilar retains promoter occupancies and sequestration beyond the repressilator/Hill clocks. The calcium store/receptor state pair, finite cluster chain, three competitive-inhibitor moieties, reversible persister modes, chirality competition and receptor adaptation each expose useful different mechanisms. The immune effector–tumor–cytokine network differs from the active Gompertz/drug-resistance models. A staged generic toggle was rightly omitted. Existing generic cell-cycle titles do not contain these same six-state/source equations. No renamed retired stub or padding-only duplicate was identified.

Definitions/prose/reference implementations are original mathematical transcriptions/adaptations. No source PDF, XML, paper prose, figures or third-party program is redistributed in this batch; citations do not grant blanket licenses to those materials. Candidate license notes accurately state this boundary. This review does not assert that all cited articles are open source. No active-library changes or production actions occurred.

## Exact approved bytes

All ten SHA-256 values independently match evidence/validation.json.

| Candidate file | SHA-256 |
| --- | --- |
| bacterial-persister-challenge-second-biology.json | `602ab953e9b66f8c32ea165035a9f7f6e7f0f3b2845a0731250c9e9fda04a76d` |
| becker-doring-five-clusters-second-biology.json | `0d5258e7283e1625136f295b0f2e58107f3e108b5759de2f4a46f5b5db6facf7` |
| chemotaxis-integral-adaptation-second-biology.json | `2f4859818df2787051b0e255293dcaa27ea0e7ec78ac596e1117b4ac56087781` |
| competitive-enzyme-moieties-second-biology.json | `939448f6f24f33cdb15f13095572521e2a3698f0254598904f84af7e2b56365c` |
| frank-closed-chiral-selection-second-biology.json | `1fa7b584e6bba54bc0d3f4ee4ff7cbd6b945da986826f8ab73a79ad11f44ee7a` |
| kirschner-panetta-immune-second-biology.json | `a7dc14e42aad7f4b6e4f7d4312bf37813bd0839a0ae42b5843237200c5b0d2b9` |
| li-rinzel-closed-calcium-second-biology.json | `fc9164107964a141526d5385f9cf33e5a2be010fc3569c1e538f395945595c21` |
| schlogl-bistable-chemistry-second-biology.json | `66d9e037c3c7fa22392c6f71ecad3fc5954a3c4cc872c726c88151c9fa36c9c9` |
| tyson-cdc2-six-state-second-biology.json | `fb3aabd5384c079714792c0d69c0dbb13553c9d2deaae031e0a889f5e9fb84ce` |
| vilar-sequestration-oscillator-second-biology.json | `dc01c97e3bd69011f1748a2dc5bdea0a98b374fc9319b57625269239ca9c5a09` |

Approval is limited to these bytes, documented defaults and stated source/adaptation boundaries. Substantive edits require a new comparison.
