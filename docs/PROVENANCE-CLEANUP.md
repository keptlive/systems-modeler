# Proposed NSIDC description-reference cleanup

2026-10-24. **Isolated metadata proposals only; no active models changed.** Twenty-six clearly unrelated generic NSIDC reference sentences are proposed for removal. One relevant Arctic reference is preserved and one glacial-cycle reference is deferred. This does not verify any model's equations, calibration, literature fidelity, or remaining source citations.

## Context/source review and exact scope

The earlier audit counted28 non-Arctic suspects, including the old World3 capital definition. That definition has since been separately replaced. This scan of the995-file checkout finds28 **total** remaining matches:26 proposed removals, Arctic amplification preserved, glacial/interglacial cycles conservatively deferred. No count was padded by deleting legitimate context.

The repeated sentence is exactly:

` Reference: NSIDC Arctic Sea Ice News. Source: https://nsidc.org/arcticseaicenews/`

NSIDC's first-party [About Our Analyses](https://nsidc.org/news-analyses/about-our-analyses), [analysis archive](https://nsidc.org/sea-ice-today/analyses) and [project description](https://nsidc.org/our-research/featured-projects/sea-ice-today-and-ice-sheets-today) establish that the cited service concerns observed sea-ice conditions and polar/cryosphere research context. The old URL timed out during retrieval; the first-party successor pages were accessible. A missing old URL alone was not used as evidence of irrelevance.

For each entry the reviewer read its description, stocks, auxiliary names and existing source/reference. None of the26 proposed removals contains an Arctic/sea-ice mechanism, observed ice series or a parameter attribution to that service. These cover finance, service operations, education, general biodiversity, agriculture, healthcare, transport and business/economic mechanisms. Each per-file record lists its actual context stocks/variables, retained source/reference and the exact decision rationale. Arctic amplification has sea-ice extent, Arctic temperature and ocean heat, directly within the citation's subject; it stays byte-for-byte intact. Global glacial cycles involve ice volume/temperature/albedo: while the generic Arctic-news page is not established as its executable source, contextual relevance is plausible enough to defer deletion.

Existing DOI identities were checked through publisher-deposited Crossref metadata where available;20distinct DOI/article links were attempted. BIBLIOGRAPHIC-CHECKS.json retains titles, lookup URLs, retrieval statuses and unavailable/429/404 outcomes. These are bibliographic checks, not primary-equation validation. Generic SDXorg [Cookbook](https://github.com/SDXorg/PySD-Cookbook) and [test-models](https://github.com/SDXorg/test-models) repository identities and the [Case/Shiller publisher page](https://www.brookings.edu/articles/is-there-a-bubble-in-the-housing-market/) were inspected, but a generic repository link does not establish a particular JSON's provenance. Additional publisher search results corroborated several titles where metadata retrieval was limited. No guessed replacement citation is inserted.

Only the exact ASCII sentence inside `description` changes. Before snapshots retain exact active bytes; after snapshots are made by one exact byte-substring removal. Thus all other formatting, IDs, names, created/updated timestamps, source/reference fields, model claims, warning paragraphs, equations, initializer values, units, settings, topology and layouts remain unchanged. The existing identifier-reconciliation/unverified-source warning on the protest model is explicitly retained. Scientific or bibliographic defects outside that stray sentence remain open; the cleanup must not be represented as validating the remaining descriptions.

## Additional source discrepancies discovered, not silently repaired

The existing source DOI for the protest entry resolves to ?Basic notions for the analysis of large two-mode networks?; the transit entry to ?Forecasting the effects of road user charge by stochastic agent-based modelling?; startup fundraising to ?Endogenous Liquidity in Asset Markets?; and Heckscher?Ohlin to ?Accounts of the First Bank of the United States.? These differ from their retained references/model claims. Service-quality's DOI also names a managerial-feedback experiment rather than its retained Sterman book reference. These observations are recorded for a later separately scoped provenance repair. The removal candidate **leaves those source/reference fields unchanged** so it does not replace one unsupported attribution with another. Other failed or rate-limited lookups remain unresolved, not labeled wrong merely because retrieval failed.

## Per-file decisions

| Active path | Decision | Inspected stock context | Existing source check |
|---|---|---|---|
| models/management/service-quality-dynamics-man.json | Remove exact stray sentence | Service Quality, Demand, Capacity, Staff Experience | Modeling Managerial Behavior: Misperceptions of Feedback in a Dynamic Decision Making Experiment |
| models/energy/oil-depletion-price-dynamics-ene.json | Remove exact stray sentence | Proven_Reserves_Gb, Production_Capacity_Gbd, Oil_Price_Dollar | unavailable |
| models/education/skill-learning-forgetting-edu.json | Remove exact stray sentence | Skill Level, Memory Strength | repository_or_page_checked |
| models/education/learning-and-forgetting-curves-model-edu.json | Remove exact stray sentence | Knowledge Level, Memory Strength, Cumulative Study Hours | repository_or_page_checked |
| models/education/learning-curve-skill-acquisition-edu.json | Remove exact stray sentence | Skill Level, Practice Accumulated, Memory Strength | unavailable |
| models/social/housing-affordability-crisis-soc.json | Remove exact stray sentence | Housing Stock, Households, Housing Prices, Under Construction, Affordability Gap | unavailable |
| models/social/goldstone-tilly-protest-dynamics-model-soc.json | Remove exact stray sentence | Concessions, Repressive Threat (Tr), Expectation of Concessions Needed, Expectation of Repression Needed | Basic notions for the analysis of large two-mode networks |
| models/transportation/public-transit-ridership-service-tra.json | Remove exact stray sentence | Transit Ridership, Service Level, Transit Revenue, Car Users | Forecasting the effects of road user charge by stochastic agent-based modelling |
| models/climate/biodiversity-ecosystem-function-cli.json | Remove exact stray sentence | Species Richness, Ecosystem Biomass, Soil Nutrients | repository_or_page_checked |
| models/climate/climate-arctic-amplification-cli.json | Preserve | Sea_Ice_Extent_M_km2, Arctic_Temperature_Anomaly, Ocean_Heat_Content | The central role of diminishing sea ice in recent Arctic temperature amplification |
| models/climate/biodiversity-tipping-point-cli.json | Remove exact stray sentence | Species Abundance, Habitat Area, Ecosystem Services | unavailable |
| models/climate/glacial-interglacial-cycle-cli.json | Defer | Ice Volume, Global Temperature Anomaly | repository_or_page_checked |
| models/agriculture/crop-rotation-productivity-agr.json | Remove exact stray sentence | Soil_Nitrogen, Pest_Population, Crop_Yield | Crop rotation |
| models/healthcare/telemedicine-adoption-hea.json | Remove exact stray sentence | Traditional_Visits, Telehealth_Visits, Provider_Readiness | unavailable |
| models/healthcare/moral-hazard-health-insurance-hea.json | Remove exact stray sentence | Healthcare_Utilization, Health_Stock, Insurance_Costs | unavailable |
| models/finance/cryptocurrency-bubble-dynamics-fin.json | Remove exact stray sentence | Crypto_Price, Speculative_Capital, Market_Sentiment, HODLer_Holdings | unavailable |
| models/finance/capm-asset-pricing-fin.json | Remove exact stray sentence | Portfolio Value, Market Value | unavailable |
| models/finance/crypto-market-bubble-fin.json | Remove exact stray sentence | Crypto_Price, Holders, Market_Sentiment | unavailable |
| models/economics/hotelling-exhaustible-resource-model-eco.json | Remove exact stray sentence | Resource_Stock, Resource_Price, Cumulative_Extraction | repository_or_page_checked |
| models/economics/saas-subscription-dynamics-eco.json | Remove exact stray sentence | Prospects, Trial Users, Active Customers, Churned Customers, Monthly Recurring Revenue, Product Quality | System dynamics for corporate business model innovation |
| models/economics/heckscher-ohlin-trade-eco.json | Remove exact stray sentence | Capital Good Output, Labor Good Output | Accounts of the First Bank of the United States |
| models/economics/weitzman-prices-quantities-eco.json | Remove exact stray sentence | Cumulative_Emissions, Welfare_Loss | unavailable |
| models/economics/inflation-expectations-dynamics-eco.json | Remove exact stray sentence | Actual Inflation, Expected Inflation, Wage Level, Central Bank Credibility, Output Gap | unavailable |
| models/economics/housing-market-bubble-crash-eco.json | Remove exact stray sentence | Housing Prices Index, Mortgage Credit, Housing Supply, Speculative Demand, Foreclosure Inventory | repository_or_page_checked |
| models/economics/sales-agent-market-building-dynamics-eco.json | Remove exact stray sentence | Tier 1 Leads, Tier 1 Clients, Tier 2 Leads, Tier 2 Clients, Months of Buffer, Tenure, Total Cumulative Sales, Total Cumulative Income | repository_or_page_checked |
| models/economics/business-startup-fundraising-cycle-eco.json | Remove exact stray sentence | Cash_Balance, Employee_Count, Customers, ARR | Endogenous Liquidity in Asset Markets |
| models/economics/costanza-natural-capital-eco.json | Remove exact stray sentence | Forest_Area, Wetland_Area, Ocean_Area, Grassland_Area | unavailable |
| models/economics/business-customer-lifetime-value-eco.json | Remove exact stray sentence | Marketing_Prospects, Free_Trials, Paying_Customers, Churned_Customers, Cumulative_Revenue | unavailable |

## Reproduction, receipts and admission boundary

MANIFEST.json binds every before/after path, exact SHA-256, ID, changed-field list, removed text, unchanged executable-payload hash, context and source-check boundary. The before/ and after/ trees are review artifacts, not an active model root or an executable curation plan. Independent review must bind exact after hashes before any metadata-only replacement transaction is prepared. If an active file changes after this snapshot, rebase/review it instead of overwriting newer data.

Run `.venv/bin/python -m pytest tests/test_provenance_cleanup.py -q`: **31passed in0.06s**. Checks cover all28 snapshots, exact one-sentence byte removal for26 proposals, unchanged whole non-description JSON payload (stronger than checking selected equations), explicit fields/settings/units/element equality, matching executable hashes, preserved/deferred references, confinement and retained warning paragraphs. No simulation is necessary to prove a description-only byte edit preserves execution; numerical behavior and scientific fidelity were not recertified.

Exact mutation receipts:

| Active path | Before SHA-256 | Proposed after SHA-256 |
|---|---|---|
| models/management/service-quality-dynamics-man.json | `3469f5924ff305ffc0f6e28da9bde91e6bd19ed5eb7addbb57b5c1decb1159c9` | `6230d797c2fee920fe8547762de34cbffc394163aea4d1aa62be120eae8b255a` |
| models/energy/oil-depletion-price-dynamics-ene.json | `623b0b9c73f769aea10e00fdcb7d15799503d74ea13b019ada1d7dec444b0137` | `8c031c6c3aae116cfef1fcf51ad959ba8280e29b8c1649a80c48c890f0a8d0ec` |
| models/education/skill-learning-forgetting-edu.json | `eb2aedebce78716d4be559a694f8edf05d4e5f942d52e4ea88ccb1f7a8f27e3d` | `42f891c2417f1a3789922b07bc4a14ac1e0f15afcad1537e206ac68e749fc18d` |
| models/education/learning-and-forgetting-curves-model-edu.json | `c7f234f22dbd2d976c926c13d048b6b9c6edb841aa5566e1ab3eec9c663cad7f` | `ae9e40832103392b593ee80ab6cc7df6f5763a3832cc4ac44763462226a24037` |
| models/education/learning-curve-skill-acquisition-edu.json | `53884e8ed08ac27f1a15e29a6e1bccac97676502ac9274c035eb6425dccf07fd` | `3c91b17bb3b9b7d3082ae235569629dff61f3905bcf83e39decec5123421ee08` |
| models/social/housing-affordability-crisis-soc.json | `7d46baa35ae054ff04323758a9bbc9cfc9018ef4cdc489279626c9d6cc5674ba` | `de253e0c2453ceb0bdef3d8981283567bad4dba68929c0dfe727b17ca2b61898` |
| models/social/goldstone-tilly-protest-dynamics-model-soc.json | `6faeda03165c27d06a32e4eed11f159851390bb9e17c9802d096ada62154e6e7` | `a13cdfc96c9c420b4e4c3e140cdaf2733c9f2995b66c1c8eadaba407e9c6a121` |
| models/transportation/public-transit-ridership-service-tra.json | `e601918de0899e73955a67044489d875e86d553d759c1b38d4f7aace29fa362b` | `ba7fb744f6c0ee69a2653fce8399dcd125ef8af7b3bea795717c469ccbc8b813` |
| models/climate/biodiversity-ecosystem-function-cli.json | `8c6d072734d42c3c381c8b9fcdec97070229586f61d10d3c0afcc85199ef569a` | `c167e42a11b4e1c8d7023c74e3a9258a603eb76bf9c563fb4144f8418b4e8040` |
| models/climate/biodiversity-tipping-point-cli.json | `f9362c6d860161d4427bdfa4736fd37e232f17fdb94f3ee2c32a2ea687d28513` | `2441116817dc2b21b005965691c5ec367a5746762dff32e8d53398bceb59c724` |
| models/agriculture/crop-rotation-productivity-agr.json | `37815dc6a80c3c42ffa9c03cdfff1187746f236e18a063fd6c209f5caf3fe6ba` | `bfebfbb280bd516b1bc6b514bb22d7265f67398dde8e5b05eb8c0ea027266b98` |
| models/healthcare/telemedicine-adoption-hea.json | `1406f434d7b38cfc7b528246e94da3b01fc592536c89d6325bae5d56f0b538e4` | `76171ea697cf374a70cac8046b8446839e1067c4fcf2226a9af0cd64997b2e3d` |
| models/healthcare/moral-hazard-health-insurance-hea.json | `08028fccbd3ccf3b371d8e310fbaaa9c550e1b917ea6db87488f877b78d3e5d5` | `1be5e0af7f8b6b386af969e19877d435702d0b2bd508abb786aa17abaffefceb` |
| models/finance/cryptocurrency-bubble-dynamics-fin.json | `0fb989e97258ac5dc8e8a76c189e9f692fc100bf566263feb4b97047636ac233` | `cb64c55e0bf5788126d9402ac608007095f4c059791db97421ecdd5de480c0e6` |
| models/finance/capm-asset-pricing-fin.json | `41650843756c51ecea446eb360f28f9a633877c12774c27f88ba47d19d089e77` | `3038a298374c32f2a8ecfc21bbbde4855e43aab7cf72e289e2a40cd6da455d18` |
| models/finance/crypto-market-bubble-fin.json | `caa764ba3c959e8151b327ed9ad79806f23729601e63c41ead7de5c5b6870e7a` | `7ae203618f637ae93f313315d9bee2113286145ec0de50941517739d27e64593` |
| models/economics/hotelling-exhaustible-resource-model-eco.json | `2131b5df8e32722ef7da9c2a85c2966e4308ab7b244c07decdabf08bc506c042` | `a950f99d00826b23151bac7ed77b881a1110a9da86136a9cb95a00834f32564b` |
| models/economics/saas-subscription-dynamics-eco.json | `3573c1c11cfc9f8e10066bfd639c4a6f697a52a3bc1176b568a425fc756f1651` | `8b3456f724daf4c29ff469f36df5389e2ca4f453f9377a9c187bb3cc5dc6bd86` |
| models/economics/heckscher-ohlin-trade-eco.json | `b553f2c6ca1ee12493e1b85d2e6fbe7f2863dafb8fdff1e0282523ea09a39d0d` | `584ef4a482673d3b14619b18b65788834bcb3820f10683d3799b48d056a88071` |
| models/economics/weitzman-prices-quantities-eco.json | `bfca10da758c678ece20891c0f40062a1c3e55c753603999ad3990353a2e2e18` | `ce906f4ddd4724354e832623d431ba3827d270168d7211a4a261ce0b15485540` |
| models/economics/inflation-expectations-dynamics-eco.json | `f04d1215bdf11d94164e1244a9f9eb2812fdf7873a010fa0c856f6f30c61fa2a` | `fc947a6e1af1a6176c531b63c9a480c608f1b29d1c1857fbbda48357c6939458` |
| models/economics/housing-market-bubble-crash-eco.json | `e9593bca0d0c79de3bf4e351d7f7caca83cd583e381385f9dcefe1e8f331d551` | `34d60fb64c516984270977e4b116b0d2d7ece2dc944353b23998ea43a7ebdd60` |
| models/economics/sales-agent-market-building-dynamics-eco.json | `a2fa77e2a3c28527d1c1196ea10dc89463f4b49c086ddfae8acf66d44cc0018b` | `88ed6ada18887e8f446aec3470143a3db3bac0b4a18f2fabd95bbc1e44a9271a` |
| models/economics/business-startup-fundraising-cycle-eco.json | `ade679126e3065983e3f8cd96abbd6a582f246c448fe85fd23038a236570e753` | `4bec1b14c2d2b0eedfcd38119ef9b4e939c8d81f01530868748516256e037462` |
| models/economics/costanza-natural-capital-eco.json | `849d356312d8b18d6feba0f47e69b50fe19450486a036809d150aa2221155806` | `de3469729b94eb8f4764d135497422bb980a6c596fbf50ff641eedf7c65b8728` |
| models/economics/business-customer-lifetime-value-eco.json | `21f82a728353f31ab2db14ca0ec31788c0eb363d5d711e8c1aa50abddd103be6` | `7a7c02599f55b1a6ad58594a29c94549345c09a3c65150fed10919a1800e4077` |
