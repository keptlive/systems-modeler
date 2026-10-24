# Engine/input findings 1.6

Read-only review of the 137 public failed default runs in operations/library-full-v150.json, against source baseline e4fabd8. The initial investigation changed only this report and tests/test_engine_inputs_v16.py. The parent then assigned bounded app.js editor fixes, recorded below, with scripts/check_property_inputs_v16.cjs. No engine, corpus model, earlier test or receipt was edited; no commit or deployment.

The strongest findings concern input identity and initialization semantics. I found no evidence that making the engine case-sensitive, automatically assigning “Initial …” auxiliaries, or replacing zero denominators would correctly repair these failures. Three independently reproducible strict-XMILE identifier gaps are recorded separately with strict expected-failure tests; they are not offered as explanations for these 137 failures.

## Audit scope

The audit contains 941 completed runs and 137 failures among 1,078 tracked public definitions. Error-text counts overlap: 77 failures mention an unknown variable,5 unknown functions, 41 nonfinite values, 7 duplicate names, 4 domain errors, 9 division by zero, 2 unsupported expression types, 6 request-step limits and 1 syntax error. These are observations of messages, not mutually exclusive scientific diagnoses or claims that the first reported downstream dependency is the root cause.

Graphical-function restoration and the LOOKUP trio are owned by the separate physical/corpus investigation; no proposed graph data or LOOKUP repair is included here.

## Case collisions: explicit input defects, not a casefold engine bug

[XMILE 1.0 sections 3.2.2.1–3.2.2.2](https://docs.oasis-open.org/xmile/xmile/v1.0/xmile-v1.0.html) treats names differing only by case as the same identifier, and makes spaces, underscores, newline and nonbreaking space equivalent. The [official Vensim variable-name rules](https://www.vensim.com/documentation/ref_variable_names.html) independently specify case-insensitive names and equivalent spaces/underbars.

All seven audited collision failures are actual duplicate names or case-only collisions:

| Public model | Conflicting definitions | Consequence / recommendation |
| --- | --- | --- |
| global-nitrogen-cycle-model-cli | flow industrial_fixation=0; auxiliary industrial_fixation=120 | Conflicting equations for one symbol. Recover intended fixation flow and distinct parameter identity; do not pick0 or 120 by element order. |
| predator-prey-allee-effect-eco | attack coefficient a=.02; Allee constant A=20 | The source mathematical notation needs distinct engine names, e.g. Attack Coefficient and Allee Scale, with explicit expression substitution. Do not turn on case sensitivity globally. |
| software-project-dynamics-brooks-law-eco | flow Turnover Rate=Workforce*Turnover_Rate; parameter Turnover Rate=.01 | Fractional coefficient and people-per-time flow share one symbol. Distinct semantic names and units are necessary; current expression is ambiguous/self-referential. |
| university-enrollment-dynamics-edu | flow and auxiliary Endowment Spending, both Endowment_Fund*Spending_Rate | Equations agree but identifiers still collide. Preserve product elements/IDs and reconcile their intended diagnostic/reference identities explicitly; do not silently discard one. |
| full-beer-model | duplicate R_Order_Rate, W_Order_Rate, W_Customer_Orders; some entries are A FUNCTION OF placeholders | Incomplete/duplicated source extraction. Original source recovery is required; arbitrary deduplication would discard content and conceal placeholders. |
| cell-cycle-regulation-phy | k3/K3, k4/K4, k5/K5, k6/K6 have different coefficients | Kinetic rates and saturation scales require distinct semantic tokens and source-unit mapping. Casefold rejection is correct for this language. |
| coupled-pendulum-oscillators-phy | Angular Acceleration1/2 each occur as flow and auxiliary; flows reference their own canonical names | Assign a separate derivative/flow identity and propagate references from a verified model. The duplicate-name error precedes additional shorthand and initialization defects. |

Concrete independent counterexample: the mathematical expression k3/(K3+1), with k3=1 and K3=.5, is 2/3. Declaring k3 and K3 as two current-language variables correctly raises a collision instead of returning a silently wrong value. A synthetic translation to Kinetic_Rate_3/(Saturation_Constant_3+1) gives 2/3 at every output. This establishes the semantic distinction; it does not authorize renaming real model quantities without recovering their source mapping.

Recommendation: authoring/import validation should list both element IDs, types, original spellings and equations for every collision. Semantic symbol translation must happen explicitly at the source/adaptation boundary, preserve original notation as provenance and preserve existing UI elements. Never repair ambiguity by declaration order or silently relaxing the language.

## Initial stocks: missing assignments are not inferred from labels

[XMILE 1.0 section 4.2](https://docs.oasis-open.org/xmile/xmile/v1.0/xmile-v1.0.html) gives each stock an explicit initial-value equation; when that equation depends on other variables, their initial values are used. It does not assign a stock from an auxiliary merely named “Initial …”.

None of the 137 failed public JSON definitions has a nonempty stock initial equation. Fourteen have every stored stock initial value equal to zero. This observation does not itself prove an error: zero can be a valid initial condition. Four of those fourteen also expose “Initial …” auxiliaries:

- labor-market-dynamics-model-eco: Initial Labor Force 160000000, Initial Working Age Population 200000000, derived Initial Vacancies, Initial Wage 60000; stock initials remain zero. A separate unmatched parenthesis currently fails parsing before this can be reconciled.
- seasonal-influenza-transmission-model-with-vaccination-epi: Initial Exposed 100 and Initial Infectious 10, yet all stock initial values are zero. These auxiliaries do not initialize their similarly named compartments.
- coupled-pendulum-oscillators-phy: Initial Angle1=.3 plus initial velocity/energy auxiliaries, while all stock initial values remain zero. It first fails duplicate-name validation and also has missing shorthand references.
- subscripted-population-model-massachusetts-towns-eco: Initial Population is a list containing an ellipsis. This is missing data/unsupported array dialect, not an evaluable complete population initializer.

Independent minimal experiments:

1. A stock Susceptible with initial_value=0 and no initial equation remains zero, even alongside Initial Susceptible=100. This is correct current behavior.
2. Setting the stock initial equation explicitly to Initial_Population, with Initial Population=100+TIME and simulation start 5, starts it at 105. With inflow 2, its trajectory is105+2*(t-5), while the auxiliary continues changing. Initial equations are not reevaluated as stock assignments.
3. Forward parameter/stock dependencies resolve without using numeric placeholders; true initial cycles fail rather than taking arbitrary placeholder values. An invalid initial equation never falls back to the numeric field.

Recommendation: show the actual stock initializer, its evaluated start value and unused possible initial-value auxiliaries in an authoring diagnostic. Flag possible disconnections as evidence for review, never automatic assignments. Recover the intended source initial state, units and conservation totals before changing stored model inputs.

## Undefined diagnostics can prevent otherwise meaningful dynamics

At zero vaccinations, Deaths_Averted/(Elderly_Vaccinated+Adult_Vaccinated+Young_Vaccinated) is0/0. The vaccine-allocation definition therefore fails at its first reported output. Likewise the all-zero bacterial definition divides by Total_Bacteria. The engine computes all declared scalar outputs, not merely flows affecting stocks, so an undefined diagnostic invalidates the complete result.

A minimal Count stock at 0, constant inflow 1 and unused Ratio=Count/Count raises division by zero. An explicitly authored reporting convention IF Count=0 THEN -1 ELSE Count/Count yields[-1,1,1,…] while preserving Count=t. The latter is a synthetic demonstration of lazy reporting, not evidence that -1,0,NaN or any other replacement is correct for the scientific models.

Recommendation: distinguish “undefined reporting diagnostic at initialization” from “derivative cannot be computed” in diagnostics. A future partial-output mechanism would need an explicit result-schema/status contract and must not replace invalid quantities by zero. Scientific model repairs need source-defined conventions.

## Additional input/dialect distinctions

- email-workflow-management-model-soc uses DELAY(Arrival_Little_Action,Little_Action_Time,Little_Action_Order). Arrival_Little_Action is not the declared arrival-flow name. Even after an explicit source-backed name mapping, the supported XMILE third DELAY argument is an initial/prehistory value, not an order. A minimal DELAY(1,1,3) returns 3 before the delay horizon, while DELAYN(1,1,3,0) starts at 0 with three exponential stages. Do not reinterpret all three-argument DELAY calls as DELAYN.
- limits-to-growth-system-archetype-edu returns string labels such as Growing from an equation. [XMILE section 3.2.3](https://docs.oasis-open.org/xmile/xmile/v1.0/xmile-v1.0.html) defines its equation values as real numbers. A UI status formatter is distinct from a numeric equation or a future explicit string dialect. Do not turn strings into zero.
- Common missing names are semantic abbreviations, not permitted case/whitespace aliases. A stock Susceptible Population does not implicitly define S or Susceptible. Exact supported aliases work; fuzzy name resolution could wire the wrong quantity.
- Six defaults exceed the 10,000-step request limit. This is a capacity/request outcome, not proof of bad mathematics; increasing DT blindly can destroy accuracy for a fast ODE. Use a bounded scientifically meaningful horizon or an explicitly designed batching feature while retaining limits.
- Signed stocks remain allowed. Optional nonnegative-stock semantics need explicit source/model support; global clamping would change equations and can conceal failures.

## Confirmed bounded strict-XMILE identifier gaps (not repaired)

The existing historical alias policy maps punctuation to underscores and makes them collide. That is broader than [XMILE sections 3.2.2.1–3.2.2.2](https://docs.oasis-open.org/xmile/xmile/v1.0/xmile-v1.0.html), where quoted punctuation is literal and an en-space is explicitly not equivalent to standard identifier whitespace.

| Counterexample | Independent expected strict-XMILE result | Current result |
| --- | --- | --- |
| variables “A-B”=1 and “A_B”=2; Output="A-B"+"A_B" |3; hyphen is a literal character inside the quoted name | Duplicate-name rejection |
| variables “A B” (U+2002 en-space)=1 and “A_B”=2 |3; en-space is explicitly not identifier whitespace | Duplicate-name rejection |
| Cash$Balance=2; expression Cash$Balance+1 |3; internal dollar is a permitted unquoted identifier character | Syntax error; quoting the name works |

Three strict xfails record these unresolved gaps. Existing tests intentionally pin the legacy punctuation alias behavior, so changing canonical_name globally is not an appropriate unreviewed fix. Recommendation: design an explicit strict/import dialect or exact-identifier path with legacy alias fallback only when unambiguous, and propagate it through validation, evaluation, connector extraction and export together. Existing names/IDs/product paths must survive. No such mode or API change is made here.

All seven actual corpus collision cases above are exact-name or case-only duplicates, so these punctuation gaps do not account for those failures. No failed equation contains a dollar sign. There is no demonstrated 137-model success gain from these synthetic gaps.

## Verification and provenance

Command: .venv/bin/python -m pytest -q tests/test_engine_inputs_v16.py

Result: **20 passed, 3 strict expected failures**. The expected failures are the three unresolved identifier gaps above; no existing test was weakened. Core engine files and every tracked model remain unchanged by this pass.

Audit file SHA256: a10be7c2d954be3b46e456aab06dfb01d651fea42524ef56ce337893b751fa71

All-zero-stock failed definitions (inventory only, not a defect verdict):

- models/climate/global-food-security-cli.json
- models/climate/ocean-heat-content-dynamics-cli.json
- models/climate/sustainable-agriculture-transition-cli.json
- models/economics/cybersecurity-threat-landscape-eco.json
- models/economics/labor-market-dynamics-model-eco.json
- models/economics/subscripted-population-model-massachusetts-towns-eco.json
- models/education/learning-and-forgetting-curves-model-edu.json
- models/education/online-learning-platform-edu.json
- models/epidemiology/seasonal-influenza-transmission-model-with-vaccination-epi.json
- models/evolution/kimura-neutral-theory-evo.json
- models/healthcare/antibiotic-resistance-evolution-extended-hea.json
- models/physics/coupled-pendulum-oscillators-phy.json
- models/social/email-workflow-management-model-soc.json
- models/social/urban-traffic-flow-dynamics-soc.json


## Property-editor input behavior (executed JavaScript probe)

The parent requested an additional read-only review of static/js/app.js. A Node 24 VM loaded the actual App object with minimal document/Canvas/Simulation stubs and exercised its real updateProperty, desktop property binding and mobile property binding. The probe initially ran before application edits; the parent subsequently authorized the bounded fixes below.

### Rename breaks dependent model references

At the inspected baseline, updateProperty at line 1223 assigns element[property]=value, invalidates results and rerenders. Both name inputs call it on every input event. It does not rename equation tokens, name-based flow endpoints or name-based connector endpoints, or reject canonical collisions/empty names.

Executed fixture:

- stock ID s, name Population, initial 100;
- Births equation Population*.1 with to_stock Population;
- another flow uses from_stock s;
- one connector uses Population, another uses IDs.

After updateProperty('name','People'), the stock is People but the equation, first flow endpoint and connector still say Population. The ID-based endpoint remains s. This is a model integrity defect introduced by an ordinary user edit, unlike the corpus's preexisting source-name mismatches.

Safe fix recommendation: keep a name draft, validate nonempty/canonical uniqueness before commit, and perform a single rename transaction preserving IDs and updating dependent references. Rewrite parsed identifier tokens, including quoted forms and supported aliases, rather than global text replacement. Do not rewrite comments, string table names unrelated to the renamed element, substrings such as Population_Growth, or external provenance text. Name-based endpoints/connectors must be updated; stable ID endpoints stay unchanged. If a syntax cannot safely be rewritten, report exact dependencies before committing a partial rename. One undo operation should restore the entire transaction. Existing properties, paths and content must remain available.

### Blank numeric input is guarded, but its UX path is inconsistent

Desktop lines 1200–1201 and mobile lines 361–362 combine a finite valueAsNumber guard on input with parseFloat(value) on change. Clearing the field therefore suppresses the input write but calls updateProperty(initial_value,NaN) on blur/change.

The current central guard at lines 1225–1228 already rejects this write. The executed probe preserved initial_value 100 on both desktop/mobile; alerts fired, and updatePropertiesPanel was called. Thus this is **not** evidence that the current model stores NaN or serializes it to null. The defect is inconsistent draft/commit behavior: change reparses invalid data, alerts, and refreshes the desktop-only properties panel even when the invalid input was in the mobile panel.

Safe fix recommendation: use one shared finite-number commit path for input/change, with blank and invalid drafts leaving the last valid model value intact. Use valueAsNumber or a strict whole-value conversion; never parseFloat-prefix acceptance. On commit, show an inline validity message or restore the previous valid value in the active panel. Refresh both panel variants through their appropriate renderer. Keep the central finite guard as defense in depth. Do not coerce blank to 0, and do not regenerate the entire active panel on each valid keystroke in a way that loses focus/caret.

### Stock initializer augmentation already exists in the full product

The base App renderers expose numeric initial_value for stocks and restrict their equation inputs to flows/variables. However, **workspace.js dynamically adds “Initial equation (overrides numeric value)” plus Units to both desktop/mobile properties, and relabels the numeric field “Fallback value (initial equation takes precedence)” when appropriate**. That existing augmentation must be counted when assessing the complete product. The isolated App VM probe did not load workspace.js and does not establish a missing-feature defect in the assembled interface.

Five tracked definitions use stock initial equations: sir-simple, si, sir, seir-epidemic-model-epi and solow-swan-growth-model-eco. For example, SEIR Susceptible stores numeric0 but initializes from Total_Population-Initial_Exposed. The engine correctly follows the expression. The existing workspace caption explains the fallback; this patch preserves that field, caption, initializer and units. An optional future effective-start-value preview could make dependencies clearer, but is not required to repair the confirmed rename or numeric-draft defects.

## Authorized bounded editor corrections

No reusable backend rename operation was found. The existing MCP contract explicitly requires clients to rename dependent references in the same batch, and no rename endpoint/helper exists in app/. Rather than add a new API, the editor now handles its supported scalar syntax locally and rejects unsafe ambiguity.

Changed static/js/app.js:

- Both name editors commit on change, not every keystroke. Empty/control-character/reserved-time names and canonical element/table/ID collisions are rejected with a readable message.
- A rename stages all equation-token and structural-reference changes before mutation. Quoted identifiers, case/space aliases and supported punctuation aliases use the existing engine namespace. Unicode casefold exceptions are generated from the backend Python runtime; whitespace/punctuation normalization follows the current engine policy, not the unresolved strict-XMILE alternative.
- Token rewrites affect complete scalar references and stock initializer expressions, not substrings, numeric exponents, brace comments, single-quoted lookup strings or built-in function positions. Named table calls and declared LOOKUP table arguments retain their independent table identity.
- Ambiguous scalar-as-function/table uses, affected array references, malformed quotes/brackets and unsupported syntax cancel the rename before any model mutation. IDs stay stable; name-based flow and connector endpoints are updated, while existing ID endpoints remain unchanged.
- The new name and any selected element's rewritten equation fields synchronize without rebuilding the panel, preserving workspace.js's initializer/units augmentation.
- Initial-number input/change handlers share valueAsNumber plus finite validation. Invalid or blank drafts never alter the model. On commit, desktop and mobile fields restore the last valid value and show a clear message; direct nonfinite property writes still fail in the central guard. No blank-to-zero coercion or parseFloat prefix acceptance.
- The existing mobile chart is shown before Chart Options and series/filter chips; final values remain after them. All IDs, data attributes, event hooks, chart modes, series controls and analytics/AI tabs remain available. Chart/Stats/AI tab captions no longer contain literal emoji.

Verification:

- node scripts/check_property_inputs_v16.cjs passes. It executes actual App methods and real property binding with a minimal document stub, covering transaction success/rollback, canonical and ID collisions, Unicode names, quoted references, comments, built-ins/table namespaces, both numeric fields, preserved chart/control hooks and chart-first order.
- The script's --json mode emits the original and actual App-renamed synthetic models. Feeding these through the unchanged Python engine independently confirms identical simulation times and Population/People Served, Births and Population Growth trajectories. This is stronger evidence than comparing rewritten strings alone.
- .venv/bin/python -m pytest -q tests/test_engine_inputs_v16.py tests/test_advanced_functions_v15.py: **238 passed, 3 strict expected failures**. The xfails remain the three documented engine identifier gaps, not failures of the editor patch.
- This isolated Node probe is not full browser rendering/accessibility QA. Parent/diagram work owns assembled UI verification.


Inspected app.js SHA256: 74411e1660bfe4e6d144ab5e71c7004a451509aec90512fdeeb249c65aee560f

Frozen corrected app.js SHA256: b027f7631069f84aa95263bff8c76821aeb9b38b8c2b855ce7dcaa33dacdd467
