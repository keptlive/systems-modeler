# Native bounded MDL import

`app/core/mdl_parser.py` implements an independent scalar Vensim MDL reader in Python. It neither executes nor depends on Simlin. The [pinned Simlin MDL architecture](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/mdl/mod.rs) informed the separation of parsing, conversion and explicit loss reporting. Upstream parser code was not copied.

`parse_mdl(text)` returns:

- `model`: an ordinary scalar model dictionary for existing validation and simulation.
- `diagnostics`: warnings about applied defaults, topology representation, units range metadata, display omissions and solver assumptions.
- `original_source`: the exact supplied text, including documentation and sketch.
- `source_format`: `vensim_mdl`.

On failure, `MDLImportError(ValueError)` exposes `original_source` and `diagnostics`, with severity, code, message and optional record number. An unsupported equation never returns an apparently usable partial model. Consumers must retain the original source and display warnings; scalar JSON export cannot reproduce the original MDL document.

## Supported subset

The quote-aware record scanner handles pipe-delimited records, tilde equation/unit/documentation fields, nested brace comments, a UTF-8 header, equation line continuations and .Control-style group banners. It recognizes the sketch marker only at a physical line start. The entire sketch/trailing metadata remains in original_source; editor geometry is not imported and a warning identifies that omission.

Names may contain spaces; references are matched case-insensitively with spaces/underscores following the existing engine's alias rules. Ambiguous names fail. Quoted names are recognized; names containing structural characters outside this supported scalar subset fail. References are converted into quoted scalar parser identifiers. No eval, exec or arbitrary function invocation occurs.

Each `INTEG(derivative, initial)` declaration becomes a stock plus one signed net inflow whose equation is the exact translated derivative. Numeric initial conditions remain numeric; expression initializers retain their translated equations. This preserves the differential equation while explicitly reporting that material-flow topology was not inferred. Negative derivatives remain signed inflows; this representation does not establish inter-stock conservation or reconstruct pipes.

Other assignments become auxiliaries, even if a name suggests a flow. Arithmetic, exponentiation, comparisons, boolean operators, IF THEN ELSE, basic trigonometric functions, EXP, LN, SQRT, ABS, MIN, MAX and STEP are supported. Vensim TIME maps to engine TIME, TIME STEP maps to DT; INITIAL TIME and FINAL TIME references become imported numeric controls. Unknown functions or references fail. Pulse, delay and smoothing functions are deliberately rejected because their source semantics have not been established by this reader.

Entire-equation `WITH LOOKUP(input, ([(xmin,ymin)-(xmax,ymax)],(x1,y1),...))` and the same syntax without the plot-range header are supported. Coordinates must be finite numeric literals, strictly increasing in x, with 2–1000 points. Tables use continuous, endpoint-clamped interpolation. Plot-range metadata remains in source and generates a warning. Standalone lookup declarations, extrapolation modifiers and nested inline lookups are unsupported.

INITIAL TIME, FINAL TIME and TIME STEP accept finite numeric literals. SAVEPER must equal TIME STEP, either numerically or by that exact symbolic reference. Missing controls apply explicitly reported defaults of 0, 100 and 0.25. Conflicting time-unit labels fail; alias conversion between time units is not attempted. Imported execution starts with Euler, and a warning states that trailing Vensim solver metadata was not applied. The user can select another supported solver after import.

## Explicit exclusions and bounds

Arrays, dimension declarations, macros, external data, nonstandard assignment operators, empty equations, arbitrary unknown functions, unsupported lookup forms, output resampling and nested INTEG fail with retained source. Documentation, group presentation and sketch metadata remain only in original_source. Units strings are retained; their optional range annotations are reported and removed from executable unit strings.

Input is limited to two million UTF-8 bytes, 500 records, 100,000 characters per expression, and a conservative 250 source-equation limit to leave room for generated stock net flows under the current 500-element engine bound. Existing scalar validation and simulation work budgets still apply.

## Verification and attribution

The tests contain a small equation/unit/control excerpt of [SDXorg Teacup](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/test/test-models/samples/teacup/teacup.mdl), attributed to James Houghton (2015), distributed under the MIT license already retained in `tests/fixtures/sdxorg/LICENSE`. Documentation and drawing records are omitted from that test excerpt; model equations, initial conditions and simulation controls are preserved. Complete output is checked independently against the analytic exponential-cooling solution with RK4. Original fixtures also exercise expression initializers, aliases, record/comment parsing, conditional expressions, interpolation/clamping and explicit rejection/bounds cases.

