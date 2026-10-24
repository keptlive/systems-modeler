# Corpus repairs 1.8 — partition B

This review covers every one of the first 43 failed files in the sorted v1.7.0 public audit, pinned to commit `c3ac31b`. Fifteen definitions changed; fourteen now complete their saved default run and twenty-nine still fail. The labor-market definition received a partial syntax/alias repair and still fails at initialization. No empirical calibration is claimed.

The [portable receipt](../operations/corpus-repairs-v18-b.json) contains each exact original JSON text, its SHA-256, current SHA-256, changed fields, baseline and saved current default/half-step/quarter-step probes, bounded independent-integration probes, fresh current default results, engine hashes, source scope and remaining evidence gaps. Every original text was checked against `git show c3ac31b:<file>`. All stock, flow, variable and connector IDs, positions and counts remain intact; start, end and output spacing remain unchanged.

The saved exploratory DOP853 probe independently integrates the engine-evaluated RHS, so it tests integration rather than equation transcription. Its 6,000-evaluation cap is an inconclusive limit, not evidence of finite-time blowup or invalid continuous dynamics. Some saved direct traces deliberately exercise Euler even after a definition selected Radau; the receipt labels those diagnostic traces. The fresh default result records the selected method. The originating engine hashes of the older exploratory probes were not saved; this limitation is explicit rather than attributed retrospectively. Unseeded exploratory probes use a diagnostic seed of 42 without inserting it into the definitions.

## Verified repairs and their limits

World2 is the one primary-source RHS reconstruction. The original [MIT archive document](https://dome.mit.edu/bitstream/handle/1721.3/189645/39080024064039.pdf?isAllowed=y&sequence=1), PDF pages 82–91, contains the July 1970 D-1354 documentor. All ten pages were visually inspected. Its twenty-two TABHL curves, birth/death normals 0.045/0.025 and initial agricultural fraction 0.3 replace the generated linear placeholders. The native capital-generation curve CIPC = [0.005, 0.05, 0.09, 0.12, 0.14, 0.15] is represented by the existing normal 0.05 times CIM = [0.1, 1, 1.8, 2.4, 2.8, 3]. The pre/post-1970 coefficients in this source run are equal. Every table and the five-stock RHS has a separate handwritten test; a tighter independent Radau trajectory agrees at all 201 annual samples. This does not claim a native DYNAMO replay, a later World2 variant, or a validated present-day forecast.

The two DICE quantity repairs use the [native DICE2016R GAMS listing](https://www.gams.com/latest/docs/apis/examples_python/nordhausdice_8py_source.html): capital is in trillions of 2010 USD, carbon stocks are GtC and industrial emissions are GtCO2/year. Carbon mass conversion is 12/44. The four-stock variant uses the source 588 GtC preindustrial reference and logarithmic doubling forcing. These remain simplified local adaptations, without native optimization or source-matched full carbon/climate dynamics.

The ice-albedo radiation repair follows the [NIST Stefan–Boltzmann units](https://physics.nist.gov/cgi-bin/cuu/Value?sigma%7Csearch_for=stefan+boltzmann) and the [exact Celsius/kelvin offset](https://www.nist.gov/pml/owm/si-units-temperature). The existing rounded 5.67e-8 constant already produces W/m²; removing a million-fold divisor restores compatible flux units. No calibration parameter is invented.

Other completed changes recover a unique alias, remove a duplicated dimensional factor, supply a mathematically unique origin limit, analytically eliminate an existing algebraic loop, or explicitly select Radau for a positive continuous ODE that saved Euler overshoots. Those operations preserve identified local mathematics; they do not establish that the local mathematics reproduces a cited publication. In particular NPZ still loses unassimilated grazing from the three compartments; Bartlett is deterministic rather than a stochastic fade-out reproduction; and the within-host model has no verified clinical source.

## Complete case record

“Complete” below means a finite saved default trajectory, with the additional tests described where applicable. “Failed” preserves the actual failure and unresolved evidence; no denominator floor, fabricated forcing, guessed initialization or automatic timestep/solver change was used. Stored conceptual citations are included for provenance, and are explicitly not treated as executable equation evidence.

### 0. Beer Distribution Game

`models/classic/beer-distribution-game-cla.json` — **Failed; unchanged.**

Inventory/supply-line adjustment quantities and Production_Order are undeclared, and the extraction omits shipment/fulfillment dynamics. A source reference to the Beer Game does not supply those missing equations.

**Remaining evidence:** Original executable Beer Game structure and author-confirmed adaptation/wiring are missing.

**Run:** Retailer Orders: unknown_variable; Production: unknown_variable. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.1287/mnsc.35.3.321): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 1. World2 Forrester Original Model

`models/classic/world2-forrester-original-cla.json` — **Complete; changed.**

Unbounded substituted linear feedbacks did not implement World2. The primary 1970 D-1354 documentor supplies 22 TABHL curves, .045/.025 birth/death normals and initial agricultural fraction .3. All curves and source RHS are restored; Radau resolves the source ODE on the saved annual output grid.

**Remaining evidence:** No native DYNAMO trajectory was rerun. This verifies the 1970 source RHS, not a contemporary empirical forecast or the later 1973 variant.

**Run:** 201 retained samples; selected method `radau`. Historical source RHS verified only; no contemporary empirical calibration.

**Evidence scope:** [Source 1](https://dome.mit.edu/bitstream/handle/1721.3/189645/39080024064039.pdf?isAllowed=y&sequence=1): Primary 1970 D-1354 documentor, PDF pp. 82–91 visually checked; all 22 tables and RHS checked; not native DYNAMO trajectory. [Source 2](https://mitpress.mit.edu/9780262560047/world-dynamics/): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 2. World3 Non-Renewable Resources Sector

`models/classic/world3-non-renewable-resources-sector-cla.json` — **Failed; unchanged.**

Resource Usage Multiplier calls a source-like table at Industrial_Output_Per_Capita, but that input is not declared in this isolated resource subsystem. Missing table/input adaptation prevents evaluation.

**Remaining evidence:** Full coupled World3 sector definition, input per-capita output and correct versioned lookup mapping are needed.

**Run:** Resource Usage Multiplier: unknown_function; Resource Extraction Capital Requirement: unknown_function. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.1016/B978-0-12-850754-3.50020-2): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 3. Agricultural Water Demand Model

`models/climate/agricultural-water-demand-cli.json` — **Complete; changed.**

Time Step=1 is an independently authored reservoir-withdrawal period and collides with reserved TIME_STEP while solver dt=.25. Descriptive renaming and exact references preserve its existing value and separate the physical period from the integration grid.

**Remaining evidence:** Reservoir/crop coefficients and original agricultural source remain uncalibrated.

**Run:** 241 retained samples; selected method `euler`. Not established; stated local mathematical/numerical repair only.

**Evidence scope:** [Source 1](https://github.com/SDXorg/PySD-Cookbook): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 4. Arctic Sea Ice Decline Model

`models/climate/arctic-sea-ice-decline-model-cli.json` — **Failed; unchanged.**

The melt equation uses undeclared feedback_amplification. No unique numeric feedback parameter exists to recover from the local file.

**Remaining evidence:** A cited empirical sea-ice study or original executable must identify the omitted coefficient and its units; do not invent it.

**Run:** ice_melt: unknown_variable. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://github.com/SDXorg/PySD-Cookbook): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 5. DICE Integrated Assessment Model (Simplified)

`models/climate/dice-integrated-assessment-model-simplified-cli.json` — **Complete; changed.**

Capital 223e12 mixed dollar and trillion-dollar source quantities; emissions mixed GtCO2 with GtC stocks. Native DICE2016R supports K=223 trillion 2010USD, carbon stock units and 12/44 conversion. Those units are repaired; explicit Radau resolves the local continuous temperature response on the existing five-year grid.

**Remaining evidence:** The local carbon exchange, climate feedback, exogenous growth and SCC are simplified adaptations. Native DICE optimization/scientific fidelity is not established.

**Run:** 18 retained samples; selected method `radau`. Not established; stated local mathematical/numerical repair only.

**Evidence scope:** [Source 1](https://www.gams.com/latest/docs/apis/examples_python/nordhausdice_8py_source.html): Native DICE2016R GAMS quantities: KtrillionUSD,k 0=223; MAT 851/MU 460/ML 1740/CCA inGtC; emissionsGtCO2/year; carbon mass conversion. [Source 2](https://github.com/SDXorg/PySD-Cookbook): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 6. Humidity

`models/climate/forest-fire-spread-cli.json` — **Failed; unchanged.**

Fuel consumption continues at positive active-fire demand when Fuel_Load approaches 0; Fuel_Load crosses negative near t 6. Negative fuel changes spread/residence signs, eventually driving active area below 0 and invalidating SQRT. The bounded continuous reference also reaches a domain failure.

**Remaining evidence:** Need source fuel units, finite-fuel consumption boundary and fire-spread/residence law. A positivity clamp or smaller dt alone is not a source repair.

**Run:** Perimeter_Length: domain_error. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.2737/INT-RP-115): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 7. Global Carbon Cycle Model

`models/climate/global-carbon-cycle-model-cli.json` — **Failed; unchanged.**

Airborne Fraction is undefined at initial zero cumulative emissions. Additional absent Ocean_pCO2, outgassing and temperature-effect quantities prevent full carbon-cycle evaluation.

**Remaining evidence:** Need original carbon-cycle equations/lookup data and an explicit reporting convention at zero cumulative emissions.

**Run:** Airborne Fraction: division_by_zero; Fossil Fuel Emissions: unknown_function; Photosynthesis (GPP): unknown_variable; Ocean CO2 Uptake: unknown_variable. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.2307/j.ctt3fgxqx): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 8. Global Food Security Model

`models/climate/global-food-security-cli.json` — **Failed; unchanged.**

All stocks initialize 0; Cropland_Expansion divides the 0 food gap by 0 Average_Yield. The cited crop-yield study does not initialize this generated five-stock system.

**Remaining evidence:** Recover source/country/scale-specific land,yield,demand and production initial conditions; no arbitrary positive yield floor.

**Run:** Cropland_Expansion: division_by_zero. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.1371/journal.pone.0066428): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 9. Global Nitrogen Cycle Model

`models/climate/global-nitrogen-cycle-model-cli.json` — **Failed; unchanged.**

Industrial fixation is declared twice: a flow at 0 and an auxiliary at 120. The case-insensitive scalar language correctly refuses two equations for one symbol.

**Remaining evidence:** Need source mapping of fixation coefficient versus actual stock-changing flow, including units and intended equation.

**Run:** name_collision. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://github.com/SDXorg/PySD-Cookbook): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 10. Global Tipping Points 2023 Assessment Model

`models/climate/global-tipping-points-2023-assessment-cli.json` — **Failed; unchanged.**

Ice Albedo Feedback=.03*(1.5-T) becomes negative above 1.5, so the outgoing Sea Ice Loss flow instead grows ice. Ice above its fraction range reverses the warming feedback, leading to unbounded signed dynamics. A bounded explicit reference exhausted its evaluation allowance rather than validating this closure.

**Remaining evidence:** Need original tipping-element state definitions, calibrated feedback signs and domains. Budget exhaustion does not prove either solution existence or finite-time blowup.

**Run:** Sea Ice Loss: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://global-tipping-points.org/): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 11. Ice-Albedo Feedback Model

`models/climate/ice-albedo-feedback-model-cli.json` — **Complete; changed.**

Stefan_Boltzmann=5.67e-8 returns W/m² when multiplied by kelvin^4, matching absorbed flux. Dividing by 1e6 destroyed that balance. Remove that divisor and use the exact 273.15 Celsius offset; keep other coefficients and the authored grid.

**Remaining evidence:** No original executable energy-balance adaptation or calibration of heat capacity/ice response has been identified.

**Run:** 201 retained samples; selected method `euler`. Not established; stated local mathematical/numerical repair only.

**Evidence scope:** [Source 1](https://physics.nist.gov/cgi-bin/cuu/Value?sigma%7Csearch_for=stefan+boltzmann): Stefan-Boltzmann constant unitsW m^-2 K^-4; retain authored rounded 5.67e-8 value. [Source 2](https://www.nist.gov/pml/owm/si-units-temperature): Exact Celsius/kelvin offset 273.15. [Source 3](https://github.com/SDXorg/PySD-Cookbook): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 12. Nordhaus DICE Integrated Assessment Model

`models/climate/nordhaus-dice-integrated-assessment-cli.json` — **Complete; changed.**

Atmospheric 851 is a GtC stock, not ppm. Native DICE2016R identifies preindustrial 588GtC and logarithmic doubling forcing, and emits GtCO2/year. Correct the forcing ratio/logarithm and convert emissions by 12/44.

**Remaining evidence:** The four-stock adaptation omits native restoring/carbon-cycle terms and optimization. Correct units do not certify DICE source fidelity or SCC accuracy.

**Run:** 37 retained samples; selected method `euler`. Not established; stated local mathematical/numerical repair only.

**Evidence scope:** [Source 1](https://www.gams.com/latest/docs/apis/examples_python/nordhausdice_8py_source.html): DICE2016R MAT 851GtC,preindustrialMATEQ 588GtC,logarithmic doubling forcing and emissionscarbon conversion. [Source 2](https://doi.org/10.1073/pnas.1609244114): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 13. Ocean Heat Content Dynamics Model

`models/climate/ocean-heat-content-dynamics-cli.json` — **Failed; unchanged.**

Transfer rates multiply a heat stock by 1-stock/capacity; above capacity they reverse direction instead of relaxing a layer temperature difference. The intermediate layer becomes negative. The continuous reference fails near 22.74, supporting a malformed/domain-limited heat closure rather than a purely coarse-grid explanation.

**Remaining evidence:** Need source heat/temperature units, conservative interlayer exchange and surface heat-loss equations.

**Run:** Surface_Intermediate_Transfer: non_finite_result; Intermediate_Deep_Transfer: non_finite_result; Ocean_Heat_Release: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.1126/science.aav7619): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 14. Phosphorus Lake Eutrophication Model

`models/climate/phosphorus-lake-eutrophication-cli.json` — **Failed; unchanged.**

Anoxia amplifies sediment release as algae grows. At t 54 the saved Euler removal 117.0 exceeds sediment 8.52 plus deposition 14.42 over one step, emptying sediment below 0. A bounded explicit reference hits 6000 evaluations; that alone does not establish continuous-solution validity.

**Remaining evidence:** A verified stiff reference, algae/phosphorus stoichiometry and original nutrient accounting are still needed before choosing a solver or changing dynamics.

**Run:** Sediment Release: non_finite_result; Algae Growth: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://heronetnext.epa.gov/reference/37262/): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 15. Sea Level Rise and Ice Sheet Dynamics Model

`models/climate/sea-level-rise-and-ice-sheet-dynamics-model-cli.json` — **Failed; unchanged.**

CO2_Scenario is an undeclared function/table, with many incomplete temperature/ice/sea-level aliases. The generic Cookbook citation does not supply its forcing points.

**Remaining evidence:** Recover actual scenario data and source equations with a complete symbol/unit mapping.

**Run:** CO2 Concentration: unknown_function; Ice-Albedo Feedback (Greenland): unknown_variable; Greenland Sea Level Contribution: unknown_variable; Marine Ice Sheet Instability Factor: unknown_variable. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://github.com/SDXorg/PySD-Cookbook): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 16. Solar Irradiance and Climate Model

`models/climate/solar-irradiance-and-climate-model-cli.json` — **Failed; unchanged.**

TSI is undeclared in the solar-forcing equation. No local time series or forcing table defines the missing irradiance input.

**Remaining evidence:** Recover the original irradiance series, units, time alignment and baseline rather than fabricate a sinusoid or constant.

**Run:** solar_forcing: unknown_variable. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** No identified original source: Unverified illustrative solar/climate stock-flow definition. Previous DOI 10.1038/nature 14240 is Feldman et al.2015, Observational determination of surface radiative forcing by CO2 from 2000 to 2010; it is not the source of this solar-cycle model. Missing TSI and heat-budget equations unresolved.

### 17. Sustainable Agriculture Transition Model

`models/climate/sustainable-agriculture-transition-cli.json` — **Failed; unchanged.**

All farm compartments start 0, giving 0/0 in peer-adoption via Total_Farms. No native adaptation supplies farm composition.

**Remaining evidence:** Author/source initial compartment totals and soil state are required; no invented farm count or denominator floor.

**Run:** Transition_Start: division_by_zero. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.1038/s41893-018-0114-0): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 18. Recycling_Inflow

`models/economics/aluminum-supply-chain-sustainability-eco.json` — **Failed; unchanged.**

Rapid accumulated revenue/investment makes Decarbonization_Progress exceed 1 and turns gross emissions negative; emissions become negative by t 2. Abatement gain also grows without bound. Explicit reference budget exhaustion is not evidence for a corrected source model.

**Remaining evidence:** Need annual production versus accumulated-stock units, investment/abatement law, emissions boundary and original parameter scale.

**Run:** Emission_Reduction: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.3390/su16208892): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 19. Brand Loyalty Dynamics

`models/economics/brand-loyalty-dynamics-eco.json` — **Failed; unchanged.**

Brand Equity=2*Loyal_Customers causes churn to reverse above 50 loyal customers. The flow's endpoint also couples a rate based on loyal users to trial users, which become negative. Continuous integration encounters a singular growth regime near 26.15.

**Remaining evidence:** Need the source customer-accounting topology and a calibrated nonnegative churn law; no arbitrary cap.

**Run:** Churn: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://systemdynamics.org/resources/): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 20. Common Value Auction Model

`models/economics/common-value-auction-eco.json` — **Complete; changed.**

Bidder experience grows the relaxation coefficient, eventually taking dt*gain beyond Euler's stable range. Tight independent integration of the unchanged authored RHS remains bounded. Explicit Radau fixes numerical execution with the same saved output times.

**Remaining evidence:** The learning ODE and parameters remain an illustrative adaptation, not a verified Milgrom-Weber auction model.

**Run:** 101 retained samples; selected method `radau`. Not established; stated local mathematical/numerical repair only.

**Evidence scope:** [Source 1](https://doi.org/10.2307/1911865): Stored conceptual/source reference; equation fidelity is not inferred from citation identity. [Source 2](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html): Numerical method only; independent handwritten authored RHS tests do not establish empirical source fidelity.

### 21. Coral Reef Bleaching and Recovery Dynamics

`models/economics/coral-reef-bleaching-and-recovery-dynamics-eco.json` — **Failed; unchanged.**

Stress recovery has rate 12 with dt.25, giving Euler amplification 1-3=-2; thermal stress first crosses negative in 2005.75. Subsequent bleaching/recruitment feedback diverges. The bounded explicit reference does not complete the full horizon.

**Remaining evidence:** Need a verified continuous/DDE ecological reference, source calibration and response domains before numerical or structural changes.

**Run:** Recovery Potential: non_finite_result; Coral Recruitment: non_finite_result; Algae Grazing: non_finite_result; Herbivore Population Growth: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://github.com/SDXorg/test-models): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 22. Cybersecurity Threat Landscape Model

`models/economics/cybersecurity-threat-landscape-eco.json` — **Complete; changed.**

The attack flow equals rate*A²/(A+D) for nonnegative threatsA and defenseD; it lies between 0 and rate*A. Its unique origin limit is 0. An explicit conditional supplies only that mathematically forced value, leaving positive-domain arithmetic unchanged.

**Remaining evidence:** DBIR is observational background and does not calibrate this generated threat/defense dynamic model.

**Run:** 209 retained samples; selected method `euler`. Not established; stated local mathematical/numerical repair only.

**Evidence scope:** [Source 1](https://www.verizon.com/business/resources/reports/dbir/): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 23. DMP Search and Matching Model

`models/economics/dmp-search-matching-eco.json` — **Complete; changed.**

Euler overshoots unemployment below 0, making the fractional matching function non-real. The continuous positive matching ODE has a fast near-zero-unemployment timescale. Explicit Radau and an independently written RHS preserve the positive trajectory on the saved grid.

**Remaining evidence:** The wage/vacancy closure and numeric coefficients are not a verified Mortensen-Pissarides equilibrium implementation.

**Run:** 401 retained samples; selected method `radau`. Not established; stated local mathematical/numerical repair only.

**Evidence scope:** [Source 1](https://doi.org/10.2307/2297896): Stored conceptual/source reference; equation fidelity is not inferred from citation identity. [Source 2](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html): Numerical method only; independent handwritten authored RHS tests do not establish empirical source fidelity.

### 24. Labor Market Dynamics Model

`models/economics/labor-market-dynamics-model-eco.json` — **Failed; changed.**

The unmatched Vacancy Creation parenthesis and unique worker/entry/fraction aliases are repaired. All population/wage stocks still initialize 0, so labor-force and matching ratios remain undefined at t 0.

**Remaining evidence:** The unused Initial... auxiliaries do not specify every omitted stock initializer. Recover actual source cohort/wage initialization and equation mapping.

**Run:** Unemployment Rate: division_by_zero; Labor Force Participation Rate: division_by_zero; Vacancy Rate: division_by_zero; Labor Market Tightness: division_by_zero. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://github.com/SDXorg/test-models): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 25. Marine Fishery Maximum Sustainable Yield

`models/economics/marine-fishery-msy-eco.json` — **Complete; changed.**

Profit/Cost already has vessel units because Cost is per-vessel annual expense. Multiplying by Fishing_Fleet again made exit quadratic in vessels and removed the fleet in the first Euler step. Removing that duplicate factor restores the local vessel/time dimensional balance.

**Remaining evidence:** Response-rate calibration, full bioeconomic unit provenance and exact Clark source-equation fidelity remain unverified.

**Run:** 201 retained samples; selected method `euler`. Not established; stated local mathematical/numerical repair only.

**Evidence scope:** [Source 1](https://www.wiley-vch.de/en/areas-interest/mathematics-statistics/mathematics-16ma/applied-mathematics-16ma2/computational-biology-16ma23/mathematical-bioeconomics-978-0-470-37299-9): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 26. Market Share Competition Model

`models/economics/market-share-competition-model-eco.json` — **Failed; unchanged.**

Quality Investment 10m produces Quality 1,000,100 and huge switching gain. The saved share rises to 106.28 at the first quarter-step and then turns negative; customer/experience feedback eventually makes a fractional learning power non-real. Explicit reference hits its 6000-call cap before reaching the horizon.

**Remaining evidence:** Need a tight bounded stiff reference and verified quality/advertising units and accounting. A failed explicit reference does not prove no valid continuous solution exists.

**Run:** Unit Cost Firm A: non_real_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://github.com/SDXorg/test-models): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 27. NPZ Ocean Ecosystem Model

`models/economics/npz-ocean-ecosystem-eco.json` — **Complete; changed.**

The positive-domain NPZ rates deplete nutrient too rapidly for saved Euler dt 1. Explicit Radau preserves the unchanged local equations. Summed nutrient changes by-(1-gamma)*grazing, so unassimilated grazing is an unresolved export/loss, not silently recycled.

**Remaining evidence:** Determine whether unassimilated grazing represents deliberate export or omitted closed-cycle recycling; exact Franks source set and empirical calibration remain missing.

**Run:** 366 retained samples; selected method `radau`. Not established; stated local mathematical/numerical repair only.

**Evidence scope:** [Source 1](https://doi.org/10.1023/A:1015874028196): Stored conceptual/source reference; equation fidelity is not inferred from citation identity. [Source 2](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html): Numerical method only; independent handwritten authored RHS tests do not establish empirical source fidelity.

### 28. Two-Sided Platform Network Effects Model

`models/economics/platform-network-effects-advanced-eco.json` — **Failed; unchanged.**

Perceived user/provider values can exceed their 50/25 scales, reversing churn into acquisition. Value and two-sided network feedback then grow without a market boundary; competitor users become negative near 69.5. The bounded explicit reference exhausts its allowance.

**Remaining evidence:** Need original market/churn domains and a verified continuous reference; no source-backed saturation coefficient or clamp is available.

**Run:** Transaction Flow: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.1257/jep.23.3.125): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 29. R&D Investment and Innovation Dynamics

`models/economics/rd-investment-innovation-eco.json` — **Failed; unchanged.**

Knowledge creation multiplies personnel,sqrt(capital),and growing knowledge, then feeds patents/products/revenue/capital. This superlinear reinforcing loop overflows without an identified limiting mechanism; the explicit reference exhausts its 6000 evaluations near 7.28.

**Remaining evidence:** Need source R&D/revenue units, limiting mechanisms and a verified long-horizon reference. Evaluation-budget exhaustion is not a proof of finite-time blowup.

**Run:** Knowledge Creation: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://github.com/SDXorg/test-models): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 30. Real Business Cycle Model (Basic)

`models/economics/real-business-cycle-basic-eco.json` — **Failed; unchanged.**

Technology_Shock integrates positive rho*log deviation as a derivative, turning a discrete persistence parameter into unstable continuous amplification; output is also accumulated production. The reference cannot establish the intended RBC law.

**Remaining evidence:** Recover the discrete-time technology process or a dimensionally derived continuous-time adaptation. Do not invent a negative reversion sign or rescale rho.

**Run:** Production: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.2307/1913386): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 31. Semiconductor Chip Shortage Supply Chain Model

`models/economics/semiconductor-chip-shortage-supply-chain-eco.json` — **Failed; unchanged.**

Panic ordering grows linearly with backlog, while desired capacity multiplies current capacity by backlog. This creates unbounded reinforcement; inventory/fulfillment constraints and the intended demand process are not source-verified. The explicit reference hits its work cap.

**Remaining evidence:** Need a source demand/production/inventory system and independently verified continuous dynamics; do not infer a saturation or arbitrary gain.

**Run:** Desired_Capacity: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://www.ecb.europa.eu/press/economic-bulletin/focus/2021/html/ecb.ebbox202104_06~780de2a8fb.en.html): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 32. Startup Ecosystem Dynamics Model

`models/economics/startup-ecosystem-dynamics-eco.json` — **Failed; unchanged.**

Funding deployment persists after available funding reaches 0 (crossing at t 2.5), then the founding denominator approaches/crosses-10000. Startups can fall below-1, invalidating LOG(1+startups); the continuous reference also reaches a domain error.

**Remaining evidence:** Need financing/availability and talent accounting boundaries with units and an original source. No floor or capped hiring is invented.

**Run:** Ecosystem Support: domain_error. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.1002/9781119204459): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 33. Sterman Commodity Cycles Ch20

`models/economics/sterman-commodity-cycles-ch20-eco.json` — **Complete; changed.**

Demand and Market Price were an instantaneous algebraic loop. The two positive-domain authored relations can be eliminated exactly: D=D 0*(MAX(1,Inventory)/(Coverage*D 0))^(e/(1+e)). This removes the loop without inventing a lag or changing its existing inventory floor.

**Remaining evidence:** The closed form requires positive coverage and e>-1. No original Sterman chapter 20 executable or calibration has been matched.

**Run:** 401 retained samples; selected method `euler`. Not established; stated local mathematical/numerical repair only.

**Evidence scope:** [Source 1](https://web.mit.edu/jsterman/www/BusDyn2.html): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 34. Subscripted Population Model (Massachusetts Towns)

`models/economics/subscripted-population-model-massachusetts-towns-eco.json` — **Failed; unchanged.**

The local initial population list contains an ellipsis, Towns dimensions are missing and a four-argument DELAY is outside the supported scalar dialect. The original native source has 351 town values and subscript semantics.

**Remaining evidence:** Need a complete array-aware import/engine and preserved dimension/member mapping. A scalar population or guessed truncated list is not equivalent.

**Run:** Initial Population: unsupported_expression; Births: unsupported_expression; Deaths: equation_error. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://github.com/SDXorg/test-models): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 35. Trophic Cascade Ecosystem Model

`models/economics/trophic-cascade-ecosystem-eco.json` — **Failed; unchanged.**

Predation terms remove mesopredators/herbivores independently of their remaining prey. At zero prey the derivative can remain negative; mesopredators cross below 0 near 2.25. A continuous reference also fails near 7.77, so this is not repaired by selecting a stiff method alone.

**Remaining evidence:** Need a verified trophic-response/predation law, unit scales and source boundary behavior.

**Run:** Herb_Growth: non_finite_result; Veg_Growth: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.1016/j.biocon.2011.11.005): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 36. Limits to Growth System Archetype Model

`models/education/limits-to-growth-system-archetype-edu.json` — **Failed; unchanged.**

System State returns Growing/Constrained/At Limit strings from a numeric scalar equation. The engine correctly refuses that unsupported value type.

**Remaining evidence:** Need a source/author-approved numeric status encoding or a separate categorical reporting feature. Do not silently replace labels by 0.

**Run:** System State: unsupported_expression. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://www.penguinrandomhouse.com/books/163984/the-fifth-discipline-by-peter-m-senge/): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 37. Online Learning Platform Model

`models/education/online-learning-platform-edu.json` — **Failed; unchanged.**

Content quality grows beyond its reference 100, making Late_Dropout negative. Dropped_Out crosses below 0 near 26.25 and reverse dropout plus enrollment/quality feedback diverges. The explicit reference exhausts its allowance.

**Remaining evidence:** Need original dropout/quality domains and learning-platform accounting; no source supports a clamp or arbitrary saturation.

**Run:** Learner_Activation: non_finite_result; Late_Dropout: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.1145/2460296.2460330): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 38. Grid Frequency Stability Dynamics

`models/energy/grid-frequency-stability-ene.json` — **Failed; unchanged.**

Inertial Response drains stored kinetic energy while Frequency Change divides by it. Energy reaches 0 near 23.42 in continuous reference and crosses negative in saved Euler near 23.44, so the frequency singularity is present in the authored closure.

**Remaining evidence:** Need a physically derived energy/frequency balance, units and source reserve response; no denominator epsilon or invented replenishment.

**Run:** Reserve Deployment: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.1109/TPWRS.2018.2821757): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 39. Age-Structured Epidemic Model

`models/epidemiology/age-structured-epidemic-who-epi.json` — **Complete; changed.**

Daily Euler infection can remove more susceptibles than a compartment holds, creating negative susceptible stocks. The unchanged positive two-age SIR ODE conserves each age group and is resolved by explicit Radau with independent RHS/mass checks.

**Remaining evidence:** The hard-coded contact matrix, reciprocity, parameters and empirical interpretation remain unverified against Mossong data.

**Run:** 181 retained samples; selected method `radau`. Not established; stated local mathematical/numerical repair only.

**Evidence scope:** [Source 1](https://doi.org/10.1371/journal.pmed.0050074): Stored conceptual/source reference; equation fidelity is not inferred from citation identity. [Source 2](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html): Numerical method only; independent handwritten authored RHS tests do not establish empirical source fidelity.

### 40. Bartlett Measles Fade-Out Model

`models/epidemiology/bartlett-measles-fade-out-epi.json` — **Complete; changed.**

Birth Rate=Population/(70*365) is already persons/day. Births multiplied by Population again, producing persons²/day and explosive growth. Use the existing absolute flow directly; preserve all demographic coefficients.

**Remaining evidence:** The file remains deterministic, not Bartlett's stochastic fade-out process; initial cohort totals differ from the fixed population parameter and calibration is unverified.

**Run:** 731 retained samples; selected method `euler`. Not established; stated local mathematical/numerical repair only.

**Evidence scope:** [Source 1](https://doi.org/10.2307/2342553): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

### 41. SARS-CoV-2 Viral Load Dynamics

`models/epidemiology/covid19-sars-cov2-viral-dynamics-epi.json` — **Complete; changed.**

Immune-mediated infected-cell removal becomes fast relative to Euler dt.1, making infected cells negative near 4.3 and causing later overflow. Explicit Radau and a handwritten positive-domain RHS resolve the unchanged local equations.

**Remaining evidence:** The earlier clinical/Ke citation was unrelated and withdrawn; no source supports the local inoculum, target-cell scale, rates or SARS-CoV-2 calibration.

**Run:** 301 retained samples; selected method `radau`. Not established; stated local mathematical/numerical repair only.

**Evidence scope:** No identified original source: Unverified illustrative within-host viral-dynamics model; no identified source for the implemented equations or parameters. [Source 2](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html): Numerical method only; independent handwritten authored RHS tests do not establish empirical source fidelity.

### 42. Delay-Differential SEIR Model

`models/epidemiology/delay-differential-seir-epi.json` — **Failed; unchanged.**

Default DELAY history uses initial input rates. Initial exposed 100/infectious 10 are not matched to complete incubation/infectious cohort histories; delayed removal exceeds infectious stock near t 70. Half/quarter Euler also fail. This is a DDE/history issue, not an ODE Radau candidate.

**Remaining evidence:** Recover original history functions, compartment initial compatibility and delay-time semantics from the DDE source.

**Run:** Exposure Rate: non_finite_result. Full structured failure and blocked dependents are in the receipt.

**Evidence scope:** [Source 1](https://doi.org/10.1038/s41598-023-40008-9): Stored conceptual/source reference; equation fidelity is not inferred from citation identity.

## Verification

`python -m pytest -q tests/test_corpus_repairs_v18_b.py`: **23 passed**. Tests cover all 43 receipt hashes and preserved product elements, fourteen finite defaults, quantity counterexamples, the exact cybersecurity zero limit, commodity algebraic identity, five independently handwritten ODE references, two-age mass conservation, the unresolved NPZ loss term, all twenty-two World2 curves and the independently written World2 RHS. The DMP reference evaluates the exact positive-domain square roots without a numerical clamp.

The combined historical/new B suites also pass: `python -m pytest -q tests/test_corpus_partition_b_v17.py tests/test_corpus_repairs_v18_b.py` — **31 passed**.

No production definitions were accessed or changed as part of this handoff. No public push or deployment was performed.
