# Original-source restorations for 1.4

This pass inspected the original imported examples in `models/other`, separately from generated scientific-domain models. Three definitions were restored. One imported failure remains unresolved because its author's checked-in source itself contains unfinished duplicate definitions. No equations were guessed and no core engine files were edited by this source-restoration pass.

`operations/source-repairs-v14.json` records exact before/after model hashes, pinned source hashes, preserved-field checks, settings and independent numerical evidence. Existing element IDs, positions, equations, stocks, settings, provenance and connectors remain intact except the primitive-type/flow-endpoint restorations described below. Original description text remains as a prefix, followed by an explanation of the example's limits.

| Model | Source finding and repair | Independent check |
|---|---|---|
| School Closure Initial Model | Restore missing adult infection flow and four existing transfer/smoothing auxiliaries as flows. | Seven-state trace against independent DOP853 reference; both age populations conserved. |
| Solow | Restore investment as an inflow and missing depreciation outflow. | Full refined RK4 trace against a closed-form solution. |
| Atmospheric Bathtub | Restore removal as an outflow and original zero-emissions inflow. | Exact Euler recurrences and continuous analytic decay/emission scenarios. |
| Full Beer Model | Unchanged: author source contains conflicting duplicate placeholders. | Exact source/path/hash comparison, including a separate complete but different variant. |

The missing definitions follow a notable historical extraction pattern: AIR, Depreciation, Emissions and the previously restored Sales Agency fraction are each the first substantive definition in their source file. Full Beer also lacks its first parameter. This is consistent with an importer dropping the first definition after the encoding header; the historical importer is not present in the current scripts, so the exact parser mechanism is unproven. These omissions originate in the inputs rather than the numerical integrator.
## School Closure Initial Model

The [pinned SDMR original](https://raw.githubusercontent.com/JimDuggan/SDMR/89bbfe65c25db5bcca511c10ef6527c8ebe35696/models/08%20Additional/04%20School%20Closures/School%20Closure%20Initial%20Model.mdl) defines adult/youth infection and recovery transfers plus a first-order reporting adjustment. The extraction omitted adult infections and left the other stock-changing equations as auxiliaries. The repair adds `AIR` and converts existing `ARR`, `YIR`, `YRR` and `CRR` elements to their source-defined flows, retaining their IDs and positions. Initial stocks and the 0-to-70-day, dt=0.125 grid remain unchanged.

The original conditional spelling remains intact; parser support for that Vensim form is tested separately. Both age groups conserve 5,000 people. A refined RK4 trace is checked against independently integrated golden values at eight times. The original closure flag is diagnostic: it does not modify contact rates, and the closure-duration parameter has no feedback into the source dynamics. Tests demonstrate that boundary. This is an epidemic baseline from an unfinished intervention exercise, not an operational school-closure policy model.

## Solow

The [pinned `Solow.mdl`](https://raw.githubusercontent.com/JimDuggan/SDMR/89bbfe65c25db5bcca511c10ef6527c8ebe35696/models/03%20Chapter/Vensim/Solow.mdl) accumulates investment and deducts depreciation. The extraction had no flows, keeping the machine stock artificially constant. Investment retains its existing ID and position as a restored inflow; the missing depreciation outflow is added. All parameters and the original dt=0.125 remain unchanged.

For the supplied constants, K' = 20√K − 0.1K and K(0)=100. Substitution u=√K gives u' = 10 − 0.05u, hence K(t)=(200−190 exp(−0.05t))². The refined RK4 trace is compared at every sample across the full horizon. This verifies the mathematical example without establishing an empirical economic calibration.

## Atmospheric Bathtub

The [pinned Cookbook original](https://raw.githubusercontent.com/SDXorg/PySD-Cookbook/d7ebddadad9cd87cf796b9b6031ea2b5c45da4c4/source/models/Climate/Atmospheric_Bathtub.mdl) deliberately starts carbon and emissions at zero. Its extraction also lost both stock-changing paths. The repair restores the existing removal equation as an outflow and the original emissions equation as an inflow. The default remains exactly zero, which is faithful to this source.

The checks use explicit unsaved scenarios to expose the restored dynamics: initial carbon 100 decays under the exact Euler recurrence, and emissions 10 produces the expected affine recurrence and continuous exponential solution. Those scenario values are not written into the library. This example is an editable linear reservoir, not a calibrated climate forecast.

## Full Beer remains unresolved for a concrete source reason

The [author's pinned additional-model file](https://raw.githubusercontent.com/JimDuggan/SDMR/89bbfe65c25db5bcca511c10ef6527c8ebe35696/models/08%20Additional/05%20Retailer%20Beer%20Game/Full%20Beer%20Model.mdl) itself defines retailer/wholesaler order rates and wholesaler customer orders twice, including unfinished function placeholders. The local model accurately exposes this ambiguity. Selecting whichever expression happens to run would invent an interpretation.

The same repository has a [separate reader version](https://raw.githubusercontent.com/JimDuggan/SDMR/89bbfe65c25db5bcca511c10ef6527c8ebe35696/reader/Models/08%20Beer%20Game/Full%20Beer%20Model.mdl) with 12 stocks, different stage couplings and a demand shock. The currently imported version has 18 stocks. Replacing it with the reader version would remove six existing stocks and change the modeled experiment. That substitution was not made. The existing failure stays explicit, and both source hashes are recorded for a future deliberate source-version choice.

## Verification

```sh
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_source_repairs_v14.py tests/test_model_investigation.py
```

New regressions are offline and use no AI/provider calls. Existing pinned SIR, SI, SIR Simple and Sales Agency checks remain in the prior investigation suite. Before deployment, back up and replace only the three named model files after checking their old hashes; never synchronize the whole model directory or overwrite user definitions. Refresh the library audit and byte-bound badges after deploying the restored definitions.