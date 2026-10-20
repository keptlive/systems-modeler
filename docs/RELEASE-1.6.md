# Stock & Flow 1.6 — diagram studio and source-backed lookups

The diagram and workbench have a coherent drafting style: readable stock cards, wrapped variable names, lavender flow valves, clipped material pipes and finer dependency curves. Selection and keyboard focus remain visible. Geometry, hit zones and fit bounds are tested together; opening a model does not rearrange its positions or alter its equations.

Header, toolbar, chat, properties, results, library, settings and mobile sheets share consistent surfaces and controls. An assistant-panel toggle frees diagram space without changing its default visibility. Final values remain available in a disclosure. Phone results show the chart before series controls, with readable unselected series and accessible fullscreen/close controls. Validation notices are dismissible and preserve keyboard focus. Invalid time settings no longer display a step estimate calculated from silently substituted defaults.

An ordinary element rename previously left its old name in dependent equations. Renames now commit as one validated transaction, preserve IDs, rewrite supported scalar references and exact name-based endpoints, and reject ambiguous or unsupported cases without partial changes. Blank/nonfinite initial-value drafts preserve the last valid input and restore it on commit on both desktop and mobile. Existing initial-equation and units fields remain available.

## Source fidelity and numerical evidence

Three failed LOOKUP definitions are restored against pinned native sources: Hares and Lynxes, Capability Trap, and Rookies and Experts. Six original graphical functions retain their published knots and endpoint-holding semantics. Twelve scoped tests compare the complete 25 × 14 native Stella CSV, independent full-grid source recurrences, and table knots/midpoints/exterior behavior. IDs, layout, original scalar parameters and initial values remain unchanged; five former zero-valued table placeholders become evaluated curve outputs. See `LOOKUP-SOURCE-REVIEW-1.6.md` and its hash-bound receipt.

The full 1,078-model public audit now completes **944 defaults and reports 134 failures**, a gain of three with no new failures. A separate instrumented full-corpus run reproduces those totals and records actual function invocation. All 25 function names present in the corpus now occur in completing examples, including LOOKUP; 19 of the 44 advertised names still require synthetic regression coverage because they do not occur in the parsed corpus. The 218 advanced-function tests from 1.5 continue to pass. Invocation or a finite result alone does not validate equations, units, calibration or scientific use.

The complete Python regression run passes **595 tests and 18 preservation subtests**, with three strict expected failures documenting unresolved XMILE identifier compatibility and one existing Pydantic settings warning. Eight Node suites cover parsing, result state, navigation/modal boundaries, series controls, diagram geometry, property transactions, fullscreen state and notifications. Real local MCP HTTP/SSE/stdio clients pass with all 17 tools. The existing 17 independent mathematical reference checks also pass in the fresh capability audit.

`ENGINE-INPUT-FINDINGS-1.6.md` explains duplicate identifiers, disconnected initial-condition inputs, reporting-domain errors and dialect limitations without inventing equations or silently replacing failures. No core numerical engine source changed in this release. The native hares model's general nonnegative constraints remain unsupported; its default matches the source, but arbitrary scenarios need review. Capability Trap retains its original author's formulation warning.

Responsive browser checks cover desktop, tablet and narrow phone layouts. Physical devices, Safari and Firefox remain unverified; this is not an all-platform certification. Existing AI, analytics, import/export, saved models and agent workflows remain present.

## Production acceptance

Activated October 20, 2026. All 13 runtime files match the reviewed release. The three model replacements passed exact old/new-hash fences; every other byte across 1,092 model/database files was preserved. The additional 13 production-only definitions retain 11 completed runs and two failures, giving **955 completed / 136 failed** across the live library.

The staged release passes 465 tests with three documented expected failures using the existing production dependencies. Live HTTPS HTTP/SSE MCP checks pass with all 17 tools. An actual local MCP-to-browser acceptance run edits a flow, computes the independently expected final balance of 110, switches to analytics and receives browser acknowledgement at revision 4, preserving source/units without AI-provider calls or saved-library writes. The public review tree independently passes 595 tests and 18 subtests, and reruns the full instrumented corpus plus 17 reference checks against its own evidence hashes.
