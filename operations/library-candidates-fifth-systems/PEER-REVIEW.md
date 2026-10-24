# Independent review: accepted as isolated illustrative candidates

Reviewed 2026-10-24. Approval is for the exact two candidates as useful future admissions, not active adoption, calibration, publication or deployment.

Manifest SHA256 023709e7e8a70d1b4daedeede9332551c87bfd16f3c4030a74783337f53dcdd2; all nine bound assets verified unchanged.
Holt model 7866c48ce562e80c6335d4f6e796e00c3b6e88656713deef3d009d781cddc6c6.
Adsorption model f27abdf55694a3794f67f93bb133dcad3575cba1456a1eb03819a3c9dfa8fa9b.

Independently opened the author-hosted Holt PDF, visually inspected printed page204 equations8-9, and compared all terms. The predator conversion factor multiplies both recruitment and maintenance exactly as the source requires. Logistic prey have separate capacities and shared predator; normalized densities/defaults are original choices, not fitted data. Zero conversion freezes predator, as documented.

Independently reopened all three official CADET v5.1.1 pages listed in SOURCE-EVIDENCE. q*-based LDF is distinct from native kinetic Langmuir and liquid-phase LDF. The single-component equilibrium loading and constant-volume mixed-tank mass budget match the candidate. Three cells are an authored network, not a CADET or plug-flow replication. Signed reversible uptake correctly supports desorption. Positive volume/nonnegative physical parameters and initial capacity bounds are explicit; no arbitrary clamp.

Independent execution: 23 author tests passed in7.56s. Additional peer_numeric.py uses explicit independently authored ODEs with scipy DOP853, random parameter and initial-state variations seed2961:16 full-series cases passed, maximum absolute difference1.621e-10; adsorption total-mass/feed budgets and numerical nonnegativity passed. PEER-NUMERICAL.json retains case results. These checks supplement analytic limits/equilibria and do not claim unconditional numerical positivity for arbitrary edited steps.

Verified all996 baseline model hashes, admission/curation index hashes and four closest-model equation lists. The two-prey shared-enemy mechanism adds a distinct interaction absent from the two-state stable predator-prey and saturating Rosenzweig-MacArthur examples. The open-flow three-cell front differs from closed two-solute competitive Langmuir and from binary distillation's equilibrium vapor/liquid transport. The author's1079/1081 expanded-RHS scan has no matches; unsupported thermal/grid forms and stock-order limitations are disclosed, so this is not a universal equivalence proof.

Attribution, primary links, original defaults, symbolic units and source-rights limits are adequate. No source paper/renders or upstream implementation are added. Existing996 models/runtime/public state are unchanged. Accept both as separately reviewed illustrative candidates; root must authorize admission and release independently.
