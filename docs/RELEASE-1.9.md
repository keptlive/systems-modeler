# Release 1.9 — source reconstruction and engine contracts

The full public corpus completes **1,050 of 1,078 definitions**, up from 1,031. Nineteen previously failing definitions now complete their full horizons. All 47 prior failures have source investigations and causal explanations; 28 remain explicit failures. No previously completing default regressed.

## Evidence behind the repairs

- Restore the native weekly Beer Game, twenty-state urban dynamics, workforce/overtime model and all 351 Massachusetts population outputs. Tests compare complete stock trajectories against independently transcribed source balances or linear recurrences.
- Reconstruct carbon, ocean heat, solar irradiance, phosphorus and World3 resource examples using original equations and actual source tables. Check mass/energy accounting, source data and applicable refinement; explicit scenario assumptions remain visible.
- Repair grid energy/frequency accounting, delayed SEIR initialization and labor initialization. Select a stiff solver for the unchanged market-share equations.
- Rebuild Lorenz convection, reactor kinetics, pipe flow and perpetual option valuation from primary equations. Check short-time analytic/reference behavior, conservation, domains and full-horizon bounds. Teaching examples are not calibrated real-world predictions.
- Replace the incorrectly continuous technology persistence with an explicitly named fixed-saving AR(1) discrete growth illustration. It is not advertised as a complete equilibrium RBC model.

See source partitions [A](CORPUS-REPAIRS-1.9-A.md), [B](CORPUS-REPAIRS-1.9-B.md), [C](CORPUS-REPAIRS-1.9-C.md) and the [complete failure register](FAILURE-REGISTER-1.9.md). Original definitions and precise field changes are retained in SHA-bound receipts. Native reporting horizons or conventions that differ from the saved scenarios are stated explicitly.

## Engine and interface

The limits-to-growth archetype now retains its authored categorical System State through an explicit report channel. Report values are evaluated after each retained state and displayed separately from numeric charts. Text cannot enter dynamics, report dependencies are rejected, and work/text capacities are enforced. JSON and MCP preserve typed outputs; XMILE rejects unsupported reports explicitly.

Discrete-period models require the source period, Euler and a whole number of intervals across the API, MCP workspace edits and interface. Fractional-step investigations are marked inapplicable. Independent review found and fixed a targeted-edit contract loss and two floating-point interval defects. See the [contract](ENGINE-REPORTS-AND-DISCRETE-1.9.md) and [independent review](INDEPENDENT-REVIEW-1.9.md).

Large charts initially select stocks while every numeric series remains searchable. Existing controls, analytics, saved models, exports, mobile panels and legacy SSE transport remain available. The production favicon is preserved.

## Engine hardening

Independent adversarial reviews found silent numerical faults: opposing flows could cancel a small real inflow, RK4 intermediate weights could overflow despite a finite answer, fixed-delay samples could shift at large time origins, invalid scalar intermediates could be hidden in conditions, and unresolved declared constants could bind to mathematical constants. These are fixed with analytic, conservation, permutation, phase-invariance and domain regressions. Dependency retries now count toward work limits. Failures retain generated seeds, original causal chains, effective settings and exact engine/model fingerprints.

Radau rejects uncertified state jumps and state-driven lookup forcing in differential equations until event-aware integration is supported. Five saved defaults now use independently checked explicit grids; no dynamical equations were changed for this adjustment. Their default errors and refinement behavior are stated, including nonmonotone threshold-grid phase error. See [integration](ENGINE-HARDENING-1.9-A.md), [equations](ENGINE-HARDENING-1.9-B.md), [API/MCP](ENGINE-HARDENING-1.9-C.md) and [five solver repairs](CORPUS-HARDENING-REPAIRS-1.9-B.md).

Partial REST settings inherit omitted saved values. MCP preserves structured failures. Duplicate targeted IDs, non-finite results and invalid Unicode are rejected before ambiguous edits or transport failures. XMILE export translates supported scalar syntax and functions to core spellings, preserves table precedence, and rejects unsupported or seeded-stream-changing conversions. The [export audit](XMILE-INTEROPERABILITY-1.9-C.md) records the exact subset.

The results, analytics and fullscreen views offer a styled failure-report download. The actual browser JSON replay reproduced the exact causal error and engine fingerprints. Edits invalidate stale successes and failures, including numeric/report role changes. Existing paths remain available.

## Validation

The final full-horizon audit runs all 1,078 checked-in definitions: **1,050 complete and 28 fail explicitly**. It binds every model and engine file by SHA-256. Nineteen of the original 47 failures are repaired; the final release changes 23 definitions including four additional solver defaults. Completing a run does not establish empirical validity.

Thirteen JavaScript module suites pass. Real local MCP HTTP, legacy SSE and stdio checks pass. Browser checks cover typed reports, fixed-period controls, all 351 town outputs, styled failure diagnostics and actual JSON replay. Physical devices, Firefox and Safari remain unverified.

Three expected failures remain explicit XMILE identifier compatibility cases. The separate aggregate model test intentionally fails while 28 library definitions remain unresolved; it is not included in the product regression suite. Remaining inputs require missing original equations, cohort/initial data or physical-law reconstruction; the [register](FAILURE-REGISTER-1.9.md) identifies those gaps. No arbitrary clamps or invented parameters were used to turn failures into passes.

The sanitized public checkout and isolated production dependencies each pass **1,256 tests plus 18 preservation subtests**, with the same three documented XMILE identifier expected failures. Live HTTPS MCP HTTP/SSE checks pass. All 24 deployed runtime files and 23 reviewed model replacements match; every other model and the database remain unchanged across 1,092 checked data files. The 13 production-only definitions are separately audited: 11 complete and 2 fail, unchanged.
