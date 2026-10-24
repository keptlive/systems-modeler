# Typed native array reduction adapter

Local implementation, independently reviewed; pending separate publication.
No API, editor, model definitions, deployment or interchange format changed.
The static validation receipt is refreshed to bind the reviewed engine bytes. Existing source documents remain the editable source; lowering
only returns an execution artifact and leaves the input and source map intact.

The adapter adds MEAN and unary array MIN/MAX beside existing SUM, using the
existing structured compiler's validated dimensions, symbol tables, explicit
scalar ports and module-output resolver. It introduces no second module compiler.
The typed expression scanner comes from the original frozen research pass,
without its fixture Scope. Ordinary scalar source is rewritten in segments
between exact reduction spans; generated references never pass through source
identifier rewriting. There are no synthetic placeholder identifiers.

The research contract remains deliberately narrow: one declared reference for
SUM/MEAN, unary dimension-selected references for array MIN/MAX. Literal-cell
and scalar unary MIN/MAX are unchanged scalar source, including TIME, so their
existing scalar validation still applies. Multiargument MIN/MAX keep current-cell
binding and scalar clipping. Bare arrays reduce their declared axes. Quoted whole
references are supported. Arithmetic operands require an auxiliary. Module ports
remain explicitly bound scalar cells; no parent capture, arrays through ports,
mappings, wildcards, slices or container semantics are added.

One caller-owned Budget covers scanning, reference selection, lowered text and
final scalar rewriting across every expanded cell and selected equation override.
The 100,000-character equation cap, two-million aggregate work cap, bounded
64-level lexical delimiter/comment handling, 4,096 aggregate cells, 128 instances
and module depth/identifier budgets apply. Existing scalar expression-size and
execution limits still apply independently. No parser or simulation limits were
increased. SUM ordering remains left-associated and MEAN divides that same sum;
there is no arithmetic reassociation or stabilized-overflow behavior.

## Exact frozen research independently inspected

- prototype.py: `4a719e7c3b1b9c0761b1c3be7db9d011671756cb641d39a0c4e0b9fd97947475`
- test_prototype.py: `c98c43a87230c4c4dd411572dc4e6472cd79d10dd5522b4b726f3c57d7d1c5a8`
- SIMLIN-REFERENCE.json: `1372e7c9e11317fad3f80b46632923980a3c67f245f6006345e4d9405a09520d`

Review verified overload selection uses axes rather than selected-cell count,
scalar outer calls remain scalar, lexical quotes are atoms, reference selection
preserves declared Cartesian order and first signed-zero ties, resource charges
are shared, and fixture ports are scalar-only. The fixture scope was intentionally
excluded from production; validated production resolution replaces it. Existing
research tests plus new adapter tests exercise errors and independent formulas.

The pinned Simlin source inspection revision is
`3f87e9024a580b86b65e3d0c5c3353660fc5426e`; the separately executed pysimlin
0.8.5 wheel is identified by native-library hash in the copied receipt
`array-reduction-simlin-reference.json`. Wheel/source equivalence is not asserted.
All 33 reference samples for all four operations are checked by production
adapter tests. This is narrow numerical comparison, not general XMILE parity,
a performance claim or scientific validation of arbitrary models.

## Frozen implementation submitted for independent review

- structured.py: `44e119463fc6470e867fcfd519099f0ebb2a527a547c88d623ae2b1f7591a5ee`
- array_reductions.py: `9881875542167f033142376167e3e13487000aaed84029d157a09e200f2c275b`
- test_array_reductions.py: `0bb1d51f6ba256bcf828e4e383bc15c9229fa58ef1a8c9b99c9b4bc8503f61f2`

Focused validation: 143 passed (adapter, existing structured model/integration,
and frozen research suites), including hand-expanded stock trajectories under
Euler, RK4 and Radau, scalar overloads, quoted references, module-local arrays,
scalar ports, source retention, crafted placeholder-like source identifiers,
aggregate budgets and generated equation caps. Independent exact-byte approval and 18 additional scratch checks are recorded
in `ARRAY-REDUCTION-ADAPTER-REVIEW.md`. The full-suite and audit results are recorded below. API/MCP exposure uses
the existing structured compilation route; release transport regression checks
remain required. Unsupported array interchange remains an explicit limitation.


## Full catalog numerical evidence for the next release

The initial complete suite finished with 3,084 passing tests, 18 passing subtests,
one skipped test and three expected failures; its sole failing test detected the
old public validation receipt's stale engine hashes. The engine was frozen and
all 993 Git-tracked public definitions then completed full default simulations,
using `scripts/audit_library.py --full --tracked-only` and fallback random seed
42: 993 passed, zero
failed, 90.73 seconds. This is numerical execution evidence, not scientific
validation. Input diagnostics remain in the full audit rather than being hidden.

The audit script has SHA-256
`59f1a03f3a1165ce5f1d9d39746fce745e38b7fb49c970da4aab5325bcacfacb`.
The full audit has SHA-256
`204e0b30913ea1c881545a7539c84e5258d909f2c9e1af226ed2e194e473153e`.
The regenerated minimal public receipt has SHA-256
`338942c218df43b74f47d8a3b90c14cfef2b07d77d4171c39f0106bce881028a`.
Generation verified every audit model file hash against the current tracked
catalog and every engine hash against current source. All ordered public model rows are
identical to the previous receipt; the only engine
changes are the structured compiler hash and new typed reduction module key.
The public-receipt, adapter and structured suites then passed all 77 tests,
including the previously failing engine-binding check. No full-suite all-green
rerun is claimed from this targeted recheck.

This receipt belongs to the next typed-adapter release. It must accompany the
reviewed engine bytes; it is not a receipt for an earlier release without the
adapter. No publication or deployment was performed during this audit.

## Sanitized public review validation

The complete sanitized public suite passed: 3,086 tests, 18 subtests and three
expected failures in 357.09 seconds. Actual local HTTP, legacy SSE and stdio MCP
SDK checks passed the existing 993-model inventory, analytical simulation,
error/resource/prompt behavior. Additional SDK calls on each transport compiled
and simulated SUM/MEAN/MIN/MAX over all 33 samples, matched independent formulas,
and returned a tool error for unsupported arithmetic array operands. No models
were saved. This supersedes the earlier local targeted-only rerun limitation for
this public package; production staging and exact-head CI remain separate gates.
