# Actual browser QA — 1.6

Baseline and preservation scope are recorded in UI-DIRECTION-1.6.md. Tests use the actual application through the in-app Chromium browser, not static mockups. Only unsaved local draft elements were edited during destructive-control checks. No saved user model was deleted or overwritten.

## Verified interactions

- Anderson-May diagram: all four stocks, four flows and eleven variables render with full accessible names and wrapped visual labels. Material pipes and dependency lines are distinct. Fit, zoom and the reversible assistant-panel toggle retain the model.
- Keyboard Enter selects stocks and flows, renders the appropriate properties and preserves visible focus after SVG rebuilding. A temporary Stock 5 was placed, dragged, connected to Beta, selected and deleted; its new connector disappeared and the original model completed 366 samples again.
- Native text entry renamed Susceptible to Susceptible Population QA in an unsaved draft. The Infection equation gained the quoted new identifier; its stock endpoint and visible connector labels followed. The renamed model completed 366 samples. Reload discarded this local test draft.
- Clearing the initial-value field preserved/restored 100000. Error feedback was subsequently upgraded from the old blocking alert to a persistent dismissible notification; the final notification implementation has independent DOM-method tests.
- Settings focuses Start Time. Ctrl+K does not open a competing command dialog. Settings → Check inputs → Infection closes both dialogs and intentionally focuses the property Name field, rather than returning focus to the settings opener.
- Invalid zero DT produces a validation notice while retaining the settings draft. Keyboard Tab → Dismiss → Tab stays inside settings. The step estimate was corrected to show an invalid-draft message instead of the previous substituted-DT count.
- Desktop final values use a native expandable disclosure. Chart-series Stocks/All/Clear remain available. Phone results retain Chart, Stats and AI, all chart modes, filtering and final values, with the chart now first.
- At 390 × 844, stock-series chart, controls and filter remain readable; unselected chips are outlined rather than faded to unreadability. Fullscreen has a distinct exit icon. Escape closes the sheet and resets fullscreen; reopening restores the normal sheet and its Expand action.
- At 320 × 740, settings fields fit horizontally and the full form remains scrollable. At 768 × 1024, library search filters the complete library and exposes Import and default-run status cards. Desktop baseline is approximately 1205 × 884.

Saved screenshots in the task evidence folder include `mobile-v160-results.png` and the production workbench image. JavaScript error logs were checked during rename testing and were empty. Asset revisions were advanced during testing to avoid cached earlier scripts; release URLs use 20261020-8.

Production acceptance confirmed the invalid-DT message is shown without a fabricated step count, while Cancel preserves the applied model settings. Real MCP page acceptance reached revision 4 with an analytically expected final Balance of 110 and the Analytics view visibly selected. `mcp-v160-page.png` captures this synthetic local test; its temporary session was then revoked and its secret handoff file removed.

## Limits

These checks exercise responsive layout and actual pointer/keyboard workflows in one browser engine. They do not establish physical touch-device behavior, operating-system accessibility behavior, Safari or Firefox compatibility. Dense graphs necessarily shrink when fitted on a phone; zoom, full accessible names and property selection remain the detailed-reading paths. No claim is made that all remaining corpus definitions are scientifically trustworthy.
