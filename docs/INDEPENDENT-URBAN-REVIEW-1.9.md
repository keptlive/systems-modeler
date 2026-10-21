# Independent URBAN source review, v1.9

The restored urban definition matches the declared native baseline equations. No blocking omission, stock-balance, lookup, initialization, unit or alias defect was found. The independent review checks the native MDL itself; it does not treat agreement between two consumers of the generated equation map as sufficient evidence.

The retained native file has SHA-256 `fe7bbd0a26897d2ad2152d6390e3d544dcd861c2ab52eda3922a27a8b49465a4` and records the Forrester appendix model's 1974 copyright. Its [official Vensim source URL](https://vensim.com/documentation/Models/Sample/URBAN/URBAN.mdl) is retained. Fresh retrieval was unavailable during this review; the byte-verified source fixture, complete pre-sketch equation section and official function documentation were inspected.

## Coverage and independent mathematics

The [independent review tests](../tests/test_independent_urban_v19_b.py) use a separate equation/unit field reader over the raw MDL. The native source has **255 equations: 20 INTEG declarations, 231 auxiliaries and four simulation controls**, plus **53 lookup tables**. All are accounted for. The runtime has 20 native stocks, 20 explicit net-balance flows, 231 native auxiliaries and two compatibility aggregates. Simulation controls map to settings rather than additional dynamic nodes.

Every native equation and unit string is compared directly with the generated map; every lookup's entire point sequence is compared with the model. Reference evaluation and its 20 state derivatives are compiled directly from raw source expressions without reading the generated map. They match the runtime at three independently perturbed positive stock vectors and at every yearly sample over 250 years. This supplements C's separately handwritten 20-balance reference.

The complete balance review covers:

| Native level group | Balance review |
|---|---|
| New Enterprise, Mature Business, Declining Industry | Construction, enterprise maturation, business decline and industry demise signs match their native declarations. |
| Labor, Underemployed, Manager Professional | Birth, arrival and departure terms match. Labor promotion and underemployment transitions have equal and opposite entries in the appropriate stock equations. |
| Premium Housing, Worker Housing, Underemp Housing | Housing obsolescence passes between categories with matching signs. Construction and demolition terms appear in the correct compartments. |
| New Enterprise Average, Premium Housing Average, Worker Housing Average | All three averaging tendencies and symbolic initial equations match the native growth-rate-adjusted formulas. |
| Labor Ratio Perc, Labor Arrival Mult Perc, Labor Mob Mult Perc, Underemp Mob Mult Perc, Underemp to Labor Perc, Manager Prof Arriv Mult Perc, Tax Ratio Needed Perc, Attract Migr Mult Perc | Each of the eight perception integrators uses the correct source input, perceived level and time constant. No perception rate is silently treated as a population count. |

Source typos such as `premium housing contruction`, `labor daparture` and `worker housing obsolescense` remain consistently mapped. Normalized identifiers have no case-insensitive collisions. The `Underemp to Labor Perc` stock legitimately has units worker/year, so its derivative has units worker/year²; it is a perceived rate, not another worker population.

## Source semantics

All six native `GAME(0)` inputs become zero in the baseline. This follows Vensim's [normal-simulation GAME semantics](https://www.vensim.com/documentation/fn_game.html): the argument is returned unless a gaming intervention changes it. No external CIN file or interactive intervention is claimed. The urban system itself is dynamic; these zeros are source policy inputs rather than fabricated constant trajectories.

The native lookup format lists all x values followed by all y values. All 53 tables are decoded that way, preserving every point. Tests check each knot, each interval midpoint and both out-of-range endpoints against an independent interpolator. Linear interpolation with constant endpoint extension agrees with [Vensim's lookup documentation](https://www.vensim.com/documentation/22820.html).

Native initial time 0, final time 250 and integration step 1 are preserved. Symbolic initial values are evaluated from native dependencies: New Enterprise Average 140, Premium Housing Average 3500, Worker Housing Average approximately 14700, and Tax Ratio Needed Perc equal to initial tax ratio needed. The default population is **113100 persons**, using the source's family sizes, rather than an unweighted sum of the three worker-category stocks.

The original native `SAVEPER` is **5 years**. The application retains annual output at the integration step of 1 year. This is denser reporting of the same native Euler trajectory; identical native output cadence should not be claimed. All five-year native report points are included. Half/quarter grids are numerical refinement of the native ODE approximation, not changes in the source parameters.

## Compatibility boundary

Old IDs `s1`, `s2` and `s3` map respectively to housing-unit total, job-slot total and the source's family-weighted person population. Their compatible old geometry is retained. `s4` Infrastructure has no native counterpart and is explicitly archived in the repair receipt, rather than given invented dynamics. The reconstruction replaces the unsupported generated hybrid with the complete historical source system; it should continue to be described that way, not as preservation of the former four-stock quantitative model.

The source's historical category definitions and numerical coefficients are not contemporary urban calibration. This review supports the declared source reconstruction and numerical mapping, not a predictive use of those assumptions.
