# Expression compatibility and exact scalar simulation round trips

The scalar importer/exporter supports exact round trips of complete simulated
trajectories, report outputs, solver settings, and variable roles. Focused tests
also cover supported equations, graphical functions, literal names, and seeded
random stream identities. This is not a claim of complete structural equality
for all source metadata, diagrams, or unused definitions. Tests cover
MDL import followed by XMILE export/reimport as well as native scalar models.
This does not claim that every other modeling tool implements every extension.

## Correctness fixes

- Quoted MDL identifiers containing arithmetic punctuation cannot capture an
  unquoted arithmetic expression. For example, declaring `"A-B"` does not change
  the meaning of unquoted `A-B`.
- STEP snaps only local floating-point grid roundoff, bounded by the timestep;
  RK4 retains the accepted-interval input snapshot.
- A two-argument RAMP with a negative start has no implicit stop at zero.
  Existing explicit three-argument native RAMP behavior is preserved.
- MDL RAMP uses a distinct three-argument `RAMP_VENSIM` operation, including
  variable endpoints and the documented end-before-start behavior. Its arguments
  are evaluated once and its value is held across RK stages.
- Stateful initialization respects lookup-table ownership, including inactive
  branches. A table named SMOOTH is not a smoothing state.
- Radau's continuity certificate requires complete switching surfaces. Arithmetic
  wrappers around comparisons cannot bypass the discontinuity check.

## Import and export

Nested LOOKUP calls and case/spacing aliases retain their referenced table.
Quoted builtin-named tables retain their runtime ownership. Empty graphical
functions and embedded flow graphs without an input expression produce specific
validation errors instead of silently supplying data.

POW with two arguments exports as exponentiation without duplicating arguments.
Native truncating MODULO exports as REM, separate from the floored MOD operator.
Safe-division functions preserve exact-zero versus near-zero rules and eager
argument evaluation. Scalar extension calls preserve existing function semantics
rather than expanding them into formulas that could duplicate stateful or random
arguments.

REM, TRUNC, QUANTUM, SAFEDIV, XIDZ and RAMP_VENSIM, and nonstandard scalar math
spellings are compatibility extensions; support in a different XMILE reader must
be checked. In particular, the pinned Simlin source and the older published
Python wheel implement different function sets and some different semantics.
No normative XMILE MODULO function alias is assumed.

For seeded graphical-function inputs, export retains the expression shape when
rewriting it would change implicit stream identity. The random-identity guard
remains enforced. This is reproducibility of our imported model, not a promise
that different engines share a random-number algorithm.

Our exports declare the `native-scalar-v1` compatibility profile in the
`https://stockandflow.live/ns/model` namespace. Explicit extension attributes
preserve Radau selection, relative/absolute tolerances, discrete periods and
report roles; report expressions and declared scalar names retain their identity.
Variadic MIN/MAX, floored MOD and RANDOM_BINOMIAL also round-trip without changing
argument evaluation or seeded stream positions. These extensions require a reader
that understands this profile; they are not a claim of universal XMILE portability.
Unknown or misplaced native attributes, duplicate simulation settings and invalid
values are rejected rather than silently discarded.

Structured array/module export remains outside this scalar change. Invalid
signatures and malformed input still receive errors; they are not silently
coerced into a different model.

## Validation

`scripts/audit_xmile_roundtrips.py --output /tmp/xmile-roundtrips.json` checks every
Git-tracked public model. The existing pytest CI entry point runs this audit
through `test_full_tracked_library_xmile_roundtrip_audit`. It simulates before export and after
reimport, comparing every time sample, numeric series, report output, solver
setting and variable role exactly. It also checks in-memory source-model
immutability, captures the initial tracked-model inventory and byte hashes,
and requires that same inventory and bytes at completion. The receipt binds
those model hashes and engine hashes. A seed of 42 is applied consistently when a
model has no explicit seed. This is a numerical preservation check, not independent
scientific validation of every model's assumptions.

`tests/test_followup_*.py` checks full-series round trips, independent numeric
expectations, lazy branches, eager function arguments, table ownership, random
identity, solver admission and dimensional/dependency analysis.

Run `scripts/expression_roundtrip_reference.py` with an explicitly selected
pysimlin Python executable and source checkout to generate an engine-hash-bound
comparison. It records the source commit, native binary hashes, exact local
round-trip equality, and reference agreements, differences or rejections. A
reference disagreement is investigated rather than used to redefine semantics.

Primary contracts: [XMILE 1.0](https://docs.oasis-open.org/xmile/xmile/v1.0/os/xmile-v1.0-os.html),
[Vensim RAMP](https://www.vensim.com/documentation/fn_ramp.html), and
[Vensim Runge-Kutta input policy](https://www.vensim.com/documentation/rungekutta.html).

When a validated rewrite would move an implicit seeded random call, the exporter
retains the original native expression and verifies its call positions again.
Such expressions are compatibility extensions, not promises of execution in
every XMILE reader.

The recorded [Simlin comparison](expression-simlin-reference.json) uses source
commit d418b98d72019eb0509feb2e93a18e6a9674fbc7, including our proposed
upstream safe-division fix, not the older published wheel or unmodified main.
All ten cases round-trip exactly locally. Eight agree with that reference;
negative-divisor REM differs, and its reader rejects our standalone-table
nested lookup fixture. Those limitations are retained in the receipt.
