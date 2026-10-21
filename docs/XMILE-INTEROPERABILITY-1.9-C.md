# XMILE function interoperability review C

The exporter previously copied local functions verbatim. Reproduction: a model
with stock initializer `LOG(8,2)` and auxiliaries `LOG(8)`, `SMOOTH(TIME,1)` and
`RAMP(2,1,3)` emitted those exact expressions. They execute locally, but those
names/signatures are not core XMILE 1.0 equivalents.

## Primary-source contract

Sources read 2026-10-20: [OASIS XMILE 1.0, 14 December 2015](https://docs.oasis-open.org/xmile/xmile/v1.0/xmile-v1.0.html),
sections 3.3.3, 3.5 and 3.6; [Vensim LOG reference](https://www.vensim.com/documentation/fn_log.html).
Vensim's two-argument logarithm uses its second argument as the base. XMILE
defines natural `LN` and decimal `LOG10`; its extension discussion gives the
change-of-base ratio. Its conditional core form uses IF/THEN/ELSE. Function
translation now follows these contracts:

| Local form | XMILE form |
| --- | --- |
| `LOG(x)` | `LN(x)` |
| `LOG(x,b)` | `LN(x)/LN(b)` |
| `IF(c,a,b)`, `IF_THEN_ELSE(c,a,b)` | `(IF c THEN a ELSE b)` |
| `SMOOTH`, `SMOOTH3`, `SMOOTH_N` | `SMTH1`, `SMTH3`, `SMTHN` |
| `DELAY_FIXED`, `DELAY_N` | `DELAY`, `DELAYN` |
| `RANDOM_UNIFORM`, `RANDOM_NORMAL` | `RANDOM`, `NORMAL` |

Delay/smooth argument order and optional initial values remain unchanged. Nth
order is the third argument. Random arguments remain bounds or mean/deviation,
with an optional third seed. `PULSE` already matches magnitude divided by DT,
with a start and optional interval. Core `RAMP` has two arguments; the local
third end-time argument is explicitly unsupported.

## Implementation boundaries

Stock initializers, flows and auxiliaries use the same function checks. The
renderer transforms AST call spans, retains each argument once, and preserves
lazy conditional branches. Operator conversion works on tokens, so `**` inside a
quoted identifier stays intact. Ordinary equations retain their original spacing.

Graphical functions retain runtime precedence: tables named `LOG`, `SMOOTH` or
`RANDOM_UNIFORM` remain tables rather than becoming mathematical calls. These
are local/vendor aliases, not reserved XMILE core names. A translation cannot
introduce a name that resolves to another table. Core-reserved element and graphical-function
definitions, including unused or padded-name forms, fail explicitly. Existing identifier
restrictions and their three strict expected failures remain unchanged.

Unmapped helpers, unsupported arities, nested convenience `LOOKUP`, floor division
and binomial calls fail with an actionable export error instead of producing
unimplemented function calls. JSON preserves these model definitions. This is a
bounded exporter repair, not a claim of complete XMILE conformance or support for
every vendor dialect. Import parsing and the numerical evaluator are unchanged.

Distribution parameters and explicit function seeds survive these translations.
XMILE does not promise another vendor's RNG algorithm will reproduce this
engine's exact sequence. Within this engine, implicit random streams additionally
depend on source position. The exporter compares their original positions against
the final exported expression whenever a model seed is declared, including the
existing top-level lookup conversion. A translation that changes those identities
is rejected; users can use explicit function seeds or JSON. This prevents a
previously silent seeded lookup roundtrip change independently reproduced during
the review.

## Verification

`tests/test_xmile_interoperability_v19_c.py` adds 116 focused cases with exact
source-defined emitted forms, Euler/RK4 alias roundtrips, logarithm reference
values, an independent Euler smoothing recurrence, pulse magnitude/integral,
Python RNG reference draws for explicit seeds, table shadowing, unsupported
boundaries, and seeded lookup identity preservation. Fixed-history delay plus RK4
retains the engine's explicit unsupported-method error on both sides.

The new cases and existing XMILE feature/roundtrip/storage regressions pass:
**166 passed**, with the existing MCP/Pydantic settings warning. This verifies
emitted source forms and this engine's importer; it is not a third-party simulator
certification. No corpus model, dependency, or interface changed.

## Bounded syntax audit

The follow-up compares every visitor accepted by `SafeEvaluator` against the
export path, using OASIS sections 3.2.1 and 3.3 for the numeric/operator grammar.
This closes the verified gaps together rather than maintaining a list of example
equations:

| Local AST family | Export policy |
| --- | --- |
| Real numeric constants | Decimal/scientific forms remain; hexadecimal, octal, binary and digit separators become the same finite decimal value. Boolean literals become 1/0. |
| Names | Core names retain their meaning; `TIME_STEP` becomes `DT`. An unshadowed mathematical `e` becomes `EXP(1)`; a declared scalar `e` and a graphical function called `e` retain their authored meanings. |
| Arithmetic | Addition, subtraction, multiplication, division and power retain precedence; `%` becomes the core `MOD` token, including adjacent source tokens such as `5%2`. Floor division remains explicitly unsupported. |
| Unary, boolean and comparison | Supported logical/sign/relational/equality operators retain evaluator semantics, including the engine's XMILE comparison grouping. |
| Conditional | Python ternary expressions and local IF calls become parenthesized structured IF, retaining lazy branches. |
| Function call | Verified core/alias signatures and graphical-function resolution follow the contracts above. |
| Other AST nodes | Unsupported containers, indexing, attributes, bitwise operations, identity/membership tests, lambdas, assignments and non-real/nonfinite constants fail explicitly. |

The existing random-identity check covers all new syntax conversions. Equal-length
numeric conversion that retains stream position can preserve an implicit seed;
changed positions fail instead of changing draws. Explicit function seeds replay
exactly within this engine. Boolean literal seeds, already invalid in the
numerical evaluator, remain rejected rather than being repaired by conversion to
numeric literals. Independent review spot-checked the final emitted syntax,
lookup seed behavior, and unchanged explicit-seed trajectories.
