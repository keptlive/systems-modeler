# Corpus reconciliation 1.7, partition B

Reviewed 2026-10-20. This covers **all 45** failed public definitions with zero-based sorted failure index `i % 3 == 1` from `operations/library-full-v160.json`. **19 now complete full default runs; 26 still fail explicitly.** 26 definitions changed. Completion and scientific validation are recorded separately: the review does not certify all 19 completed constructions.

The permanent [machine-readable ledger](../operations/corpus-reconciliation-v17-b.json) contains every diagnosis, source scope, before/current SHA-256, exact field diff, baseline failure, current default-run outcome, source URLs, engine hashes and first-negative-stock evidence where available. It records uncertainty for every assigned model.

## Bounded changes

Most changes replace unresolvable shortened symbols with quoted full names of unique existing elements. Two notation translations preserve distinct local a/A and k/K mathematical constants at the case-insensitive language boundary. Dengue alone receives an algebraic population closure: the existing Sh->Ih->Rh graph exactly conserves its 10000 humans, so both missing Nh normalizers become `(Sh + Ih + Rh)`. This is disclosed mathematical reconstruction, not an assertion that the local dengue model reproduces a textbook. No numerical constants, stock initial values, simulation grids, stock/flow IDs, positions, flow topology, connectors or model IDs changed.

Missing measles beta/N and zero vaccination, TB population convention, zero-initialized clinical/platform compartments, absent World3 tables and incomplete nitrogen/sea-ice dynamics remain explicit. No clamps, guessed seeds, arbitrary timestep changes or placeholder-zero substitutions were used.

Seven bibliographic/source clarifications distinguish exact original model files from conceptual references. Franks is Journal of Oceanography 58:379-387, DOI 10.1023/A:1015874028196; Hom is DOI 10.1037/apl0000103; Taylor is DOI 10.1016/j.tra.2008.06.007; the ransomware DOI was an IoT-botnet ML paper, so the file now cites its stated CISA context with an explicit limitation. Bounded-confidence now cites Hegselmann-Krause 2002, while disclosing that its continuous relaxation and strict threshold differ from the original discrete averaging.

## Exact original source recovery

- [aging original MDL](https://raw.githubusercontent.com/SDXorg/PySD-Cookbook/d7ebddadad9cd87cf796b9b6031ea2b5c45da4c4/source/models/Aging_Chain/Aging_Chain.mdl), commit `d7ebddadad9cd87cf796b9b6031ea2b5c45da4c4`, SHA-256 `b463559b9b43c37bf132320bdf8be830fa6c492297dc6a2b0f78631ded9c1e01`.
- [pendulum original MDL](https://raw.githubusercontent.com/SDXorg/test-models/21aab02739dc5187bc9564e4d3de14e575905d2f/samples/pendulum/Single_Pendulum.mdl), commit `21aab02739dc5187bc9564e4d3de14e575905d2f`, SHA-256 `8c8fb6c1c292ee3dd475cf1ac7fc779a744afb425e25a7851dfdafdaf3a5bf59`.
- [beer original MDL](https://raw.githubusercontent.com/JimDuggan/SDMR/89bbfe65c25db5bcca511c10ef6527c8ebe35696/models/08%20Additional/05%20Retailer%20Beer%20Game/Full%20Beer%20Model.mdl), commit `89bbfe65c25db5bcca511c10ef6527c8ebe35696`, SHA-256 `5e075f37ea28e82ca0e379604ae197bd88709e4768c65b5ae2dd8c2dffea5e8a`.

Aging Chain source equations and initial values are recovered; local expanded labels and horizon remain. Full Beer source itself contains sketch `A FUNCTION OF` definitions followed by executable duplicate definitions. Repairing that importer/source representation without losing IDs, layout or content remains unresolved. No arbitrary deduplication was attempted.

Single Pendulum matches original parameters/equations/initials and 0..100-second grid with dt=.0078125. The engine owner expanded bounded simulation capacity, allowing its original 12800 intervals. Its unchanged Euler defaults nevertheless increase undamped energy from 450.503740 to 827.456281 (+83.6736%). The invariant test contrasts that drift with RK4 on the same equations; numerical completion is deliberately not labeled an accuracy success.

## All assigned diagnoses

### 1. urban-dynamics-model-simplified-cla — DEFAULT COMPLETES

Population shorthands referred to expanded existing stocks. Reconnected uniquely. Migration multipliers and policy parameters remain illustrative; stored citation does not establish reproduction of Forrester Urban Dynamics.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://proceedings.systemdynamics.org/2010/proceed/papers/P1153.pdf), [source 2](https://doi.org/10.1287/mnsc.35.3.321).

### 4. world3-non-renewable-resources-sector-cla — UNRESOLVED FAILURE

Repaired resource stock alias. Resource_Usage_From_Industry and Resource_Extraction_Fraction functions/tables and Industrial_Output_Per_Capita input are absent. No industrial trajectory or lookup coordinates were invented.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://doi.org/10.1016/B978-0-12-850754-3.50020-2).

### 7. arctic-sea-ice-decline-model-cli — UNRESOLVED FAILURE

feedback_amplification is undefined. Formation, volume loss and multi-year ice loss are zero placeholders. No matching original model identified in the cited umbrella cookbook repository; no feedback formula invented.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://github.com/SDXorg/PySD-Cookbook).

### 10. forest-fire-spread-cli — UNRESOLVED FAILURE

Fuel_Load outflow is proportional to total active hectares despite fuel-load stock units. Negative fuel reverses spread/residence-time signs, eventually making active area negative and square root invalid. Rothermel original uses heat-source/heat-sink formulation; arbitrary nonnegative clamps would conceal missing units and depletion semantics.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://research.fs.usda.gov/treesearch/32533), [source 2](https://doi.org/10.2737/INT-RP-115).

Independent direct Euler trace: first negative stock at time 6.0: Fuel_Load=-1.32279744.

### 13. global-nitrogen-cycle-model-cli — UNRESOLVED FAILURE

industrial_fixation is both variable 120 and flow 0; all six nitrogen transfers are zero placeholders. Stock and BNF scales have no declared unit conversion. Renaming alone would yield a static unverified cycle. No matching original located in cited umbrella repository.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://github.com/SDXorg/PySD-Cookbook).

### 16. manabe-wetherald-radiative-cli — DEFAULT COMPLETES

Tropospheric_Temp and Stratospheric_Temp uniquely referred to existing Temperature stocks. Fixed aliases only. Manabe-Wetherald original uses vertical radiative-convective calculation; this three-box radiation system and fitted emissivity/capacities are not a demonstrated reproduction.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://www.gfdl.noaa.gov/bibliography/related_files/sm6701.pdf), [source 2](https://doi.org/10.1175/1520-0469(1967)024<0241:TEOTAW>2.0.CO;2).

### 19. ocean-heat-content-dynamics-cli — UNRESOLVED FAILURE

Heat-release flow multiplies content by SST-15 although SST starts at zero anomaly; negative outflow initially adds heat. Transfer terms reverse beyond capacity. Cheng article reports observations, not these four box equations. Absolute/anomaly conventions and flux units need original-source reconstruction.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://pubmed.ncbi.nlm.nih.gov/30630919/), [source 2](https://doi.org/10.1126/science.aav7619).

Independent direct Euler trace: first negative stock at time 19.0: Intermediate_Layer_Heat=-1.6006648.

### 22. simple-global-carbon-cycle-cli — DEFAULT COMPLETES

CO2_Fertilization uniquely refers to CO2 Fertilization Factor 0.3. Reconnected without changing formula. Reservoir exchanges and NPP calibration remain unverified against textbook chapter.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://assets.press.princeton.edu/chapters/s10_8223.pdf), [source 2](https://doi.org/10.2307/j.ctt3fgxqx).

### 25. aluminum-supply-chain-sustainability-eco — UNRESOLVED FAILURE

Production accumulates as a stock but revenue treats it as a rate. Investment makes decarbonization unbounded and emission removal overshoots carbon. MDPI original documents a 1990-2050 industrial model; its supplementary-model mapping to these five local stocks and units is absent.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://www.mdpi.com/2071-1050/16/20/8892), [source 2](https://doi.org/10.3390/su16208892).

Independent direct Euler trace: first negative stock at time 2.0: Carbon_Emissions=-3045278.97.

### 28. container-port-operations-eco — DEFAULT COMPLETES

Arrival_Rate and Crane_Productivity uniquely refer to existing Vessel Arrival Rate and Crane Productivity (TEU/day). Reconnected. Throughput units and conservation require review; umbrella SDX repository is not an identified port model.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://github.com/SDXorg/test-models).

### 31. dmp-search-matching-eco — UNRESOLVED FAILURE

Euler drives unemployment negative, making square roots complex. Fixed positive vacancy entry and local wage/profit closure are not mapped to Mortensen-Pissarides equilibrium. No guessed parameters, timestep or clamps.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://doi.org/10.2307/2297896).

Independent direct Euler trace: first negative stock at time 1.5: Unemployment=-0.000879625133.

### 34. forest-ecosystem-carbon-and-succession-model-eco — DEFAULT COMPLETES

Matched shortened cohorts/carbon/disturbance/NPP/respiration/harvest names to unique existing elements. Ecological flux signs, cohort assumptions and calibration remain unverified. No matching original identified in umbrella source repository.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://github.com/SDXorg/test-models).

### 37. lucas-human-capital-eco — DEFAULT COMPLETES

Gamma uniquely refers to Gamma (Spillover) 0.1. Fixed alias. Lucas supplies conceptual human-capital/externality background; finite-cohort calibration and initial values are unverified.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://doi.org/10.1016/0304-3932(88)90168-7).

### 40. npz-ocean-ecosystem-eco — UNRESOLVED FAILURE

Euler can overshoot nutrient/plankton positivity. Three derivatives sum to -(1-gamma)*G*Z*P/(Kg+P), losing unassimilated grazing without an explicit sink/export explanation. Corrected Franks bibliography to Journal of Oceanography. No assumed recycling term or timestep inserted.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://link.springer.com/article/10.1023/A:1015874028196), [source 2](https://doi.org/10.1023/A:1015874028196).

Independent direct Euler trace: first negative stock at time 3.0: Nutrient=-5.91307922.

### 43. predator-prey-allee-effect-eco — DEFAULT COMPLETES

Distinct lowercase a=.02 attack coefficient and uppercase A=20 Allee scale collide in case-insensitive SD syntax. Translated to descriptive names retaining notation, preserving values/IDs/layout. Weak-Allee factor and predator-prey calibration are not validated by the review citation.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://webpages.ciencias.ulisboa.pt/~mcgomes/aulas/dinpop/Temas/Courcham%20et%20al%201999%20Inverse%20density%20dependence%20and%20the%20Allee%20effect.pdf), [source 2](https://doi.org/10.1016/S0169-5347(99)01683-3).

### 46. semiconductor-chip-shortage-supply-chain-eco — UNRESOLVED FAILURE

Desired capacity and panic ordering multiply endogenous stocks, producing runaway feedback. ECB source analyzes observed trade bottlenecks, not these stock-flow equations; no demand cap or guessed adjustment time.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://www.ecb.europa.eu/press/economic-bulletin/focus/2021/html/ecb.ebbox202104_06~780de2a8fb.en.html).

### 49. startup-growth-and-funding-model-eco — DEFAULT COMPLETES

Mapped Users/Cash/CAC/MRR/ARR/LTV/salary/acquisition/revenue/expense shorthands to unique existing elements. Funding timing, quality bounds and negative-cash behavior remain unverified; umbrella repository is not an original startup model.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://github.com/SDXorg/test-models).

### 52. technology-adoption-lifecycle-model-eco — DEFAULT COMPLETES

Innovation_Coefficient and Imitation_Coefficient uniquely refer to existing annotated p/q parameters. Bass supports innovation/imitation background only; advertising/network/quality/abandonment extensions remain unverified.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://pubsonline.informs.org/doi/abs/10.1287/mnsc.15.5.215), [source 2](https://github.com/SDXorg/test-models).

### 55. aging-chain-population-cohorts-edu — DEFAULT COMPLETES

Exact cookbook Aging_Chain.mdl recovered: decade aging=decade/10, loss=decade*.05, each initial 10, birth 0. JSON expanded stock names but kept Dec_1 shorthands. Repaired all cohort/loss aliases. Local horizon remains an explicit preserved adaptation.

Source scope: Exact original MDL inspected; source scope/deviations are stated in diagnosis.

Evidence: [source 1](https://github.com/SDXorg/PySD-Cookbook/blob/master/source/models/Aging_Chain/Aging_Chain.mdl).

### 58. online-learning-platform-edu — UNRESOLVED FAILURE

Unbounded content quality eventually exceeds100, making Late_Dropout negative and supplying active learners. Completion-quality feedback then runs away. Original Kizilcec paper classifies observed learner trajectories, not these stock-flow equations.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://stanford.edu/~cpiech/bio/papers/deconstructingDisengagement.pdf), [source 2](https://doi.org/10.1145/2460296.2460330).

Independent direct Euler trace: first negative stock at time 26.25: Dropped_Out=-269.189913.

### 61. age-structured-epidemic-who-epi — UNRESOLVED FAILURE

Contact-based infection exhausts susceptible stock in a one-day Euler step. Mossong is an empirical contact survey; local two-age aggregation, Beta .3 and constants have no recovered calibration mapping. No infection clamp or guessed timestep.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.0050074), [source 2](https://doi.org/10.1371/journal.pmed.0050074).

Independent direct Euler trace: first negative stock at time 4.0: S_Children=-919.128937, S_Adults=-5126.57232.

### 64. covid-19-seir-model-epi — DEFAULT COMPLETES

Beta and R0 uniquely refer to existing annotated parameters. Repaired only references. Clinical proportions, delays and initialization are local COVID illustration; Hethcote is general background, not original COVID calibration.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://doi.org/10.1137/S0036144500371907).

### 67. dengue-vector-borne-disease-model-epi — DEFAULT COMPLETES

Nh undefined. Human transitions are only Sh->Ih->Rh, so total humans is uniquely conserved at 10000. Replaced Nh with (Sh+Ih+Rh) in both infection formulas. Mathematical reconstruction of normalizer, not verified textbook dengue restoration; check full-run conservation and positivity. The library description explicitly records the human-sum reconstruction and unresolved fidelity; it no longer claims that Nh is undeclared or that all equations are unchanged.

Source scope: Conserved normalizer reconstructed from local topology; Ross-Macdonald framework is context, not exact dengue source.

Evidence: [source 1](https://journals.plos.org/plospathogens/article?id=10.1371/journal.ppat.1002588), [source 2](https://doi.org/10.2307/j.ctvcm4gk0).

### 70. measles-vaccination-coverage-model-epi — UNRESOLVED FAILURE

beta and N absent; vaccination=0 despite vaccination_rate .01. Plausible beta=R0*gamma is not exact-original evidence for this particular construction. No denominator, transmission or vaccination closure guessed.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://doi.org/10.2307/j.ctvcm4gk0).

### 73. seasonal-influenza-transmission-model-with-vaccination-epi — DEFAULT COMPLETES

R0, seasonal peak and susceptible/breakthrough infection shorthands mapped to unique existing elements. Rates/grid/initial values preserved. Broad textbook citation does not identify this seasonal vaccination campaign construction.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://doi.org/10.2307/j.ctvcm4gk0).

### 76. tuberculosis-transmission-model-epi — UNRESOLVED FAILURE

N absent. TB mortality leaves living compartments, so initial-cohort versus current-living denominator changes dynamics. General textbook citation does not identify intended convention; no denominator chosen merely for completion.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://doi.org/10.2307/j.ctvcm4gk0).

### 79. leverage-cycle-dynamics-fin — UNRESOLVED FAILURE

Price/leverage multiply without finite wealth/collateral budget or market clearing. Original Geanakoplos model determines leverage by equilibrium; local autonomous feedback equations are not its equation set. No arbitrary caps.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://www.journals.uchicago.edu/doi/full/10.1086/648285), [source 2](https://doi.org/10.1086/648285).

### 82. antibiotic-resistance-evolution-extended-hea — UNRESOLVED FAILURE

Bacterial stocks, drug pipeline and effectiveness all start 0; effectiveness decay divides by total bacteria 0. Lancet commission provides context only. No bacterial seed or denominator guard invented.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://www.dcp-3.org/sites/default/files/resources/antibioticresistance.pdf), [source 2](https://doi.org/10.1016/S1473-3099(13)70318-9).

### 85. chronic-disease-progression-model-hea — DEFAULT COMPLETES

Healthy/At_Risk/Undiagnosed/Birth_Rate uniquely map to existing stocks/parameter. Clinical rates/costs/initial values preserved. Earlier source review found no original for this healthcare construction; completion is not clinical validity.

Source scope: No original identified; local wiring repairs do not establish scientific validity.

Evidence: no original scientific source identified in the prior healthcare source review or this pass.

### 88. mental-health-treatment-system-dynamics-hea — UNRESOLVED FAILURE

Repaired unique health/cohort/capacity/workforce/stigma/dropout/budget aliases. All eight population compartments remain 0, making prevalence/treatment-gap undefined. Initial Population 10m does not specify allocation. No distribution or fallback ratios invented.

Source scope: No original identified; local wiring repairs do not establish scientific validity.

Evidence: no original scientific source identified in the prior healthcare source review or this pass.

### 91. organizational-knowledge-loss-man — UNRESOLVED FAILURE

Knowledge transfer consumes expert stock proportional to both knowledge stocks; Euler eventually overshoots experts below0 and runs away. Copying knowledge need not consume experts: flow interpretation needs source. Corrected Hom DOI; turnover review is not local model calibration.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://asu.elsevierpure.com/en/publications/one-hundred-years-of-employee-turnover-theory-and-research/), [source 2](https://doi.org/10.1037/apl0000103).

### 94. workforce-overtime-morale-man — UNRESOLVED FAILURE

Initial completion2400 versus backlog200 and arrivals200 makes backlog-900 after first .5 step. Negative backlog drives negative target workforce; unbounded overtime/morale and quitting/Morale cause runaway. Generic Vensim sample index does not identify units or exact original.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://vensim.com/documentation/sample_models.html).

Independent direct Euler trace: first negative stock at time 0.5: Work_Backlog=-900.

### 97. full-beer-model — UNRESOLVED FAILURE

Exact JimDuggan Full Beer Model.mdl itself contains A FUNCTION OF sketch definitions then executable duplicates for R/W Order Rate and W Customer Orders. Import treated both as elements. Dedup would remove/merge IDs/layout/content; no arbitrary removal/zero substitution. Expected-order CECO stock wiring also needs source reconciliation.

Source scope: Exact original MDL inspected; source scope/deviations are stated in diagnosis.

Evidence: [source 1](https://github.com/JimDuggan/SDMR).

### 100. cell-cycle-regulation-phy — DEFAULT COMPLETES

Distinct k3..k6 and K3..K6 collide in case-insensitive SD syntax. Translated names to Parameter lowercase/uppercase retaining symbols; replaced exact-case uses. Values/IDs/layout/topology preserved. Exact local four-state mapping to Tyson-Novak remains unverified.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://pubmed.ncbi.nlm.nih.gov/11371178/), [source 2](https://doi.org/10.1006/jtbi.2001.2293).

### 103. heat-transfer-and-diffusion-model-phy — DEFAULT COMPLETES

Temperature/HVAC/Q_* aliases uniquely matched existing full names using quoted references. No capacities/signs/grid changed. Solar double-counting, flux display signs and building calibration need physics review; original model not identified.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://github.com/SDXorg/test-models).

### 106. nuclear-power-plant-operations-phy — UNRESOLVED FAILURE

100000 intervals times reported elements exceeds new1m retained-value/work limits. Initial prompt rate -1.65e11 and delayed release 4e6 with dt .01 makes neutron stock negative first step. Power/heat units and Doppler sign need review. No capacity bypass, dt or guessed constants.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://doi.org/10.1002/9783527812318), [source 2](https://github.com/SDXorg/test-models).

Independent direct Euler trace: first negative stock at time 0.01: Neutron Population=-649960000.

### 109. simple-pendulum-phy — DEFAULT COMPLETES

Exact native Single_Pendulum.mdl recovered:0..100 seconds,dt .0078125,12800 intervals; initial values/equations/parameters match. Expanded engine budget permits unchanged grid. Undamped Euler energy grows 83.7%; completion is not an accuracy pass. Invariant/convergence evidence included.

Source scope: Exact original MDL inspected; source scope/deviations are stated in diagnosis.

Evidence: [source 1](https://github.com/SDXorg/test-models/blob/master/samples/pendulum/Single_Pendulum.mdl).

### 112. bounded-confidence-opinion-soc — DEFAULT COMPLETES

Distance_12/Interact_12 pairs map to existing hyphenated names. Fixed aliases and replaced unrelated DOI with original Hegselmann-Krause. Original discrete synchronous averaging includes confidence boundary; local continuous relaxation/strict< threshold/polarization stock are preserved adaptations.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://www.jasss.org/5/3/2/2.pdf), [source 2](https://www.jasss.org/5/3/2.html).

### 115. hardin-tragedy-commons-extended-soc — UNRESOLVED FAILURE

Harvest independent of remaining resource exceeds regeneration, crosses zero, then negative logistic regeneration runs away. Hardin essay does not supply these equations/parameters. No depletion clamp or assumed harvest saturation.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://doi.org/10.1126/science.162.3859.1243).

Independent direct Euler trace: first negative stock at time 8.25: Common_Resource=-15.3425043.

### 118. milgram-small-world-soc — UNRESOLVED FAILURE

branching_factor 50 is used as continuous logistic rate with dt 1; reached population exceeds total then becomes negative and invalidates logarithm. Milgram observed message chains, not these logistic equations. No guessed reinterpretation/timestep.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://doi.org/10.1037/h0024480).

Independent direct Euler trace: first negative stock at time 6.0: People_Reached=-1.7565993e+09.

### 121. population-momentum-soc — DEFAULT COMPLETES

Cohort/fertility/mortality shorthands map to expanded names. Fertility on both-sex reproductive cohort lacks specified female fraction. Stored social-network paper unrelated to Keyfitz; no demographic constants or sex ratio added.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://populationsciences.berkeley.edu/publications/classic-population-publications-uc-berkeley/), [source 2](https://doi.org/10.2307/2060339), [source 3](https://doi.org/10.1016/j.socnet.2007.04.006).

### 124. social-network-effects-and-technology-adoption-model-soc — UNRESOLVED FAILURE

Repaired market/network/WOM/adoption/target aliases. Active/potential/competitor stocks all 0 despite initial-value parameters, giving undefined ratios. No population allocation/ratio guards invented; stored social-network DOI does not specify platform model.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://doi.org/10.1016/j.socnet.2007.04.006).

### 127. urban-traffic-flow-dynamics-soc — UNRESOLVED FAILURE

Linear speed-density gives negative speed beyond jam density. dt .1 hours*60km/h/1km=6 violates cell transport positivity scale; inflow not supply-limited. Initial explicit updates overshoot and blow up. LWR original spatial conservation law is not these queue heuristics.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://doi.org/10.1098/rspa.1955.0089).

Independent direct Euler trace: first negative stock at time 0.2: Vehicles_Segment_1=-123.038657.

### 130. ransomware-cyber-threat-tec — UNRESOLVED FAILURE

Capability grows from accumulated revenue without losses; attacks exceed vulnerable organizations and cause negative populations/runaway. Stored DOI is IoT-botnet ML. Replaced with cited CISA guidance, explicitly conceptual not local equations.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://www.cisa.gov/stopransomware/ransomware-guide).

Independent direct Euler trace: first negative stock at time 69.0: Vulnerable Organizations=-174844.152.

### 133. urban-rail-transit-ridership-tra — UNRESOLVED FAILURE

Adds 10% of dollar revenue directly to 0..100 quality without cost-per-quality conversion. First step adds 6250 quality units net .25 loss, making attrition negative. Corrected Taylor DOI; empirical transit demand study is not this dynamic three-stock system.

Source scope: Bibliographic/conceptual background only; no complete original equation/calibration mapping established.

Evidence: [source 1](https://www.sciencedirect.com/science/article/abs/pii/S0965856408001274), [source 2](https://doi.org/10.1016/j.tra.2008.06.007).

Independent direct Euler trace: first negative stock at time 0.75: Potential_Riders=-424776.796.

## Validation and limitations

`python -m pytest tests/test_corpus_partition_b_v17.py -q`: 8 passed in 2.92s. Tests cover complete partition/hash/diff accounting and preservation, independently derived aging-chain total balance, full-run dengue human/vector conservation and positivity, distinct case-sensitive mathematical constants after translation, convex/symmetric opinion averaging, native-grid pendulum energy diagnostics and RK4 invariant, unresolved-source errors and workforce first-step domain failure.

The full partition audit uses each definition's complete default horizon. The ledger records ranges even for completed models, because finite output alone does not prove realistic states or calibrated behavior. No external empirical comparison was claimed for generated constructions. Native model recovery was achieved for three sources only; publisher access was mixed, some originals were blocked or abstract-only, and broad repository references did not identify the missing models.

Existing historical source-only receipts should be validated through the explicit subsequent field-diff chain; current bytes cannot remain equal to their earlier after-hashes after reviewed 1.7 reference corrections. Original receipts are preserved. No deployment, public push, version bump or global-audit overwrite was performed.
