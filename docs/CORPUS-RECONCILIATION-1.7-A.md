# Corpus reconciliation 1.7 — partition A

Reviewed all45 baseline failures whose index modulo3 is0 after sorting by file. The baseline is `operations/library-full-v160.json`, pinned to `c99c022fe630388be5cf1c16bd0ac79a156a8969`. No assigned case was omitted.

Fourteen saved definitions changed: two native-source restorations and twelve explicit local identifier translations. Thirteen defaults now complete numerically; one of those is the unmodified Morris–Lecar shell with no derivative flows, so it remains an incomplete model. Thirty-two defaults still fail. None is claimed scientifically validated. The manifest records each original/current SHA256, every changed field, source access/registration evidence, full default/half-step/quarter-step diagnostics and unresolved next steps.

No stock initial value, numeric coefficient, flow endpoint, node ID, node name, position, existing connector or saved time control changed. No denominator replacement, positivity clamp, guessed forcing curve, arbitrary time-step change, silent loop solution or string-to-number substitution was introduced.

## Bounded capacity

The old10,000-interval ceiling rejected a genuine native12800-interval pendulum default. The backend, investigation tool, analytics and MCP now support at most100,000 intervals/100,001 retained samples,500 elements,1,000,000 retained scalar values including the initial sample, and1,000,000 work units. The existing work accounting includes hidden delay/smooth stages, stochastic calls and five evaluations per RK4 interval. The root agent aligned browser validation and analytics. The independent sample ceiling bounds long scalar-response payloads; the retained-value/work budgets remain stricter for larger or more expensive models. Saved equations, methods, horizons and grids are preserved.

This also admits the40000-interval Morris–Lecar definition. Its two stocks are constant because it has no flows; the receipt explicitly flags that outcome instead of claiming a neuron repair.

## Original implementations recovered

- [Native workforce model](https://raw.githubusercontent.com/SDXorg/test-models/21aab02739dc5187bc9564e4d3de14e575905d2f/samples/Workforce/workforce.mdl): seven original hiring-lookup knots, clamped linear interpolation and punctuated hour references. Existing inputs and all4801 output times are preserved; an independent literal source recurrence checks stocks and rates across the entire grid. No native CSV was present in this sample folder.
- [Native double pendulum](https://raw.githubusercontent.com/SDXorg/PySD-Cookbook/d7ebddadad9cd87cf796b9b6031ea2b5c45da4c4/source/models/Pendulum/Double_Pendulum.mdl): explicit source-symbol translation and support for the original1/128-second grid over100 seconds. An independent four-state source Euler recurrence checks all12801 samples. Large energy drift and chaotic timestep sensitivity remain. Source-equation agreement is not an accurate mechanical trajectory claim.

The [Baby Names sketch](https://raw.githubusercontent.com/SDXorg/PySD-Cookbook/d7ebddadad9cd87cf796b9b6031ea2b5c45da4c4/source/models/Baby_Names/Baby_Names.mdl) contains placeholders rather than recoverable equations. The [subscripted population original](https://raw.githubusercontent.com/SDXorg/PySD-Cookbook/d7ebddadad9cd87cf796b9b6031ea2b5c45da4c4/source/models/Subscripted_Population/Subscripted%20Population%20Model.mdl) requires351 town populations and array/delay semantics. Both remain unresolved; a scalar fallback would discard their source meaning.

## Every assigned model

Status means numerical execution of the saved default. Original/source fidelity and calibration remain separate. Explicit local name translations use only already-declared quantities; a broad paper/book/repository citation does not authenticate a generated adaptation.

### 1. beer-distribution-game-cla

**failed** · Unresolved; definition unchanged.

Seven undeclared inventory/supply-line correction quantities and Production_Order; inventories/backlog lack shipment/fulfillment paths. Sterman's beer-game article supports the stock-management context, not these omitted equations. Need original executable structure; supplying zero correction factors would change behavior.

Original reference: [cited source](https://doi.org/10.1287/mnsc.35.3.321).

### 2. world3-food-production-cla

**completed** · Local identifier repair; source implementation unresolved.

Capital_Effect is undeclared; the only declared development multiplier is Capital Effect on Development. Explicit token mapping fixes local evaluation. The simplified subsystem, inputs and World3 provenance are not a reproduction of a recovered original.

Original reference: [cited source](https://doi.org/10.1016/B978-0-12-850754-3.50020-2).

Full-horizon successful probes: dt=1: 201 samples; dt=0.5: 401 samples; dt=0.25: 801 samples.

Maximum scaled stock differences across successive grids: 0.000791091, 0.000389287. These are numerical sensitivity observations, not source validation.

### 3. agricultural-water-demand-cli

**failed** · Unresolved; definition unchanged.

Authored auxiliary Time Step=1 collides with reserved TIME_STEP, while configured dt=.25. These are different values. Renaming or choosing one requires clarifying whether this quantity is a physical availability time or integration control; leave unchanged rather than silently choosing1 or.25.

Original reference: [cited source](https://github.com/SDXorg/PySD-Cookbook).

### 4. energy-system-transition-model-cli

**completed** · Local identifier repair; source implementation unresolved.

Thirteen shorthand identifiers differ from complete local declared names. Explicit mapping repairs those references. Renewable Capacity Investment feeds Cumulative Renewable Deployment but does not feed Renewable Energy Capacity; do not invent the missing link from a conceptual repository URL. Numerical/source integrity remains separate.

Original reference: [cited source](https://github.com/SDXorg/PySD-Cookbook).

Full-horizon successful probes: dt=1: 81 samples; dt=0.5: 161 samples; dt=0.25: 321 samples.

Maximum scaled stock differences across successive grids: 0.274449, 0.0800701. These are numerical sensitivity observations, not source validation.

### 5. global-food-security-cli

**failed** · Unresolved; definition unchanged.

All five stocks initialize to0; Cropland_Expansion divides0/0 by Average_Yield. Ray et al. is an empirical yield-trend analysis, not a source for this five-stock model or initial conditions. Original/calibrated stock initializers needed.

Original reference: [cited source](https://doi.org/10.1371/journal.pone.0066428).

### 6. ice-albedo-feedback-model-cli

**failed** · Unresolved; definition unchanged.

Outgoing_Radiation divides Stefan-Boltzmann power by1e6 while Absorbed_Radiation remains hundreds, creating inconsistent apparent energy units; negative/unbounded ice and temperature follow. No matching original source file exists in the cited Cookbook checkout. Need unit/time system and physical equations, not an arbitrary radiative multiplier or clamp.

Original reference: [cited source](https://github.com/SDXorg/PySD-Cookbook).

### 7. ocean-acidification-detailed-cli

**completed** · Local identifier repair; source implementation unresolved.

Growth_Rate is undeclared; Calcifier Growth Rate is the unique local declared growth coefficient. Explicit mapping repairs this reference. Zeebe's publication index supplies neither this model's full carbonate chemistry nor these illustrative biological coefficients.

Original reference: [cited source](https://www.soest.hawaii.edu/oceanography/faculty/zeebe_files/Publications.html).

Full-horizon successful probes: dt=0.5: 201 samples; dt=0.25: 401 samples; dt=0.125: 801 samples.

Maximum scaled stock differences across successive grids: 0.0004385, 0.000218584. These are numerical sensitivity observations, not source validation.

### 8. sea-level-rise-and-ice-sheet-dynamics-model-cli

**failed** · Unresolved; definition unchanged.

CO2_Scenario is an undeclared forcing/table function; many stock/flow shorthand references are absent. Source Cookbook contains neither this sea-level model nor the CO2 scenario points. Need actual forcing history and equation/unit reconciliation; a fabricated trajectory is not acceptable.

Original reference: [cited source](https://github.com/SDXorg/PySD-Cookbook).

### 9. sustainable-agriculture-transition-cli

**failed** · Unresolved; definition unchanged.

All farm compartments are0; adoption divides by Total_Farms=0. The sustainability citation does not establish initial farm composition or this adaptation. Need explicit source initial state; adding a denominator floor or arbitrary farms changes the model.

Original reference: [cited source](https://doi.org/10.1038/s41893-018-0114-0).

### 10. common-value-auction-eco

**failed** · Unresolved; definition unchanged.

Bidder_Experience integrates cumulative Winner_Profit and multiplies bid-adjustment gain. The unbounded adaptive gain destabilizes this ODE/default Euler run. Milgrom-Weber's auction theory does not establish this learning ODE or coefficients; no source-supported gain cap or step replacement recovered.

Original reference: [cited source](https://doi.org/10.2307/1911865).

Full-horizon successful probes: dt=0.25: 401 samples.

### 11. cybersecurity-threat-landscape-eco

**failed** · Unresolved; definition unchanged.

All threat/defense stocks initialize0; Successful_Attacks contains0/(0+0). Verizon DBIR is observational evidence, not a definition of this zero-threat limit or these dynamic equations. Need a documented limit/reporting convention and actual initial state.

Original reference: [cited source](https://www.verizon.com/business/resources/reports/dbir/).

### 12. fishery-dynamics-and-management-model-eco

**completed** · Local identifier repair; source implementation unresolved.

Fifteen fishery shorthand references have unique complete local declarations (including BMSY/FMSY, TAC, capital and profit). Explicit mapping restores scalar identity. The SDX test-model repository has no matching native fishery implementation; recruitment, topology, parameters and calibration remain illustrative.

Original reference: [cited source](https://github.com/SDXorg/test-models).

Full-horizon successful probes: dt=0.25: 401 samples; dt=0.125: 801 samples; dt=0.0625: 1601 samples.

Maximum scaled stock differences across successive grids: 0.00153386, 0.000756171. These are numerical sensitivity observations, not source validation.

### 13. labor-market-dynamics-model-eco

**failed** · Unresolved; definition unchanged.

Vacancy Creation has an unmatched closing parenthesis. Employed/Unemployed/Entry_Rate/Long_Term_Fraction are undeclared; all stocks are0 despite unused Initial... auxiliaries. Static syntax repair alone would expose0/0 unemployment/matching expressions. Need source stock initializers, intended grouping and full original equations.

Original reference: [cited source](https://github.com/SDXorg/test-models).

### 14. market-share-competition-model-eco

**failed** · Local identifier repair; source implementation unresolved.

Twenty-one abbreviated Firm_A/B references differ from unique local declared names. Explicit mapping restores local identity. The source test-model repository has no matching competition model; local Customer_Base_B is already defined as Total_Market-Customer_Base_A, making its acquisition residual identically0. No behavioral change invented. After identity repair the extreme Quality Investment input causes rapid share overshoot and negative cumulative experience; the fractional learning power becomes complex by t1. Default remains unresolved.

Original reference: [cited source](https://github.com/SDXorg/test-models).

### 15. platform-network-effects-advanced-eco

**failed** · Unresolved; definition unchanged.

Churn coefficients1-User_Value/50 and1-Provider_Value/25 become negative; value growth can drive self-reinforcing user/provider growth beyond market bounds. Armstrong/Rochet-style platform context is not source support for these equations. Need original domain restrictions or structurally derived churn; no clamp inserted.

Original reference: [cited source](https://doi.org/10.1257/jep.23.3.125).

### 16. real-business-cycle-basic-eco

**failed** · Unresolved; definition unchanged.

Technology_Shock integrates a positive Rho*log deviation as a derivative, whereas rho=.95 in an RBC process is a discrete-time persistence coefficient. Output is accumulated production with no outflow. Kydland-Prescott does not validate this mixed formulation. Need a faithful discrete update or complete continuous-time adaptation, not guessed mean-reversion.

Original reference: [cited source](https://doi.org/10.2307/1913386).

### 17. startup-ecosystem-dynamics-eco

**failed** · Unresolved; definition unchanged.

Available Funding and Talent Pool can become negative under unrestricted deployment/hiring; rational funding denominator can cross0 and Active Startups can fall below-1, invalidating LOG(1+Active_Startups). Startup ecosystem citation does not supply a source financing constraint. Need original unit/accounting rules.

Original reference: [cited source](https://doi.org/10.1002/9781119204459).

### 18. subscripted-population-model-massachusetts-towns-eco

**failed** · Unresolved; definition unchanged.

Initial Population is a list containing ellipsis; Towns subscripts and four-argument DELAY are unsupported scalar dialect. Pinned native source contains351 town populations, subscripted equations and DELAY FIXED. Cannot collapse to one stock or invent a scalar initial population while preserving the intended model.

Original reference: [cited source](https://github.com/SDXorg/test-models).

### 19. workforce-model-eco

**completed** · Native source restoration.

Pinned native workforce.mdl contains the missing seven-point hiring curve and exact hyphenated hour-variable references. Recovered those only. Existing IDs, stock initial values, every numeric coefficient, time controls, links and positions stay unchanged. Full-grid independent literal source recurrence verifies behavior.

Original reference: [cited source](https://doi.org/10.1287/mnsc.35.3.321).

Full-horizon successful probes: dt=0.03125: 4801 samples; dt=0.015625: 9601 samples; dt=0.0078125: 19201 samples.

Maximum scaled stock differences across successive grids: 0.0300452, 0.0151283. These are numerical sensitivity observations, not source validation.

### 20. limits-to-growth-system-archetype-edu

**failed** · Unresolved; definition unchanged.

System State returns text labels from a scalar numeric equation. The Fifth Discipline is a conceptual archetype source, not a string-valued numeric extension. Need an explicit UI reporting/status convention or model-author numerical encoding; silently replacing labels by0 changes content.

Original reference: [cited source](https://www.penguinrandomhouse.com/books/163984/the-fifth-discipline-by-peter-m-senge/).

### 21. grid-frequency-stability-ene

**failed** · Unresolved; definition unchanged.

Frequency Change divides by Stored Kinetic Energy; Inertial Response is an outgoing flow that can drive this stock through0 under underfrequency. Subsequent division amplifies/reserve deployment diverges. The cited power-system article has not supplied this energy balance, units or generator response implementation.

Original reference: [cited source](https://doi.org/10.1109/TPWRS.2018.2821757).

### 22. cholera-sirw-model-epi

**completed** · Local identifier repair; source implementation unresolved.

S/I/R/W refer uniquely to local human/water stocks. N is the sum of the three human compartments; no population constant was invented. Explicit substitution recovers the locally authored SIRW system. The book citation remains conceptual; no empirical cholera calibration or exact original implementation recovered.

Original reference: [cited source](https://doi.org/10.2307/j.ctvcm4gk0).

Full-horizon successful probes: dt=0.1: 3651 samples; dt=0.05: 7301 samples; dt=0.025: 14601 samples.

Maximum scaled stock differences across successive grids: 0.00569191, 0.00284086. These are numerical sensitivity observations, not source validation.

### 23. delay-differential-seir-epi

**failed** · Unresolved; definition unchanged.

DELAY omits explicit prehistory and seeds each delayed flow from its first input. Initial Exposed=100 and Infectious=10 are not linked to compatible exposure/recovery histories; delayed removals can exceed available cohorts and create negative compartments. The original2023 DDE paper needs its actual history functions and transition equations restored.

Original reference: [cited source](https://doi.org/10.1038/s41598-023-40008-9).

### 24. malaria-vector-borne-transmission-model-epi

**failed** · Unresolved; definition unchanged.

Human Population is the live stock sum; nominal death rate is.0001, so nonnegative humans cannot become0 byday194.5 from10000. The observed zero denominator implies loss of nonnegative trajectories before that point, not a missing source mortality coefficient. Need method/unit/flow-positivity investigation against a native malaria source.

Original reference: [cited source](https://doi.org/10.2307/j.ctvcm4gk0).

Full-horizon successful probes: dt=0.25: 1461 samples; dt=0.125: 2921 samples.

Maximum scaled stock differences across successive grids: 0.00746794. These are numerical sensitivity observations, not source validation.

### 25. peer-vaccination-network-nudge-epi

**failed** · Unresolved; definition unchanged.

Willing/resistant/vaccinated fractions are combined with unbounded infection and hospitalization stocks and no recovery/discharge balance. Vaccination protection1-.85*Vaccinated/.7 can become negative. The EpiModel repository is a network stochastic implementation, not a verified source for this small ODE nudge system.

Original reference: [cited source](https://github.com/EpiModel/COVID-Vax-Decisions).

### 26. sir-treatment-dynamics-epi

**completed** · Local identifier repair; source implementation unresolved.

Beta is undeclared; Beta (Transmission Rate)=.5 is the unique local transmission coefficient. Explicit reference fixes recover local numerical execution. Capacity-limited treatment50 and separate recovery rates are local illustrative additions, not validated book equations.

Original reference: [cited source](https://doi.org/10.2307/j.ctvcm4gk0).

Full-horizon successful probes: dt=0.125: 801 samples; dt=0.0625: 1601 samples; dt=0.03125: 3201 samples.

Maximum scaled stock differences across successive grids: 0.0196927, 0.00991828. These are numerical sensitivity observations, not source validation.

### 27. wright-fisher-genetic-drift-evo

**failed** · Unresolved; definition unchanged.

Zero-argument RANDOM is outside supported XMILE/Vensim signature. More fundamentally, an unbounded uniform perturbation times1.7 is not a Wright-Fisher binomial-generation transition and can leave[0,1], making Drift_SD invalid. Replacing RANDOM() with uniform syntax alone is not a scientific repair.

Original reference: [cited source](https://doi.org/10.1093/genetics/16.2.97).

### 28. real-options-investment-timing-fin

**failed** · Unresolved; definition unchanged.

mu=r=.05 makes the positive characteristic root beta exactly1, so the finite perpetual exercise trigger K*beta/(beta-1) is undefined. The economic problem has a limiting/no-finite-trigger regime requiring explicit handling. Trigonometric Noise is also not geometric Brownian motion. Do not perturb r or beta to force a threshold.

Original reference: [cited source](https://press.princeton.edu/books/hardcover/9780691034102/investment-under-uncertainty).

### 29. burnout-recovery-cycle-hea

**failed** · Unresolved; definition unchanged.

Unrestricted Energy_Drain drives energy negative; stress and burnout then amplify drain, while1-Burnout/100 reverses restoration above100. Maslach et al. is a psychology review, not this ODE's domain bounds or coefficients. Need original/source-derived bounded structure rather than a clamp.

Original reference: [cited source](https://doi.org/10.1146/annurev.psych.52.1.397).

### 30. hospital-capacity-and-patient-flow-model-hea

**completed** · Local identifier repair; source implementation unresolved.

Four abbreviated waiting/fatigue/occupancy/ratio names differ from unique local declarations. Explicit references restore local equations. The source field is empty and the earlier healthcare review found no calibration; capacity/reputation feedback, staff dynamics and clinical validity remain unverified.

No original source URL is stored.

Full-horizon successful probes: dt=0.25: 1461 samples; dt=0.125: 2921 samples; dt=0.0625: 5841 samples.

Maximum scaled stock differences across successive grids: 0.149682, 0.00942024. These are numerical sensitivity observations, not source validation.

### 31. cyert-march-behavioral-firm-man

**failed** · Unresolved; definition unchanged.

Actual_Sales -> Market_Share -> Search_Effort -> Profit/Actual_Sales is instantaneous circular dependency. Cyert-March behavioral theory does not determine a unique algebraic-loop solution or adjustment delay here. Inserting SMOOTH or previous values would add an invented causal timing assumption.

Original reference: [cited source](https://doi.org/10.2307/j.ctt1b7x823).

### 32. sterman-workforce-hiring-man

**failed** · Unresolved; definition unchanged.

Actual_Demand uses STEP(50), while supported source-language STEP requires(height,step_time). Inferring STEP(1,50) from context would impose an unverified demand-event amplitude/time convention. Need original workforce variant's actual demand equation; preserve the input until recovered.

Original reference: [cited source](https://web.mit.edu/jsterman/www/BusDyn2.html).

### 33. morris-lecar-neuron-neu

**numerically_completed_but_missing_dynamics** · Unresolved; definition unchanged.

Original default requests40000 intervals. Expanded bounded engine now retains40001 samples, but no flows or stock initial equations implement membrane or potassium derivatives. Both stocks remain constant. This is an incomplete Morris-Lecar model despite numerical completion; native kinetics/gating parameters and derivative wiring are still missing.

Original reference: [cited source](https://doi.org/10.1016/S0006-3495(81)84782-0).

Full-horizon successful probes: dt=0.01: 40001 samples; dt=0.005: 80001 samples.

Maximum scaled stock differences across successive grids: 0. These are numerical sensitivity observations, not source validation.

### 34. belousov-zhabotinsky-oscillator-phy

**failed** · Unresolved; definition unchanged.

Initial dX and dY are about-2e6 with Euler dt=.01, immediately driving concentrations far below0. Source reaction-rate system is stiff; current local scaling/parameter choices are not traced to a full original recipe. Need chemical units/initial-state/source kinetics plus a supported stiff numerical method; no arbitrary tiny dt or clamp.

Original reference: [cited source](https://doi.org/10.1063/1.1681288).

### 35. double-pendulum-phy

**completed** · Native source restoration.

Pinned Double_Pendulum.mdl establishes every coefficient, stock initializer, derivative and source dt1/128 over100s. Translate g,m1,m2,L1,L2,theta1,theta2,omega1,omega2 and Angular_Velocity2 to existing declared quantities; retain12800 intervals. Full-grid independent source Euler comparison passes, with substantial energy drift explicitly retained as an accuracy limitation.

Original reference: [cited source](https://github.com/SDXorg/PySD-Cookbook).

Full-horizon successful probes: dt=0.0078125: 12801 samples; dt=0.00390625: 25601 samples; dt=0.00195312: 51201 samples.

Maximum scaled stock differences across successive grids: 1.4447, 1.45208. These are numerical sensitivity observations, not source validation.

### 36. navier-stokes-pipe-flow-phy

**failed** · Unresolved; definition unchanged.

Acceleration (force/mass) feeds Flow Rate rather than velocity, while Velocity divides by pipe cross-section; friction expression and pressure-loss flow mix spatial head-loss with temporal stock rate. Coarse explicit integration rapidly produces negative/huge states. Pope's Turbulent Flows reference is conceptual, not this lumped transient system.

Original reference: [cited source](https://doi.org/10.1017/CBO9780511840531).

Full-horizon successful probes: dt=0.005: 2001 samples; dt=0.0025: 4001 samples.

Maximum scaled stock differences across successive grids: 0.186796. These are numerical sensitivity observations, not source validation.

### 37. restricted-three-body-phy

**completed** · Local identifier repair; source implementation unresolved.

Mu and Omega uniquely denote Mass Ratio (mu) and Omega (Angular Velocity). Explicit references restore local equations. The softening denominator+r^3 .001 is a local alteration and the SDX test-model repository has no matching native restricted-three-body implementation; physical fidelity is unresolved.

Original reference: [cited source](https://github.com/SDXorg/test-models).

Full-horizon successful probes: dt=0.01: 2001 samples; dt=0.005: 4001 samples; dt=0.0025: 8001 samples.

Maximum scaled stock differences across successive grids: 1.02506, 1.16431. These are numerical sensitivity observations, not source validation.

### 38. baby-names-popularity-dynamics-soc

**failed** · Unresolved; definition unchanged.

Actual Cookbook Baby_Names.mdl is itself a sketch with A FUNCTION OF placeholders and FINAL TIME1013<INITIAL TIME1880. Local concrete rates/initials have no native executable support; People Aware decreases below0 from constant death flow, driving invalid sign feedback. Cannot recover missing empirical time series or equations from this sketch.

Original reference: [cited source](https://doi.org/10.1016/j.socnet.2007.04.006).

### 39. goldstone-tilly-protest-dynamics-model-soc

**completed** · Local identifier repair; source implementation unresolved.

Parenthesized A/Tc/V/k1/k2/k3/O/C/G/Tr names are declared, but equations omit punctuation differently. Explicit quoted references preserve exact names. Existing SocNet DOI resolves to a two-mode network statistics paper, not Goldstone-Tilly protest dynamics; fixing name references does not repair provenance.

Original reference: [cited source](https://doi.org/10.1016/j.socnet.2007.04.006).

Full-horizon successful probes: dt=0.03125: 321 samples; dt=0.015625: 641 samples; dt=0.0078125: 1281 samples.

Maximum scaled stock differences across successive grids: 0, 0. These are numerical sensitivity observations, not source validation.

### 40. migration-dynamics-soc

**completed** · Local identifier repair; source implementation unresolved.

Wage_Origin and Wage_Destination differ from declared Wage at Origin/Destination. Explicit mapping repairs local identities. Existing SocNet DOI is a two-mode network statistics paper, not this migration ODE; source equation fidelity and signed wage-driven emigration remain unresolved.

Original reference: [cited source](https://doi.org/10.1016/j.socnet.2007.04.006).

Full-horizon successful probes: dt=0.5: 201 samples; dt=0.25: 401 samples; dt=0.125: 801 samples.

Maximum scaled stock differences across successive grids: 0.00606927, 0.00305296. These are numerical sensitivity observations, not source validation.

### 41. ostrom-common-pool-institutions-soc

**failed** · Unresolved; definition unchanged.

Extraction exceeds maximum logistic regeneration even at initial near-capacity stock: regeneration24 versus extraction45. Constant extraction persists through resource0, then logistic growth becomes increasingly negative, producing finite-time negative blowup. Ostrom's book supports institutional concepts, not this unbounded stock equation.

Original reference: [cited source](https://doi.org/10.1017/CBO9780511807763).

### 42. social-media-viral-spread-soc

**failed** · Unresolved; definition unchanged.

Exposure rate multiplies susceptible users by an unbounded feedback Algorithm_Boost driven by engagement. Rates can empty susceptible stock within one Euler interval, after which signed compartments/amplification explode. The SocNet DOI is unrelated network descriptive statistics; source response/positivity conditions are unavailable.

Original reference: [cited source](https://doi.org/10.1016/j.socnet.2007.04.006).

### 43. urban-development-feedback-soc

**failed** · Unresolved; definition unchanged.

Infrastructure investment from population/jobs feeds attractiveness multiplicatively; unrestricted migration can exceed land capacity, making business attractiveness negative and interacting with population-squared denominators. Vensim sample catalog confirms the Urban Dynamics example exists but supplies no equation match for this small local adaptation.

Original reference: [cited source](https://vensim.com/documentation/sample_models.html).

Full-horizon successful probes: dt=0.125: 801 samples; dt=0.0625: 1601 samples.

Maximum scaled stock differences across successive grids: 0.031282. These are numerical sensitivity observations, not source validation.

### 44. quantum-computing-progress-tec

**failed** · Local identifier repair; source implementation unresolved.

R_and_D_Investment must explicitly reference the declared R&D Investment stock; do not add an engine ampersand alias. Even after mapping, error-rate decay can cross numerical/biological bounds and Logical_Qubits divides by Error_Rate. Arute et al.2019 is an experimental processor paper, not these investment/progress equations.

Original reference: [cited source](https://doi.org/10.1038/s41586-019-1666-5).

### 45. greenshields-traffic-flow-model-tra

**failed** · Unresolved; definition unchanged.

Greenshields supplies the linear speed-density law and parabolic capacity relation, already restored in1.4. The local arrival/queue ODE and dt=.1h are illustrative additions. At low-density equilibrium the response derivative is about-36/hour, so Euler h*.abs(lambda)>2 and unstable. This is not evidence for a different Greenshields coefficient or a source-defined clamp.

Original reference: [cited source](https://onlinepubs.trb.org/Onlinepubs/hrbproceedings/14/14P1-023.pdf).

Full-horizon successful probes: dt=0.05: 481 samples; dt=0.025: 961 samples.

Maximum scaled stock differences across successive grids: 0.223426. These are numerical sensitivity observations, not source validation.

## Private production cases

Two private snapshots were inspected separately without remote mutation. Exact quoting of declared multiword identifiers removes their syntax errors but reveals undefined zero-pending-vote reporting at their all-zero initial states. No source or author-defined initial conditions/zero-denominator convention supports completing those models. Original snapshots stay unchanged; diagnostic candidates and detailed evidence remain private.

## Verification

- `.venv/bin/python -m pytest -q tests/test_capacity_v17.py tests/test_corpus_sources_v17_a.py`:14 passed.
- Earlier combined engine, analytics, investigation and capacity regression run:184 passed; the updated investigation/capacity-only rerun passed31 tests. One existing Pydantic settings forward-reference warning remains.
- Full native-grid or independent compartment-RHS comparisons cover workforce, double pendulum, treatment SIR and cholera; conservation and the pendulum's energy-drift limitation are explicit assertions.
- Receipt preservation tests verify every existing identity, layout field, stock initializer and time setting, plus exact after-hashes for all14 changed definitions.

The read-only reproduction script is `operations/reconcile_corpus_v17_a.py`; its full manifest is `operations/corpus-reconciliation-v17-a.json`. External source retrieval results include unavailable references and DOI registration metadata. An HTTP response/body hash or registered title alone is not evidence that original equations were recovered. Full-library tests/audit and any deployment are separate work.
