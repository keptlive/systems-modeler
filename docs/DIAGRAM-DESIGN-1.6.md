# Diagram design 1.6 — technical drafting surface

## Brief and baseline

Audience: people building, inspecting and revising stock-and-flow systems. Primary diagram task: recognize state versus transfer versus dependency, read the actual element names, select/edit/connect elements and keep the whole model in view. Thesis: a precise technical drawing with semantic shapes, restrained surfaces and readable labels, rather than a field of brightly filled icons.

Read the design-direction brief, art-direction and critique guidance. Baseline inspected: live v1.5 desktop 1205×884 screenshot `live-v150-workbench.png`, retained with private QA artifacts. The Anderson-May example's solid orange circles truncated almost every multiword auxiliary to eight characters; flow labels were also clipped, white outlines competed with text, dependency arrows ended beneath node centers, and rendering logged every refresh. The existing navy identity, blue rectangular stocks, lavender valves and amber auxiliary vocabulary remain the foundation.

Preserved paths: mouse and touch selection/drag; manual stock/flow/variable placement; dependency creation; connector selection/deletion; property editing; keyboard activation; zoom/pan/reset/fit; imported/saved element IDs, coordinates, equations, flow links, source content and time settings. No autolayout or model mutation occurs in rendering. Shell, toolbar, sidebars and browser verification are owned by the coordinating reviewer.

## Authored visual grammar

- Stocks: modest 112×64 dark-blue cards, a fine blue accent rule and STOCK eyebrow. Multiline names replace twelve-character truncation. The shape remains the system-dynamics state primitive.
- Variables: 110×42 subtle amber-outlined capsules, with an amber hollow-circle symbol and readable two/three-line names. The muted body supports dense existing 50-unit vertical spacing. Every Anderson-May auxiliary name fits without ellipsis. Exceptional long labels use bounded wrapping plus a native full-name title, rather than expanding geometry across neighboring nodes.
- Flows: compact horizontal lavender bowtie valves, central spindle and separate wrapped label plates. Transparent 44×44 valve targets and the label plate participate in selection and dragging. Solid directional material lines are visually distinct from fine dashed dependency curves.
- Dependencies: rounded-body endpoint clipping and smaller arrowheads keep the direction outside the node silhouette. Wide transparent hit paths support selection without visually thickening the drawing. Self/coincident dependency links receive finite cubic loops instead of division-by-zero geometry. Material arrows with no visible gap between overlapping primitives are omitted instead of being drawn backwards; links remain in the model and inspector.
- State: subtle fill/stroke changes on hover; clear semantic selection and keyboard focus. Native group titles retain complete names and units. Keyboard Enter/Space uses the same selection/connect handler, and focus is restored to the corresponding element after a render.

Tokens: stock body #1b324b / stroke #648caf; variable body #252c36 / stroke #937954 / text #e9d7b9; flow #bea8eb; dependency #7d94af at 65% opacity. System sans 11.5px stock names, 10.5px flow/variable names, 8px eyebrow; no new asset/font dependency. One/two-pixel non-scaling strokes preserve technical clarity through zoom. Reduced-motion users receive static state changes.

## Geometry and interaction evidence

Node bounds, touch hit zones, endpoint intersections and fit bounds share the new dimensions. Fit includes wrapped flow captions and dependency control points, with reserved title and bottom-control space. Positions are never rewritten to accommodate typography. Material-flow orientation still comes exclusively from the existing source/target stock fields. No source/sink cloud was inferred from an unresolved stock reference.

`node scripts/check_diagram_v16.cjs` passes independent geometry assertions: stock and capsule clipping, rounded-body finite endpoints, self/coincident dependencies, overlapping material arrows, flow-caption hit zones, complete Anderson auxiliary wrapping, fit containment and unchanged model positions. `node scripts/check_frontend.cjs` confirms all frontend scripts parse. These checks do not substitute for rendered interaction testing.

Actual final desktop/narrow-view screenshots, mouse/touch/connect/edit and keyboard findings are pending the coordinating reviewer's browser session. This subagent's browser runtime has no available surfaces. Physical mobile devices, Safari/Firefox and screen-reader operation remain untested unless separately recorded. No commit or deployment performed by this reviewer.
