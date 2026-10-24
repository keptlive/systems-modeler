# Minimal preset discoverability using the existing product

Research only, October24,2026. No runtime or active model was changed. The final proposal description now includes these instructions, subject to exact-hash rereview.

## Verified existing paths

- Inspect already renders report.inputs.description as plain text in Source & run settings (static/js/validation.js). Its Equations & initial values rows include an existing button for each variable/stock; selecting r closes Inspect and selects the current editor element. Users can edit its existing Equation field and run normally. This is not a new toolbar or preset widget.
- The library search already checks both model name and description (static/js/library.js). Including former model titles/IDs and their r presets in the canonical description helps old-name searches find the retained model. It does not make old deep links redirect.
- The existing chart Save Run and Compare controls retain trajectory copies in Charts.previousRuns and overlay saved runs. Desktop and mobile controls already exist. Saved entries have generated labels/timestamps/results, not a frozen model/parameter provenance record; do not describe them as persistent named scenario definitions or a scientifically attributed comparison.
- The existing compare_scenarios MCP tool accepts up to10named parameter overrides on a deep-copied saved model, so the three exact invocation presets in SCENARIOS.json need no engine/API/schema addition. It returns summaries, not full trajectory overlays. This proposal's test invokes the actual tool and traps saves.
- There is no currently verified browser preset menu or automatic Model.scenarios field. Do not promise one or add ignored metadata to fake discoverability.

## Smallest useful adoption change

Use visible canonical description content, so all three cases are discoverable through existing library search and Inspect, then use existing edit/run/comparison actions. PRESET-DESCRIPTION.txt supplies concise proposed wording:

1. State the three defaults explicitly: r3.7,3.8,3.9; Population0.1;0..100generations; Euler and dt=discrete_period=1.
2. Tell users exactly how to change r through Inspect and the existing Equation field. State that this intentionally changes the current draft and never saves automatically.
3. Tell users to run/save each case in stated order, then use existing Compare. Generated Run1/Run2/Run3 labels map to that chosen order; keep exports or notes for parameter provenance.
4. Include both former titles/IDs plus parameter mapping, so name/description search can discover the consolidation. Old-ID deep links still require a separately reviewed retirement note/redirect policy.
5. Point agents to the literal existing compare_scenarios payload. Only link a public help/preset URL after it has actually been published and verified.

This is a model-description/documentation change, not an interface redesign. No new button, toolbar, automatic parameter application, custom scenario storage or analysis workflow is required. The proposed canonical description now includes the explicit instructions and former-ID migration notes. Its revised metadata-only hash must be independently approved before adoption. No public help URL is promised.

## Evidence and boundaries

Six consolidation tests establish full default trajectory/legacy-view parity and actual MCP scenario-tool operation. Browser edit/run/comparison instructions above are established source paths, not a new end-to-end browser receipt. Before adoption, root should exercise all three presets through the existing editor/Inspect and Save Run/Compare, confirm period guard/error paths and verify the canonical description is visible in the public library and Inspect. Export's actual browser refusal/preserved-controls check is separately root-attributed in docs/XMILE-EXPORT-ERRORS-REVIEW.md.

This research recommends two retirements because the cases are parameter variants of one mechanism. It does not use a count target to justify removal. No active adoption is performed.
