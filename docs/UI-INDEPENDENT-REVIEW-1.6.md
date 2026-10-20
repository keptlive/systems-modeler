# Independent UI integration review 1.6

Reviewed the coordinating reviewer's studio shell, index resource order, mobile expansion and result-summary changes; also reviewed the subsequently frozen app.js property transaction and mobile ordering patch. No shell/app/model code was changed by this reviewer. The diagram renderer was authored by this reviewer, so the geometry integration findings below are verification of authored work, not an independent aesthetic assessment of it. Actual browser checks are performed by the coordinating reviewer because this runtime exposes no browser surface.

## Findings and corrections

1. **Settings focus could override an intentional property selection.** The new settings-close observer initially restored its opener unconditionally. Inspection closes its native dialog and settings overlay, then intentionally focuses the selected element's property field. A later observer callback could steal that focus. The observer now restores only when focus remains inside the closed overlay or on the document body. The coordinating reviewer confirmed the actual Settings → Check inputs → Infection path closes both overlays and focuses `prop-name`.
2. **Command finder could stack over an unapplied settings draft or library overlay.** `WorkbenchTools.open()` initially checked native dialogs only. It now also blocks active settings/library overlays. Added checks to `check_workbench_v15.cjs` execute the real method with each protected state and verify normal opening otherwise. Actual Settings focus and Ctrl K blocking were confirmed by the coordinating reviewer.
3. **Mobile fullscreen could survive a programmatic/Escape close.** The preexisting expansion script reset only for explicit Close/overlay clicks. The class observer now resets fullscreen, body overflow and button state whenever the sheet exits `.open`. `check_studio_v16.cjs` executes the actual script, verifies explicit and programmatic closures, and confirms the observer does not repeatedly mutate an already closed sheet.

The inherited labeling gap on the three ×-only close buttons is also closed: settings, mobile panel and fullscreen now have explicit accessible names. Existing Cancel/Escape routes remain available.

No remaining blocking regression was found in this bounded code review after these corrections. This does not certify all user journeys or accessibility across platforms.

## Feature and state preservation

Studio icon replacement changes children of existing buttons, retaining IDs, event handlers and title-derived accessible names. Simulation-owned Run/Animate labels remain state-owned. The assistant toggle has explicit controls/expanded semantics, retains the chat DOM/state and uses the existing resize observation without rewriting node positions. Existing library, import/export, save, chart modes/scenarios/analytics/AI and agent controls remain present.

The final-value summary is an ordinary keyboard-operable details/summary disclosure. All series values remain available; this change does not alter trajectory or chart selection state. Mobile chart-first ordering retains all chart, scale, series, summary and analytics/AI hooks and controls. Resource order loads studio styling before diagram semantics, and all changed resources have versioned URLs.

Atomic rename computes token-aware equation rewrites and endpoint updates before committing. It preserves built-in/table call namespaces and IDs; collision, ambiguity and unsupported syntax errors leave the model unchanged. Numeric initial-value drafts do not commit blank/nonfinite values and restore the last applied value on final invalid change. Both desktop/mobile handlers are exercised by the focused property checks. These editor safeguards do not reconcile an already malformed scientific definition or add unsupported engine semantics.

Diagram integration uses shared node dimensions for clipping, hit areas and Fit. Native names/units and full ARIA labels remain available; Enter/Space uses the existing selection/connect route and restores node focus after rendering. Self/coincident dependency curves remain finite, and overlapping material primitives do not emit backwards arrows. No autolayout, equation or position mutation is performed by rendering. Mouse/touch/pan/zoom behavior retains the established handlers; actual rendering and interaction verification belongs to the browser evidence.

## Verification

The following real-code Node checks independently passed in the current working tree:

- `check_frontend.cjs`: all frontend scripts parse and prior numerical frontend checks pass.
- `check_simulation_state.cjs`: stale asynchronous simulation/analytics result fencing.
- `check_workbench_v15.cjs`: ranked search, delegation, mobile property focus, truthful status precedence and active-modal boundaries.
- `check_series_controls.cjs`: filtering/selection with result/color preservation and small nonzero labels.
- `check_diagram_v16.cjs`: finite clipped/self geometry, fit containment, label wrapping, hit zones and unchanged positions.
- `check_property_inputs_v16.cjs`: atomic rename/rollback/collisions, both numeric inputs and mobile control preservation.
- `check_studio_v16.cjs`: fullscreen button/close/overlay/programmatic exit and nonrepeating observer behavior.
- `check_notifications_v16.cjs`: actual notification method, native/settings/body ownership priority, safe message text, alert/status roles, persistent errors, six-second status expiry and focus restoration on dismissal/expiry.

The coordinating reviewer additionally reported actual native rename of Susceptible to Susceptible Population updating quoted flow references, endpoints and diagram labels. Browser outcomes, viewports and screenshots should be recorded in the release's UI QA document; code checks are not a substitute for them. Physical devices, Safari/Firefox, screen-reader operation, high zoom and slow/offline behavior remain unverified unless separately documented. No deployment or commit performed by this reviewer.

## Final notification delta

Replacing the blocking error alert with a dismissible DOM notification preserves the message and provides alert/status semantics. Errors remain until dismissed or replaced by a later notification; other statuses expire after six seconds. Message insertion uses textContent, and the controls remain within the active modal owner.

Two concrete issues were found and corrected during this final delta. A combined CSS selector selected the earliest matching modal in document order, which could attach a notice behind a native top-layer inspection dialog. Explicit native-dialog → settings-dialog → body priority now selects the correct owner. Removing a keyboard-focused Dismiss button could also leave focus on body outside the nonnative settings trap; dismissal and expiry now restore a connected prior focus within the owner or fall back to its first enabled field. The new deterministic actual-method notification check passes for nested owners, dismissal, expiry and removed-prior-field fallback. Browser keyboard verification remains the coordinating reviewer's responsibility. No further blocking issue was identified in the reviewed delta.