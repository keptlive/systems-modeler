# LOOKUP source restoration, version 1.6

Three previously failing teaching models now recover their original graphical functions and source equations. This is a bounded source reconstruction, not certification of ecological or organizational realism. No engine, interface, integration setting, existing node identity/name/position, stock initial value, flow link or connector changed. Actual source parameters are preserved; five zero-valued table placeholders become evaluated curve outputs while retaining their original nodes.

`operations/lookup-source-review-v16.json` records exact old/new model SHA-256 hashes, every changed field, source-file hashes, the original table points, the complete native-reference CSV, source name mappings and numerical/semantic limits. Verification is offline:

```bash
python -m pytest -q tests/test_lookup_sources_v16.py
```

## Sources and recovered semantics

| Local definition | Pinned original implementation | Recovery |
| --- | --- | --- |
| Hares and Lynxes | [Native Stella sample](https://raw.githubusercontent.com/SDXorg/test-models/21aab02739dc5187bc9564e4d3de14e575905d2f/samples/bpowers-hares_and_lynxes_modules/model.stmx), [canonical CSV](https://raw.githubusercontent.com/SDXorg/test-models/21aab02739dc5187bc9564e4d3de14e575905d2f/samples/bpowers-hares_and_lynxes_modules/output.csv) | Two graphical functions; punctuated birth/death/harvest references; preserved scalar module wiring |
| Capability Trap | [Capability Trap.mdl](https://raw.githubusercontent.com/SDXorg/PySD-Cookbook/d7ebddadad9cd87cf796b9b6031ea2b5c45da4c4/source/models/Capability_Trap/Capability%20Trap.mdl) | Three graphical functions and their work/improvement inputs |
| Rookies and Experts | [Rookies Demo Model.mdl](https://raw.githubusercontent.com/SDXorg/PySD-Cookbook/d7ebddadad9cd87cf796b9b6031ea2b5c45da4c4/source/models/Rookies_and_Experts/Rookies%20Demo%20Model.mdl) | Seven-point hiring response and exact references to hyphenated hour variables |

The source repository revisions are `21aab02739dc5187bc9564e4d3de14e575905d2f` and `d7ebddadad9cd87cf796b9b6031ea2b5c45da4c4`. Source files were fetched directly, not inferred from model titles or fitted to application output. The adjacent Cookbook folders contain the `.mdl` files but no native canonical CSV; those two cases therefore use independent source-RHS checks rather than claiming native Vensim trajectory reproduction.

The [Vensim manual](https://www.vensim.com/documentation/22820.html) specifies linear interpolation and endpoint holding for ordinary lookups. The [XMILE standard](https://docs.oasis-open.org/xmile/xmile/v1.0/os/xmile-v1.0-os.html), sections 3.1.4 and 4.3.3, likewise defines continuous graphical functions with clamped endpoints and makes continuous the default. Consequently all six recovered curves explicitly use `interpolation: continuous`; the historical JSON default of extrapolation would be incorrect here. Vensim's square-bracket editor ranges are not extra data points.

Existing placeholder nodes remain visible. Their equations now evaluate the recovered data at the same source input, and downstream expressions use those values. Separate table data supplies the graphical functions without deleting or replacing old node IDs. This adds redundant display outputs in the two models that formerly had placeholder nodes; it does not add a new behavioral mechanism. The engine's supported `LOOKUP(table, input)` form is used explicitly. No broader foreign-dialect support is claimed.

## Hares and lynxes: complete native-grid comparison

The native sample has a root model and two linked modules. The existing scalar file had retained the two principal stocks but lost both curves and referenced undeclared table aliases. Birth/death fractions and the one-time harvest also used identifiers that did not exactly match punctuated local names. Restoring the explicit source mapping fixes these without changing any local initial value or time control.

The source kill curve is linear over eleven points from 0 to 500. The lynx-mortality curve has eleven points from density 0 to 100; its final value is approximately 0.00673794699908547. The complete preserved Euler default runs from 0 through 12 at 0.5 intervals. Every one of the original CSV's **25 time points and 14 reported series** is compared, including both stocks, flows, rates, density and the harvest. Maximum absolute differences are approximately 3.97e-7 for hare stock and 4.17e-7 across the reported series, consistent with the CSV's printed precision. The original CSV already exercises mortality endpoint holding above density 100, so matching it rules out an accidental extrapolating-table reconstruction. The harvest removes a total of 100 animals over its single pulse.

The [sample README](https://raw.githubusercontent.com/SDXorg/test-models/21aab02739dc5187bc9564e4d3de14e575905d2f/samples/bpowers-hares_and_lynxes_modules/README.md) attributes `output.csv` to Bobby Powers, August 28, 2015, using Stella 10.0.6. The currently pinned native file has a newer Stella Architect 1.4 header. These are distinct provenance observations: the comparison uses the repository-provided canonical CSV, not a new native run or an assertion that the current native file was authored in 10.0.6.

**Semantic boundary:** the native file explicitly declares nonnegative stocks and flows. This scalar engine cannot encode those constraints generally. All baseline stocks/flows remain positive and match the canonical series, but that does not establish equivalence for arbitrary scenarios. An unsaved harvest-10,000 counterexample produces negative lynxes; the test retains this limitation explicitly instead of adding an invented clamp. General native-module and nonnegative-constraint support remains outside this repair.

## Capability trap: exact tables, retained source caveat

All three point arrays are present in the pinned `.mdl`, including the work-pressure/improvement table as the first definition after its encoding header. The local file instead had zero-valued placeholders and mismatched table aliases. The recovered curve nodes feed the original working-time and improvement equations; the source spelling `Time Spend on Improvement` maps to the existing local `Time Spent on Improvement` node. No historical importer mechanism is claimed or patched.

The default is an exact equilibrium: capability 100 and both pressures 1. A zero-motion trajectory alone would not validate the repair. Tests also evaluate full 1,601-point trajectories for the existing performance-step input set to 500, with pressure-step input 0 and .01. An independently written literal source-RHS Euler calculation supplies the expected states. Every source knot, segment midpoint and out-of-range boundary is checked separately.

The source author calls the working-time formulation “not quite correct” and notes conflation of work pressure and improvement time. This warning remains in the model and receipt. Matching this teaching implementation does not resolve that modeling problem or establish empirical calibration. Irrelevant original description/citation claims are replaced with the actual pinned implementation reference.

## Rookies and experts: table callable versus evaluated output

The source defines a standalone seven-point hiring lookup and invokes it at backlog pressure. The local file represented that as an unsupported inline `LOOKUP(input, list)` expression, then attempted to call the resulting scalar as a function. The recovered table and evaluated auxiliary retain the original node; hiring uses that evaluated value. Quoted references restore the original hyphenated hour-variable identities without changing engine aliases.

Tests compare the complete 4,801-point stored Euler grid against an independently coded source recurrence for rookies, experts, backlog, hiring and task completion. This checks the supervision coupling and all stock-flow signs, rather than merely observing finite values. All curve knots, segment midpoints and exterior values are checked too.

The source directly caps a task-completion rate by the backlog stock, retaining an implicit dimensional assumption. Supervision can also exhaust expert productive time in other scenarios; no unsupported productivity floor is inserted. The restored source is a teaching example, not evidence of fitted organizational behavior or universal positivity.

## Disposition

These three saved defaults complete and now provide source-backed positive LOOKUP cases. A full library rerun is separate; this scoped review does not recalculate the corpus-wide totals. Original native output agreement, independent source-equation checks, source completeness, physical constraints and calibration remain separate evidence categories. The remaining nonnegative/module limitations and source-authored caveats must survive any release or user-facing status report.

The scoped suite completed **12 passed in 31.96 seconds**. Its receipt confirms unchanged engine hashes, exact model after-hashes, original structure/input preservation and all per-series native-reference error measurements.
