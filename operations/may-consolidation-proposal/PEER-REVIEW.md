# Independent May consolidation proposal review

2026-10-24; reviewer dimensional_analysis, not the consolidation author. **Approve the final exact mathematical/source/compatibility proposal below, including its revised visible preset instructions and migration notes.** Active adoption remains subject to publication, staged verification and the scoped transaction/release conditions; it is not performed by this approval. This review executes no transaction and changes no active model, saved definition, runtime or catalog count.

## Source and scientific scope

Independently inspected May's primary1976 article through the [Caltech NED section2 reproduction](https://ned.ipac.caltech.edu/level5/Sept01/May/May2.html) and [section4](https://ned.ipac.caltech.edu/level5/Sept01/May/May4.html). The normalized generation map and higher-period windows support the canonical mechanism and the corrected diagnostic interpretation. The three legacy files differ in illustrative r values and algebraic diagnostics, not in their one-stock update mechanism. No claim is made that their chosen initials, horizon or r values are an original calibrated May dataset. Original publication text/figures/code are not redistributed and no open article license is invented.

The existing opt-in discrete_period=1 contract is appropriate: it fixes the Euler increment encoding to one synchronous generation and prevents other solver/timestep overrides. This does not improve a continuous logistic ODE; it declares a different mathematical object. The canonical proposal keeps actual stock/flow/variable IDs, all initializer/equation arithmetic, connectors and diagram positions. Independently compared its whole element payload with the richest legacy source: only the two expressly declared diagnostic variable names differ; the name/description/time settings changes are separately disclosed.

Instantaneous Log Slope correctly describes one log derivative, not a long-run Lyapunov exponent. Coarse Parameter Range Code no longer certifies dynamics; its99 does not establish chaos. The separate research test's r3.83 stable-period3 counterexample is consistent with the primary source's window discussion. No clamp, invented statistical confidence or global chaos classifier was introduced.

## Independent numerical/compatibility verification

Re-ran consolidation tests alone:6passed in0.54s. Re-ran consolidation plus the earlier source/contract research tests: **27passed in1.08s**, one preexisting Pydantic settings warning. Separately checked every current active source/archive hash, canonical stock/flow/connectors/variable payload preservation and generation-map residuals for all three presets (residual below5e-16). Current active files still match the proposed before hashes.

The compatibility mapping is precise. r3.7's Growth_Rate means constant parameter r, while r3.8's Growth_Rate means r*(1-Population); they must not share a naive alias. Recomputing1-1/r and its deviation preserves the legacy operation order rather than claiming bit-exactness from algebraic equivalence to(r-1)/r. The richest old diagnostic columns map to the two new honest names. Full original output arrays, time grids and hashed receipts were verified against actual simulations, not inferred from titles or matching final values. Exact long-chaotic-trace parity here follows preserving the same operations/default grid; it is not proof of chaos or numerical shadowing.

Read the actual compare_scenarios implementation and exercised the author's real-tool test. SCENARIOS.json uses supported model_id/scenarios/name/parameters fields, existing r and Population names, and three valid finite cases. The tool deep-copies the canonical model, retains its declared period and only returns summaries. Saves are trapped and the canonical JSON remains unchanged. Presets therefore work through the actual current API/MCP mechanism; the file does not pretend they are automatically installed in a browser menu or that the summary endpoint returns full trajectories.

## Compatibility and discoverability gates

The proposed two retirements are justified as mechanism consolidation. The final revised canonical description now contains explicit preset/edit/run/Save Run/Compare instructions, former titles/IDs and migration limits. DISCOVERABILITY.md and docs/MAY-MODEL-MIGRATION.md give matching guidance. I verified the existing Inspect element selection, name/description library search and chart comparison source paths. No redesign, ignored scenario field or automatic save is introduced. Remaining release boundaries are:

1. Keep the existing editor/parameter/run controls. The reviewed visible instructions explicitly state r=3.7,3.8or3.9, Population initial value.1,100whole generations and Euler period1. Existing controls make each case usable without a new menu/schema. They explain that Equation edits intentionally change the current draft and Save is separate. Save Run/Compare stores trajectories, not persistent parameter presets, and generated labels require parameter notes. If a public preset/help link is later supplied, publish it first; none is falsely promised by this proposal.
2. The reviewed migration draft provides the required small old-ID mapping/retirement note; publish it before execution: may-logistic-chaos ->canonical+r3.7, may-ecological-chaos-eco ->canonical+r3.8. If public routing supports redirects, that is useful separate reviewed work; do not claim this package implements them. Preserve user/private saved copies and make diagnostic-column name changes explicit to consumers.
3. Preserve JSON export and both export controls. The reviewed actual GET/POST XMILE wrapper now returns actionable422instead of a generic500, and the separately approved UI shows bounded plain-text JSON guidance. Unsupported XMILE should continue to reject rather than silently lose the period. Root's browser verification is recorded in its separate review; this reviewer did not repeat a native visual walkthrough.

No additional engine, invented Model.scenarios field, new saved-state write or automatic output-column migration is warranted by this proposal. The final canonical metadata revision changes only description relative to the committed prior proposal; all numerical/settings/element payload remains unchanged. Its final SHA-256 is bound below. Any further candidate-byte change requires refreshed receipts and focused review.

## Bound decisions

These hashes bind the proposed2retire/1replace math/identity assessment, not deployment authorization. PLAN.json counts are explicitly conditional baseline arithmetic and preserve unrelated/private definitions.

| Action | Active path | Before SHA-256 | Proposed replacement SHA-256 |
|---|---|---|---|
| retire | models/other/may-logistic-chaos.json | `7abd9c5fe02d34703228bea243e6cdade562db9c833cf45c4c6f94c4a96d30c8` | No replacement at this ID |
| retire | models/economics/may-ecological-chaos-eco.json | `91ef1ec605080528bdece04cae503e9c72bab9adc6aaaf6096a89ce4313140bd` | No replacement at this ID |
| replace | models/economics/may-chaos-population-eco.json | `7e303bdb46e3e542d32f94e0690f735da5b4cc30ea755b5801a957b6d3976518` | `3672076ba0f4ffc68c4d23d046503db7197af2dcd493411caefbf5f0de91ff86` |

## Final metadata and combined-plan rereview

Independently verified final canonical SHA-2563672076ba0f4ffc68c4d23d046503db7197af2dcd493411caefbf5f0de91ff86 and a description-only change versus the committed prior proposal. Re-ran7consolidation and31metadata tests: **38passed in0.56s**, with one preexisting Pydantic settings warning. The read-only combined checker reports29actions,27replace,2retire,0active writes.

Separately matched every combined action against its approved source manifest: all26NSIDC replacements use exactly the reviewed before/after/archive hashes and source paths, and the remaining three actions equal the final May plan verbatim. All targets/IDs are distinct. Dependency hashes bind the final metadata manifest, May plan and migration draft. The conditional995->993public and1008->1006live arithmetic preserves the stated13private models; it is proposal arithmetic, not a fresh deployed-host inventory. No database path or unrelated model target is included.

The combined plan remains a proposal, not an executable authorization or proof of safe deployment. Existing transaction preflight/backup/rollback, publication of migration notes, inclusion of export fix72cef78, staged baseline/private inventory and browser preset/export/comparison checks remain release duties. The source/compatibility/discoverability content itself has no remaining mandatory review fix.

| Reviewed package file | SHA-256 |
|---|---|
| operations/may-consolidation-proposal/PLAN.json | `ec7d0d2a0f2b2d3339d8d4bb740a8590dc0ed4cfdc7a2d3cb00051bb2b040f98` |
| operations/may-consolidation-proposal/SCENARIOS.json | `bdd93cba307089ec281e54f6bec6540a94d8c1f48d1972baf07f7124a9b1edee` |
| operations/may-consolidation-proposal/OUTPUT-COMPATIBILITY.json | `f2d5bf1b6bc8257d3fac6333dfd21dde827055a34cbe895f001b4958acece636` |
| operations/may-consolidation-proposal/DEFAULT-REFERENCES.json | `2570e4433dbb715db9d0495c82b4641bce5fd57d062b3b7026253bfd41626293` |
| operations/may-consolidation-proposal/README.md | `467981c1a00d31c41d3fd7b43abfb09067d502e0782815560c42c655d1128ec4` |
| operations/may-consolidation-proposal/test_may_consolidation.py | `af2801274cae8dff41f0e8deb2304fd676041e1e41885b257de1aa11ca664c6f` |
| operations/may-consolidation-proposal/DISCOVERABILITY.md | `4f6466073605304a3b51d465902ec59c1fdc13a1a071382ee892ddde2e52026b` |
| operations/may-consolidation-proposal/PRESET-DESCRIPTION.txt | `1f52e9fa5d0eb36096127e688102f1b3ca8e6350f24374cab372889eec7fa173` |
| docs/MAY-MODEL-MIGRATION.md | `1069fa8f2002da30dbc742f97b61f7494b433cbbf6d28229918ef4ca8ea4c129` |
| operations/quality-followup-proposal/PLAN.json | `a0bd75fe2d26bca4aaeac2df30fdd4139933178bfaefca603635992453cd633c` |
| operations/quality-followup-proposal/check_plan.py | `53bb4cfb8121b43ad0b4e3609c4b9c3d47f81f8a33514b616544c37c153bee59` |
| operations/quality-followup-proposal/README.md | `da015f9b092f41596b6a6733e21a208c5a6826e23a348b7d70cee803005e3f92` |
