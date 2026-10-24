# Workspace refinement — October 20, 2026

Audience: people exploring a stock-and-flow model and agents handing a model to a person for inspection. Primary task: inspect inputs, edit a diagram, run with explicit settings, and compare the visible result. Preserve every editor, AI, chart, import/export, library, saved-model and mobile path recorded in OPERATIONS.md.

Design thesis: a compact modeling workbench with the diagram as the working surface, inputs close to the run action, and readable results that remain in view.

Retain the dark navy palette and stock/flow/variable color vocabulary, D3 diagrams and the existing three-panel desktop/mobile-panel structure. Use one restrained header, consistent controls, visible focus states and text-backed statuses. Keep decorative effects quiet. No new framework, font dependency or stock imagery.

Observed baseline: the header consumes two rows; desktop diagram nodes are clipped after import; chart margins reserve most narrow charts for an internal legend; mobile controls shrink below useful touch sizes and some purchase-independent import/export buttons disappear; a fixed cross-site footer covers workspace space; Steps input has no handler; browser zoom is disabled in the viewport; repeated CSS overrides disagree. Model/source details and loading errors are hard to inspect.

Refinement priorities: fit-to-model and explicit zoom controls; responsive chart dimensions; consistent header and readable controls; recoverable loading errors; complete mobile import/export paths; keyboard selection and focus; accessible modal/report behavior; safe rendering of user names/equations; input checking and truthful default-run statuses.

Verification matrix: wide desktop, laptop, tablet, narrow phone and landscape; keyboard/focus and browser zoom/reduced motion; library→details→import→input check→edit→simulate→analytics→save/reload→export/import. Test empty/loading/failure and long-content states. Browser/device coverage must name the actual engine and viewport; responsive emulation is not evidence of physical iOS/Android/Safari testing.

Tokens: 14–16px body, 12–13px metadata, 16px numeric/form input on narrow screens; 4/8/12/16/24px rhythm; minimum 44px coarse-pointer controls; slate surfaces, pale foreground, blue action/focus, amber review and red errors. Reduced motion removes nonessential animation. Focus ring remains visible against all surfaces.
