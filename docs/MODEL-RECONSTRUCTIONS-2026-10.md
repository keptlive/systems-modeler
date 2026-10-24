# Curated literature-equation reconstructions, October 2026

These five definitions previously had no flows and therefore frozen stocks. They now implement explicit textbook/literature ODEs. They are **illustrative, uncalibrated scenarios**, retaining the original parameter values, initial values, IDs, stock/auxiliary positions, connectors, and time horizons. They are not imported native author files and have no claimed empirical fit, numerical identity to an author implementation, or source license inherited by implication. The original six candidates were reviewed; Nerlove-Arrow was excluded (below).

Byte-exact originals of the five changed definitions are in `tests/fixtures/reconstruction-202610/`; `SHA256.json` records their original path and SHA-256. Source/reference metadata was corrected where the old link did not establish the named source. No native executable source was copied. Links checked 2026-10-23; some PMC publisher pages imposed browser challenges, so indexed equation text was available while full direct-page extraction was blocked.

## Microbiology: Monod and chemostat

[Monod (1949), The Growth of Bacterial Cultures](https://doi.org/10.1146/annurev.mi.03.100149.002103) is the historical attribution for the specific-growth relation. The accessible authored protocol [Gresham and Hong (2014), The Use of Chemostats in Microbial Systems Biology](https://pmc.ncbi.nlm.nih.gov/articles/PMC3940325/), Figure 2 equations 1-2, supplies the coupled balances. [Gresham and Hong (2015), The Functional Basis of Adaptive Evolution in Chemostats](https://pmc.ncbi.nlm.nih.gov/articles/PMC4391987/) also states the substrate balance as equation 2. We use:

- `mu=mu_max*S/(Ks+S)`.
- Chemostat: `X'=mu*X-D*X`; `S'=D*Sin-D*S-mu*X/Y`. Five named flows implement the two balances. Existing `Net_Growth` remains an auxiliary.
- Monod batch: set the transport term D to zero, yielding `X'=mu*X`, `S'=-mu*X/Y`. This is our closed-batch deduction from the balances, not a claimed Monod source-file reproduction. Two flows implement biomass production and substrate consumption.

Constant yield, perfect mixing, one limiting nutrient, no maintenance/death, and sterile feed are assumptions. Biomass/substrate represent consistent mass concentrations; Y is biomass mass/substrate mass, mu and D inverse time. No organism, nutrient, concentration unit or time unit was inferred for the inherited scenario.

## Levins patch occupancy

The historical citation is [Levins (1969), Some Demographic and Genetic Consequences of Environmental Heterogeneity for Biological Control](https://doi.org/10.1093/besa/15.3.237), not the inherited unrelated Springer DOI. [Williams and Hastings (2011), Paradoxical persistence through mixed-system dynamics](https://pmc.ncbi.nlm.nih.gov/articles/PMC3061147/) explicitly gives `p'=c*p*(1-p)-e*p`. Two flows use the already-present colonization/extinction auxiliaries. `Occupied_Patches` is an occupied **fraction**, not a count; homogeneous patches and mass-action colonization are assumed. Rates are inverse time. Defaults imply equilibrium p=0.6.

## One-compartment kinetics

[Lennon O Naraigh (2023), Case Studies in Mathematical Modelling, UCD](https://maths.ucd.ie/~onaraigh/CSMM/CSMM_v1.pdf), section 5.2, gives first-order elimination and the clearance relationship. We implement `A'=-CL*A/V`, `C=A/V`; the initial stock represents an already absorbed bolus and there is no subsequent input. CL is volume/time and V volume; mass and time units remain unspecified. This is a teaching scenario, not a dosing recommendation. The existing approximate half-life report `0.693*V/CL` is preserved.

## Mass-spring-damper

[Sanjay Sarma et al., MIT 2.003J (2007), The Behavior of Dynamic Systems](https://ocw.mit.edu/courses/2-003j-dynamics-and-control-i-fall-2007/2cdba03827d012dc69402e8bb8828815_system_behavior.pdf), equation 10 (printed page 5) and forced equation 26 (printed page 8), gives `m*x''+c*x'+k*x=F(t)`. Signed integration flows implement `x'=v`, `v'=(F-c*v-k*x)/m`; negative displacement/velocity are physically meaningful. Linear spring, viscous damping and constant mass are assumed. Units must be consistent (for example kg, m, seconds); no physical calibration is claimed.

## Exclusion and numerical evidence

Nerlove-Arrow was not changed. Its unexplained `Sales` stock cannot be reconstructed from its goodwill ODE: sales is ordinarily an output rate/function. Inventing sales adjustment dynamics, or relabeling a stock as cumulative sales, would introduce unsupported assumptions. The original remains eligible for archival by the curation owner.

All five use explicit RK4 with the inherited output step. This is a declared numerical choice; equations contain no new clipping or stabilizing clamps. `tests/test_curated_reconstructions.py` checks full default completion and every series finite, existing canvas/data preservation, Levins and pharmacokinetic closed forms, damped-oscillator closed form and dissipating energy, plus independently handwritten microbiology ODEs solved with DOP853 and step halving. Batch mass `S+X/Y` is conserved; chemostat total obeys `T'=D*(Sin-T)`. Full-horizon microbiology errors are bounded by 0.0005 concentration units for batch and 0.00003 for chemostat, with more than tenfold improvement on halving dt. These checks establish the specified mathematical implementation, not biological/clinical/engineering validity.

Validation: `.venv/bin/python -m pytest -q tests/test_curated_reconstructions.py` — 10 passed.
