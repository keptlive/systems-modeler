# Independent local sensitivity UI review

2026-10-24. Reviewer: dimensional_analysis, not the UI author. **Approved at the exact hashes below after two review findings were fixed.** This is source/behavioral review; visual browser verification remains the integrating maintainer's responsibility. No UI/runtime/test source was edited by the reviewer; only this review document was written.

## Preservation and integration

Read the existing Inspect implementation, App.modelSnapshot/readSimulationSettings, the local sensitivity transport/core contract and the new module/test/docs. The index change is exactly one additive script include. Existing validation, investigation, editor, import/export, Save, simulation, charts, analytics, AI and resource navigation remain present. The module adds a collapsed section within the existing Inspect body; it neither replaces its other sections nor repurposes raw variance as parameter sensitivity.

The module deep-clones the inspection snapshot and captures the current draft fingerprint separately. It does not assign App.model, save, load, Simulation results, Charts or Analytics state. Its POST targets only the read-only local sensitivity endpoint; the JSON report download is separate from model export. The test freezes simulation sentinels and verifies the input model/simulation serialization is unchanged. This does not certify every preexisting UI path visually, but no removal or state-mutating path was found in the reviewed diff/module.

## Request/result semantics

Selections use immutable stock and variable IDs, display names/IDs/value/unit annotations, and require explicit positive finite absolute h. Computed variables are excluded from selector discovery, duplicate IDs are rejected, and rows are bounded to eight. Client literal recognition is discovery only: server admission remains authoritative, so malformed/unsupported literals or model semantics fail visibly rather than being silently coerced. No client-generated expression is executed.

Reports display final baseline output, supplied output/parameter derivative units, actual final sample time, elasticity unavailability reasons, refinement/asymmetry warnings, precision/underflow cautions and perturbation failures. Full settings/sample/work/provenance remain downloadable and visible in details. Missing units remain unknown rather than invented. Strings are inserted using textContent; the inert script-text regression verifies no element creation from model/report text. The UI does not label local derivatives as global importance or confidence intervals.

The form refuses a run after draft changes relative to its captured fingerprint. If a draft changes during execution, the report is identified as belonging to the inspected snapshot. Form-selection changes now invalidate previously rendered results (see fixed finding1). A reopened/replaced Inspect body disposes the old session and aborts its request. Serial/disposed/aborted guards suppress late responses. Close and Cancel request cancellation without claiming server cleanup is already complete. Controls/busy state recover in finally. The35second client timeout exceeds the bounded server default; it now publishes a terminal status independently of promise settlement (fixed finding2).

## Findings fixed before approval

1. **Stale experiment presentation:** successful results originally remained after changing the output, parameter or step, or adding/removing a row, while the main result heading did not identify a prior experiment. Independently reproduced with the actual module in a scratch DOM harness. Author added input/change invalidation and explicit add/remove invalidation, clearing the table and explaining that the current selections need a new run. Added regressions exercise both events and row operations. Resolved.
2. **Timeout late-success status:** an independent fake35second timer probe aborted a request that later resolved successfully. Guards correctly suppressed results, but the status stayed Running because only the catch branch set the timeout message. Author now publishes terminal timeout/cancellation-request status directly in the timer callback, guarded by session/serial validity. A late-success regression verifies no result rendering and the terminal message. Resolved.

No remaining mandatory fix found within this scope. Native fetch abort normally rejects, but the second hardening also handles delayed/mocked successful settlement honestly.

## Executed verification and limits

Independently ran `tests/test_local_sensitivity_ui.py` on the final freeze: **1 passed in0.25s**. The single Python test executes numerous assertions against the actual JavaScript module in a Node DOM harness: additive mount/idempotence, ID/step payloads and rejection paths, units/warnings/failures/inert text, preservation, selection invalidation, stale-draft refusal, typed server errors, Cancel, close, disposal, timeout and late response suppression. An earlier independent scratch probe established each reported finding rather than inferring it from titles or comments. `git diff --check` passed.

The lightweight DOM does not prove browser rendering, native dialog/focus behavior, mobile layout, assistive-technology behavior or actual HTTP worker cancellation. Existing backend contract/transport tests and the integrating maintainer's browser walkthrough remain separate evidence. Approval here is not a numerical-core or deployment approval.

| Reviewed file | SHA-256 |
|---|---|
| static/js/local-sensitivity.js | `91c8357b51f4b723bc7e8b1d93fc5d107fdd5b9293e22bbc4afd2d7df1225579` |
| tests/test_local_sensitivity_ui.py | `20ec698fed49f6bc76f5cf416f399c6ce4b1153556c03c89cbfb138ecbeb7eb3` |
| docs/LOCAL-SENSITIVITY-UI.md | `b3d8434804e088c16a7c225de1a918f1156ffa684d0e2e8dfb9bc87106b51169` |
| static/index.html | `5ece6c555282262a02f2336d2b95e1691f8a6d5cb881c9005c18148d189e43a0` |

Hashes bind the whole files at review time; unrelated later index edits should be reviewed as a new additive integration diff. Any module behavior change requires revalidation.
