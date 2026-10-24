# UI direction 1.5 — precision workbench

## Brief and preservation baseline

Audience: people building and inspecting stock-and-flow systems, including people reviewing models supplied by an agent. Primary journey: choose/build a model → inspect inputs and source limits → set a solver/horizon → run → examine results → revise/save/export. Design thesis: a compact scientific workbench in which the diagram is the primary working surface, current computational context is always legible, and navigation never competes with the model.

Read the repository preservation baseline, UI-DIRECTION.md and UI-QA.md before changing the interface. Preserve the navy identity and stock/flow/variable semantic colors. Existing paths retained: new/save/saved models; library search/categories/details/import; XML/XMILE/JSON import and export; manual stock/flow/variable/link/delete tools; canvas pan/zoom/fit; title and property editing; time settings, steps and random seed; inspection and numerical investigation/report download; AI generation/modification; agent connection/session controls; chart, analytics and AI insights; all chart types, logarithmic/normalized scales, animation, scenarios, saved runs and export; mobile add tools, AI/Edit/Results panels, settings, import/export; help and cross-site navigation. No original action or model data removed. Parent owns additional series-selection behavior in charts.js.

## Evidence and decisions

Baseline: live v1.4, 2026-10-20, desktop 1205×884, parent-captured screenshot `live-v140-design-baseline.png` (private QA artifact), visually inspected by this reviewer. Observed: large assistant column with repeated introduction; uneven action hierarchy; long model name truncated; run/steps separate from editing controls on a wrapped row; chart and variable controls visually crowded. Existing dark three-panel workbench is a suitable foundation. No alternate branding, layout replacement, framework or asset dependency is introduced.

Retained: panel composition, native controls/dialogs, diagram and all existing semantic colors. Adapted: dot-grid canvas, longer title area, compact type roles, coherent borders/surfaces, stronger run action, grouped steps/run, tighter readable properties/results/inspection. Added: command and element finder plus persistent model/solver/run context. The finder searches commands, element names and equations; all commands invoke existing controls/functions. No new destructive operation is added. Arrow keys navigate results, Enter chooses, Escape closes, and Ctrl/Command K opens it. Native dialog preserves modal keyboard boundaries. On narrow screens the same finder is available in the horizontally scrollable action row, and command targets retain the existing mobile routes.

Truthful feedback: the context strip reads actual model counts, actual solver/horizon and Simulation state, with text as well as color for running, failure and completed sample counts. It never marks an unrun model verified. Pending inspection changes its button label and aria-busy; the element search reports matching/total counts, including empty matches. These additions do not alter simulation equations, settings or results.

## Reusable system

Primitive colors: canvas #111c2e, low surface #142034, panel #172236, raised #1d2c42, border #3b4c65, foreground #edf3fc, metadata #b7c7dc, action #8bc1fc, focus #c1e1ff. Semantic roles retain stock blue, flow purple and variable orange from the established system. Completed status uses muted mint plus text; failures use warm red plus text.

System UI sans; headings 16–24px/1.25, body 13–14px/1.5–1.65, metadata 11–12px, numeric context tabular. Equations/code use existing monospace. Spacing 4/8/12/16/20/24; 5–7px control/card corners and 12px dialog corners. Desktop fields favor compact density; phone editable fields remain 16px and primary touch controls at least 44px. Existing focus ring preserved, command result focus uses an inset high-contrast ring. Motion is unnecessary and reduced-motion rules remain active. Desktop panels retain content; 900px remains the established mobile boundary. At 900–1199px panels narrow slightly to prioritize the canvas.

Implementation is an additive `polish.css` and `workbench-tools.js`, included after existing resources, plus small inspection feedback edits in validation.js. Existing DOM IDs and handlers retained. Parent series toolbar/search/action selectors are styled in the same grammar.

## Verification and pending evidence

Windows Node: `node scripts/check_workbench_v15.cjs` passed 9 focused assertions for tokenized search, no-match handling, empty/ready/complete/error state and running precedence; `node scripts/check_frontend.cjs` confirms all frontend scripts parse and existing numerical frontend checks pass. These are not browser/accessibility certification.

Final browser evidence is recorded in `UI-QA-1.5.md`: Chromium desktop 1205×884 and responsive 390×844, 768×1024 and 320×740 checks covered successful and failed runs, keyboard commands, exact-name selection and property focus, chart-series selection/filtering, small numerical labels, inspection and numerical investigation. Browser findings were repaired and rechecked. The initial absence of a browser in this runtime was resolved through the coordinating reviewer's browser session. Physical iOS/Android, Safari, Firefox, assistive technology, slow/offline networks and high zoom remain unverified. No deployment or commit performed by this reviewer.
