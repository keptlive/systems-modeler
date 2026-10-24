# Remaining library quality review

2026-10-24; independent read-only audit by dimensional_analysis. No active definition, database, runtime, admission receipt or candidate JSON was changed. The checkout contained 978 active JSON files during the audit, including previously admitted source-backed batches. Findings below concern older definitions in the retained library; this is not a claim that all original 923 have received a fresh primary-literature review.

## Method and limits

Bounded scalar AST expansion substituted auxiliary/flow dependency DAGs into each stock's incoming-minus-outgoing derivative, normalized stock names by index, folded finite constant arithmetic, and compared both exact derivatives and coefficient-abstracted expression shapes. Crucially, legacy endpoints may be **stock names or IDs**: the independent audit resolved both before expansion. Calling Model.model_dump alone does not normalize those endpoints. An initial unnormalized scan was discarded because it falsely classified many named-endpoint models as stationary. The engineering candidate author was notified to fix its owned screening helper and rerun candidate checks before admission.

Two active definitions with unsupported scalar expressions were explicitly excluded from this static expansion: models/energy/duck-curve-solar-grid-ene.json and models/physics/heat-transfer-and-diffusion-model-phy.json. No equivalence under arbitrary state permutations, coordinate transformations, non-scalar compilation or transcendental identities is proved. Initials, grids, diagnostics, scientific mechanism and provenance were inspected separately; a shared RHS shape alone is not a retirement criterion.

Corrected scan: **2 exact derivative classes and 13 coefficient-abstracted classes** contain multiple active definitions. One exact class consists of three honestly labeled static calculators and is not a scientific duplicate. The other is a true duplicate Rössler simulation. Targeted simulations and source checks below establish the ranked findings. All hashes are snapshot identifiers, not authorization to mutate those files.

## Ranked concrete findings

### 1. High: both purported World3 capital subsets reverse the capital/output ratio

Paths: models/classic/world3-industrial-capital-sector-cla.json and models/classic/world3-capital-sector-cla.json.

Both define Industrial_Output by **multiplying** industrial capital by Industrial_Capital_Output_Ratio=3. The latter additionally multiplies by resource allocation factor0.95; the former by utilization0.85. Their stated World3 source [pyworld3 capital implementation](https://raw.githubusercontent.com/cvanwynsberghe/pyworld3/master/pyworld3/capital.py) explicitly defines ICOR in years and computes output as capital times utilization/resource factors **divided by ICOR** (_update_io). This makes the retained output nine times the analogous source output when ICOR=3, before considering other omitted feedbacks. Both also multiply service capital by an output-ratio constant rather than documenting an independently authored productivity coefficient.

The first expands to I'=(3*.85*.43-1/14)I=1.02507142857 I and S'=.765 I-.05 S. Default Euler output grows I from210 to4.076510419e63 over1900–2100. The second has I'=(3*.95*.27-1/14)I=.69807142857 I and grows2.1e11 to2.057833493e57. Those numbers are finite and mathematically reproducible; that is not World3 source fidelity. These are also the same triangular linear mechanism with different constants, not two independently reconstructed World3 sectors.

Recommendation: prioritize source-faithful reconstruction with independent sector regression and explicit fixed-feedback boundaries; retain only one canonical simplified sector unless a genuinely distinct scenario earns a separate entry. Until reviewed, withdraw the claim that either reproduces a World3 sector. Do not silently repair the multiplier in place: its consequences and other missing feedbacks require a reviewed replacement. The unrelated NSIDC citation in the second description also needs correction.

### 2. High: Black–Scholes option dynamics violate basic option-value meaning

Path: models/finance/black-scholes-option-fin.json.

Price_Change=S*(r/252+sigma*.01*sin(17t)); this is a deterministic oscillatory ODE, not geometric Brownian motion. Delta=.5+.4*d1/(1+abs(d1)) is an undocumented bounded rational proxy, not the normal CDF. Theta=-S*sigma/(2*sqrt(tau))/252 omits the source density/discount structure. Option_Change is Delta times the deterministic price change plus that Theta, initialized at10 with tau artificially floored at.01. It neither evaluates a call-price formula nor enforces its terminal payoff.

Default simulation yields **Option_Value=-6.181356866** at day252 with S=105.1497451 and strike100. A long call price cannot be negative; the positive expiry payoff is also not reproduced. This is an equation/model-scope problem, not a solver exception or request for a positivity clamp. The [original Black–Scholes paper](https://www.cs.princeton.edu/courses/archive/fall02/cs323/links/blackscholes.pdf) was available through primary indexed text; direct PDF retrieval returned403. Its pricing-formula attribution is not supported by these authored proxies.

Recommendation: replace through reviewed source-backed pricing/hedging reconstruction with analytic call-price, delta and expiry tests, or retire this claimed pricing model. A deterministic underlying path can be a useful declared teaching choice, but it does not justify the current pricing formulas or Nobel-model claim.

### 3. High: Watts–Strogatz diagnostic reports impossible average graph distance

Path: models/social/watts-strogatz-small-world-soc.json.

Only two edge-count stocks are integrated: R'=-.01R, Q'=.01R. No adjacency, random rewiring, connectivity or shortest-path computation exists. Its purported Path_Length is1/(10p) for p>0 and5 at p=0, where p=Q/(R+Q). Thus it is discontinuous at zero, initially increases sharply when the first shortcut appears, and becomes **0.157736753** at the default endpoint. Mean shortest-path distance between distinct connected nodes is at least1, so this cannot be the stated graph statistic. A network of100nodes with ten neighbors would also need its degree/edge-count convention clarified; initial1000edges does not match a degree-ten undirected ring's500edges.

The [original Watts–Strogatz paper](https://snap.stanford.edu/class/cs224w-readings/watts98smallworld.pdf) was retrieved. It defines graph-level structural measures; this edge-transfer ODE does not implement that mechanism. Sharing a two-compartment exponential-transfer shape with a resource-depletion example is not itself the fault: the unsupported structural diagnostics are.

Recommendation: retire or explicitly relabel as an authored shortcut-fraction surrogate, removing claims to measured network path lengths. A faithful graph model needs explicit graph semantics or independently justified approximations; capping distance at1 would merely conceal the error.

### 4. Medium-high: Markowitz entry has no optimization and ignores its nonzero correlation

Path: models/finance/markowitz-portfolio-fin.json.

Target_Stock_Weight is fixed at.6, while the description promises mean-variance optimization and an efficient frontier. No optimization or frontier is computed. Correlation=.2 is declared but unused. Portfolio_Risk=sqrt(w²*.2²+(1-w)²*.05²) omits2w(1-w)*rho*sigma_stock*sigma_bond. At initialw=.6 it gives.1216552506 instead of the covariance-consistent.1255388386. Deterministic sine returns are also not sampled correlated returns. The stock/bond/value accounting can work as an illustrative rebalancing example; it does not supply the named method.

The [original Markowitz paper](https://traders.berkeley.edu/papers/Markowitz.pdf) was retrieved and checked for its covariance-based selection framework. Recommendation: reconstruct an actual covariance-aware portfolio-choice example with an independently checked optimum/frontier, or relabel as fixed-weight illustrative rebalancing and disclose its return assumptions. Fixing the covariance term alone would still not create an optimizer.

### 5. High-confidence duplicate: identical Rössler simulation twice

Paths: models/physics/rssler-attractor-phy.json and models/physics/roessler-chaos-attractor-phy.json.

Both have x'=-y-z, y'=x+.2y, z'=.2+z(x-5.7), initials(.5,.5,.4), start0,end100,dt.03125, implicit Euler. Case/name/layout differences do not alter execution. Independently simulated all three stock columns are **bit-for-bit identical over every output** under corresponding stock-name mapping. No distinct mechanism, parameter regime or reference experiment is present.

Recommendation: retain **roessler-chaos-attractor-phy.json** as canonical because its source/reference identify Rössler1976 [doi10.1016/0375-9601(76)90101-8](https://doi.org/10.1016/0375-9601(76)90101-8); retire rssler-attractor-phy.json through the reviewed transaction workflow with an alias/redirect if supported. Both descriptions incorrectly append a Lorenz1963 reference; repair that separately with source review. Chaotic long-horizon agreement is not used as an accuracy claim here: identical execution proves duplication, not accurate shadowing.

### 6. Medium: Shannon entry is an undocumented lossy queue, not channel-capacity calculation

Path: models/technology/shannon-communication-channel-tec.json.

Channel_Capacity is fixed60 independently of signal/noise. SNR=10/2 and Error_Probability=.5*exp(-SNR/2) drive a split of transmitted messages into success/error counters; no bandwidth, coding rate, mutual information or Shannon capacity is calculated. Error-probability dependence needs a modulation/noise assumption that is absent. The [original Shannon paper](https://bayes.wustl.edu/Manual/shannon1948.pdf) was retrieved; a fixed queue service capacity is not a reconstruction of its information-theoretic limit.

Recommendation: relabel as an authored lossy-service queue and remove unsupported information-theory claims, or reconstruct a documented channel model with capacity/reference tests. Do not retire merely because a queue uses generic stock-flow balances; the issue is source/scope attribution.

### 7. Medium: three May logistic-map entries are parameter variants; preserve discrete semantics if consolidated

Paths: models/other/may-logistic-chaos.json, models/economics/may-ecological-chaos-eco.json and models/economics/may-chaos-population-eco.json.

All use P'=rP(1-P)-P, initial.1, end100,dt1, implicit Euler; r differs3.7/3.8/3.9. At these exact defaults the Euler update is P_next=rP(1-P), so the demonstrated map **is mathematically correct**. It would be wrong to condemn it as an intrinsically invalid ODE. However, changing dt or choosing another integration method produces a different system, not a refinement of the discrete map. The richest entry's Lyapunov Exponent Estimate is only log|r(1-2P)| at one iterate, not its long-run average; its regime classifier treats all r>3.57 as chaos, ignoring periodic windows.

Recommendation: one canonical discrete logistic-map teaching model with explicit generation period and r scenarios is preferable to three separate counts. Preserve existing default behavior and outputs during any reviewed migration. Relabel instantaneous log-slope and simplify unsupported regime labels. Original Nature DOI was identified but direct publisher access blocked; no full-paper reproduction claim made here.

### 8. Lower-priority consolidation/source audit: same Anderson–May host/parasite mechanism twice

Paths: models/epidemiology/host-parasite-equilibrium.json and models/epidemiology/anderson-may-host-parasite-coexist.json.

Both expand to H'=(a-b-alpha*P/max(H,1))*H and P'=(lambda-mu-b-alpha*(K+1)/K*P/max(H,1))*P, with K=2 and different parameter/scaling/horizon choices. Both explicitly describe tuning for equilibrium/coexistence. Both satisfy their neutral proportional-growth balance; the same host/parasite interaction is not a new mechanism because parasite scales differ. The max(H,1) guard alters low-host dynamics and needs an explicit modeling assumption. First lacks a source URL; second has a prose source only.

Recommendation: source review and one canonical mechanism with documented scenarios; do not retire automatically from coefficient abstraction. No independent original Anderson–May full-text fidelity assessment was completed in this pass.

### 9. Metadata provenance contamination is widespread and needs a separate scoped cleanup

A literal scan found **28 descriptions** citing NSIDC Arctic Sea Ice News outside obvious Arctic/sea-ice paths, including CAPM, World3 capital, skill learning, SaaS subscriptions and trade. Example models/finance/capm-asset-pricing-fin.json has an appropriate Sharpe DOI in source but an unrelated sea-ice reference in description. This is concrete copy contamination; it does not alone invalidate the CAPM expected-return equation or prove a duplicate. Some climate-topic matches may be defensible and require per-file review. Recommendation: source-by-source metadata correction with hash receipts, not deletion based on the string scan.

## Shared mathematics that is not sufficient evidence for retirement

The static calculators models/other/kingman-formula-variability-ops.json, models/energy/solar-panel-power-output-ene.json and models/transportation/lighthill-whitham-richards-traffic-tra.json all have zero stock derivatives, but their meaningful auxiliary calculations and current descriptions are distinct and explicit about being static. Keep their honest scope; equal zero derivatives are not a duplicate finding.

Likewise first-order material delay, bathtub and timeline decay share c-kX but have different educational contexts and explicit scope. Chemical conversion and phishing-awareness transfer, CAPM growth and induced-demand growth, Coase bargaining and gravity-trade adjustment, and two independent adjustment examples share algebraic classes without automatically sharing a scientific mechanism. These require source/usefulness review, not blanket removal. The bathtub example starts exactly at its stated equilibrium50=5*10 and is flat by construction; that is a teaching-default opportunity, not proof the equation is broken.

## Snapshot receipts and next action

Only the Rössler pair is recommended here as a conclusively redundant execution with a clear canonical-retention choice. The first four findings warrant higher-priority reviewed replacements or retirement because scientific scope fails even when simulation finishes. This report authorizes no retirement. Prioritize those source/meaning corrections over retaining an arbitrary catalog count. The engineering author subsequently corrected its helper to normalize both endpoint names and IDs with ambiguity rejection. The independent reviewer reran its three focused duplicate/endpoint checks together with four repair tests: seven passed in1.82s. Corrected candidate receipts report1,049active/staged files,1,047expanded and two explicitly unsupported, with no exact/coefficient-abstracted match for the eleven engineering candidates. Candidate hashes are unchanged; the earlier screening admission hold is resolved.

Hashes for concrete inspected files and abstract-class members follow. They bind the review to the present definitions and make subsequent repairs distinguishable.

| Path | SHA-256 |
|---|---|
| models/classic/world3-capital-sector-cla.json | `c03b5139002d5f6c04faee7afbb7a5ecd5ff4e498ac97c0504856fc069d8954c` |
| models/classic/world3-industrial-capital-sector-cla.json | `21f934c4e007b71ffd929dbc33e1ab95890497e41ca30bb0aa2db2f5dbd824be` |
| models/climate/atmospheric-carbon-bathtub-cli.json | `50c66c289a7fa5e414ca3159f62b0353e6ab68d555be01cf2da192cf2d05a047` |
| models/economics/coase-theorem-bargaining-eco.json | `1404521433250033b8bd56b86f60d63fe248d8de76e250ee1cb99a25d59b0ff6` |
| models/economics/gravity-model-trade-eco.json | `7f59a5fdecd77299e692cb0d2678ffd30a27267b73a5951459e866fd71e066cc` |
| models/economics/hotelling-resource-extraction-eco.json | `918d948b02c0edc774cdf31321385b9a71e9a414537538dd38856e537601f0d6` |
| models/economics/may-chaos-population-eco.json | `7e303bdb46e3e542d32f94e0690f735da5b4cc30ea755b5801a957b6d3976518` |
| models/economics/may-ecological-chaos-eco.json | `91ef1ec605080528bdece04cae503e9c72bab9adc6aaaf6096a89ce4313140bd` |
| models/economics/stolper-samuelson-wages-eco.json | `f27b5f98d9ac4bcebb8e17efa764a16d98f9611c51d8453214a83aba3849b37c` |
| models/education/bathtub-dynamics-demo-edu.json | `3de55e1de53ad12f91d92f304f2e9820e1b6bbe9d3e2a1f88ffafdf05e800ed0` |
| models/education/first-order-delay-edu.json | `9ef5e93e77f44118a6a239d98d65cc2037bfe456ca8362cab7c75a6b359144db` |
| models/education/penny-jar-distribution-edu.json | `16cdbf55f1247f6d2e27cf7d21bc3cb31a4673ec863e5991a78f754a28100b59` |
| models/energy/solar-panel-power-output-ene.json | `b1ab07302712369a4f939aca97d4e1a08b45821f80ace72e7aabc7db2a571f07` |
| models/epidemiology/anderson-may-host-parasite-coexist.json | `6c1c6ce28fc998663ad6ca027557f3bd162fae5ee93af67d61657ea2a01db268` |
| models/epidemiology/host-parasite-equilibrium.json | `5d1356221b8b86763e6d7ce0fa24912e5021da354347d4edfe311bee35f47a77` |
| models/epidemiology/seird-epidemic-model-epi.json | `973c0f1b942e2989e180b06332ffe56003fb5adcf2d5a246b0cfaf485e932da2` |
| models/epidemiology/who-seird-influenza-epi.json | `1b9342a5b8a0b181b0b7984d1571c9e4be768672086aa8b402e83f8f0a7ddf1e` |
| models/finance/black-scholes-option-fin.json | `9800dffbb1ef0442bb065f82ad71a1d1de74951d8808038871cb6873450ad5e7` |
| models/finance/capm-asset-pricing-fin.json | `41650843756c51ecea446eb360f28f9a633877c12774c27f88ba47d19d089e77` |
| models/finance/markowitz-portfolio-fin.json | `f7b48c70671182924e7ccc5530706cb3890b96fc9be4aa82c317f0557339d5ab` |
| models/other/atmospheric-bathtub.json | `1a2edaada89a3e8706fb28855d22ac4978c6758532775353cc5653dfbf30ad5c` |
| models/other/kingman-formula-variability-ops.json | `c00ec53f57c28a3f27107aa734a6ae3fc3d3172af3c53c913957d4da48f59a30` |
| models/other/may-logistic-chaos.json | `7abd9c5fe02d34703228bea243e6cdade562db9c833cf45c4c6f94c4a96d30c8` |
| models/physics/chemical-reaction-ab-phy.json | `1784dc1075432800cef783202f48b9299ef5312c04c55c45d952f557978f5c09` |
| models/physics/roessler-chaos-attractor-phy.json | `ca08b64c9f50f6b7aaa57f2217eb9d90d2a628c78e7de926cacf7fe534924eba` |
| models/physics/rssler-attractor-phy.json | `6caa6e40a7d9608b597a8457139bf4ce74a475a525b89ddfc65caf08c39308fe` |
| models/psychology/representational-heuristics-bias-psy.json | `47d5bd2e59a1ac89246ee707e263c88b802d26d2e0daec1f90973e63c9b80d06` |
| models/social/induced-demand-transportation-soc.json | `33ce34159a5fb98045debdb116f00f9a41b566b862e6bcfe1ff9e32c7471d194` |
| models/social/twitter-timeline-dynamics-soc.json | `4632f0a6b3fc127b160b5390fe7bb416ee469b44a449c2efcbbf3cf8b54be2ef` |
| models/social/watts-strogatz-small-world-soc.json | `f2f753d9ffc31ff7cf4fb1f67b07f76d2eac8803844d74e4cccf546e2ae0a0a0` |
| models/technology/phishing-awareness-training-tec.json | `c0b782a0c672fb577bbadb14234de89f90fda094780cf769b5c2b8aa6fce0979` |
| models/technology/shannon-communication-channel-tec.json | `bf2c9cb984f264d2e082935523d18f83dc594cefd29c3e98a2eb902f135d4618` |
| models/test/simple-growth.json | `ccba64f568358f1da413860be7f3f5fb35e0af7ccc572c742373638020ea30be` |
| models/transportation/lighthill-whitham-richards-traffic-tra.json | `767692408b873e660cfcb18da4a67b046f86b3b2719784f8cdd19975b828a7fc` |
