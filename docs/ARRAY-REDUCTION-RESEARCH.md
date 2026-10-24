# Typed structured array reductions: research contract

The frozen experiment described below now has a locally implemented adapter in
`app/core/array_reductions.py` and `structured.py`. Its bounded scope, test
evidence and independent review gate are recorded in
`ARRAY-REDUCTION-ADAPTER.md`. This does not imply deployment or publication.

The frozen offline experiment, identified by hashes in the adapter document, supports a useful
narrow extension to native structured lowering: MEAN, MIN and MAX over one
declared array reference alongside SUM. It does not modify the current compiler,
add an editor feature, or establish XMILE array interoperability. No performance
comparison was made and no speed claim is warranted.

## Proposed source and overload contract

Reference shape and declared selectors determine a reduction, not a function
name regex or the number of resolved cells. Example: for `P[Region,Age]`,
`MEAN(P[North,Age])` selects all ages in North, in declared Age member order.
`MEAN(P)` selects every declared axis. A dimension selector reduces its entire
axis even inside an array equation whose current cell binds that dimension,
matching existing SUM semantics. A singleton axis is still an array axis.

SUM and MEAN accept exactly one declared reference in this experiment. SUM of a
scalar or literal cell remains identity; MEAN of one selected scalar is also
identity. Unary MIN/MAX reduce only when at least one axis is selected as a
dimension. Literal-cell/scalar unary calls remain unchanged for scalar
validation, including their existing errors. No scalar MEAN argument-list
extension is proposed. Arithmetic array operands require an auxiliary first.

All other MIN/MAX calls remain scalar source. This is necessary to preserve
`MAX(P[Region],0)` inside an array-cell equation: the current compiler binds
Region to that cell, so the call already works as scalar clipping. It must not
suddenly mean the maximum over the entire array. Outside a compatible context,
the existing compiler still diagnoses its unbound dimension. This experiment
does not support XMILE's two-argument mixed array/scalar overload. A scalar
outer call such as `MAX(0,MEAN(P[Region]))` can contain an independently typed
reduction. Returning unchanged text never certifies scalar syntax or validity.

Literal slices, wildcards, ranges, transposes, dimension mappings, array-valued
ports, container reductions, and composite/nested array reductions are outside
the contract. SUM/MEAN unsupported operands fail explicitly. Unrecognized
MIN/MAX scalar forms continue to the existing structured/scalar validators.
There is no arbitrary Python execution, expression evaluation, dynamic import
from authored model text or generated executable code.

## Source, modules and numerical order

The pass retains the exact original equation and reduction source spans.
Double-quoted identifiers are lexical atoms; function-like text inside them is
never executable syntax. Whole-reference quoting, for example
`MEAN("P[North,Age]")`, is an additive candidate spelling. Quoted references
cannot contain comment/code fragments. Module-local scope is explicit with no
implicit parent capture. Ports represent prevalidated explicit scalar targets,
never arrays; selecting an axis through a port fails. Dotted module outputs
must come from the existing module validator rather than inference from their
spelling. Existing flow endpoints, source IDs, original project JSON, dimension
order and source maps must survive an eventual compiler adapter unchanged.

Scalar names are quoted in lowered output. Enumeration follows declared axis
order, with the rightmost axis changing fastest; members are never sorted.
SUM uses the same left-associated scalar addition order as the current compiler,
without a leading zero or reassociation. MEAN divides that ordered sum by the
selected cell count. This deliberately preserves current intermediate overflow
errors rather than substituting a numerically different stabilized mean.
MIN/MAX use existing scalar finite-real rules, visit each selected reference
once, and preserve first-occurrence ties, including signed zero. Singleton
MIN/MAX lowers to the selected reference, avoiding Python's unary iterable form.
No empty-axis identity, zero-filled bad index, NaN filtering or invented unit
conversion is introduced. Dimensions must be nonempty; all four operations
retain the selected element units, subject to independent metadata checking.

## Bounds and remaining integration work

The prototype scans iteratively with at most 64 delimiter/comment levels and
100,000 source/output characters per expression. A caller-owned shared Budget
starts at two million work units across an expanded model, charging source,
reference parsing, expansion metadata/text and overlap checking. Fixture Scope
validation limits 32 axes, 4,096 local expanded cells and eight prefix levels.
This helper does not enforce aggregate cells/instances across multiple scopes;
the current model compiler's 4,096 total cells, 128 instances, module depth,
identifier metadata and engine execution limits remain mandatory. A compiler
adapter must share a budget across every override and expanded cell; allocating
a fresh budget per expression would break the proposed resource contract.

An eventual implementation should expose the existing validated scope resolver
to typed nodes, not copy this offline Scope into production. Replace the current
SUM-only regex pass with a bounded typed pass. Keep ordinary identifier rewriting,
stock initializers, override selection, scalar error paths and source retention.
Do not loosen scalar parser expression-length limits or simulation work limits
to accommodate expanded text. No HTTP/compiler integration or lossless
round-trip coverage exists in this research package.

Adoption requires independent review, then separate authorized implementation
with existing structured/module/alias/quoted-name regressions, initialization,
lazy branches, stochastic/stateful restrictions and all solvers. Include original
JSON edit/save/reload/compile/run plus API/MCP tests and explicit XMILE loss
reporting; unsupported array interchange must remain visible. Never replace the
editable source document with the flattened execution artifact. A future units
adapter should check reductions on original typed references rather than guess
units from flattened text.

## Primary references and executed evidence

The optional array extension in
[OASIS XMILE 1.0 section 3.7.1](https://docs.oasis-open.org/xmile/xmile/v1.0/os/xmile-v1.0-os.html)
defines ordered dimensions and broader reduction/container semantics than this
experiment. Our named-dimension reduction selectors preserve native SUM rules;
they are not a translation of every XMILE subscript rule.

[Simlin's pinned builtin signatures](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/builtins.rs)
separate argument kinds, result shape and unary reduction overloads. Its
[array tests](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/array_tests.rs)
exercise slices, expressions and nested operations beyond our proposal.
Source inspection inspired the typed boundary; no implementation was reused.
Simlin's Apache-2.0 notice does not establish rights in every bundled fixture.
OASIS specification rights are separate. This package contains original code
and an original authored XMILE fixture, rather than copied upstream samples.

The executed installed pysimlin 0.8.5 wheel is pinned by native-library SHA-256
in `array-reduction-simlin-reference.json`. It is not claimed to match the inspected source
revision. Its complete 33-sample output for all four reductions agrees exactly
with the prototype and independent formulas for values `2+t` and `8-2*t`,
including the crossing at t=2. Separately, 68 regression tests compare
hand-expanded full stock trajectories, 400 random-state arithmetic answers,
ordered multidimensional selections, budgets and errors. This is narrow
numerical evidence, not full Simlin parity, complete parser security review or
scientific model validation. No production engine or active model changed.
