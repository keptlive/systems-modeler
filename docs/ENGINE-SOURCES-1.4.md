# Engine source compatibility review 1.4

This review addresses supported scalar equation semantics, not scientific certification. Work is limited to the equation evaluator and independent regressions. Model source restoration belongs to the separate model investigation. The historical public audit `operations/library-full-v130.json` contains 935 completed default runs and 143 failures among 1,078 definitions; the user-visible count of 145 also included two private definitions. Public reports must not disclose private model contents.

## Confirmed engine corrections

| Behavior | Independent expected result | Correction |
| --- | --- | --- |
| Exact Vensim function spelling | `IF THEN ELSE(1<2,3,4)` is 3; `IF THEN ELSE(X=0,1,1/X)` at X=0 is 1 without division | Normalize the three unquoted tokens only when followed by `(`. Keep lazy branch evaluation and nested XMILE statements. |
| XMILE comments | `2*3 { product } + 4` is 10 | Remove brace comments before tokenization, preserving newlines and braces within quoted identifiers/table names. Reject unclosed comments and unexpected closing braces. |
| XMILE comparison association | `3>2>1` is 0; `2=2=1` is 1 | Fold relational and equality groups left to right instead of Python comparison chaining. |
| XMILE comparison precedence | `1=2<3` is 1; `(1=2)<3` is 1 | Relational operators bind above equality. Parenthesized nested expressions retain their grouping. |
| Malformed context calls | Extra arguments are errors | LOOKUP/WITH_LOOKUP/STEP require exactly two arguments; PULSE/RAMP accept two or three. Previously additional arguments were ignored. |
| Malformed inline lookup data | A malformed pair raises an error | Reject the whole malformed point set instead of silently discarding entries. Accept two-coordinate tuple or list pairs consistently. |

No integration algorithms, state/seed semantics, caps, default lookup extrapolation, or model definitions are changed by this engine patch.

## Authoritative evidence

The [OASIS XMILE 1.0 standard, sections 3.3.1 and 3.3.4](https://docs.oasis-open.org/xmile/xmile/v1.0/os/xmile-v1.0-os.html) specifies operator association/precedence, numeric Boolean results and brace comments. Its relational group precedes the equality group. Binary operators in these groups associate left to right. Python comparison chains therefore cannot be used directly for XMILE equations.

The [official Vensim IF THEN ELSE documentation](https://vensim.com/documentation/fn_if_then_else.html) documents the spaced function spelling and lazy selection. This is bounded compatibility with that exact function spelling; it is not a claim that all Vensim operators, macro syntax or distribution signatures are implemented.

Jim Duggan's original [School Closure Initial Model.mdl](https://github.com/JimDuggan/SDMR/blob/89bbfe65c25db5bcca511c10ef6527c8ebe35696/models/08%20Additional/04%20School%20Closures/School%20Closure%20Initial%20Model.mdl) uses the spaced conditional for the threshold flag. Source tree: `89bbfe65c25db5bcca511c10ef6527c8ebe35696`; Git blob: `cc562b6801f23271ed5e0d4fdf431bf8cb542144`; original file SHA256: `770ba0f9b2c16273457c46a43c1ea868967b622d8dfdbf57fa2b7c849c15774b`. Its formula is preserved in the parser regression with underscore aliases for source spaces. Tests check both sides and equality at the threshold. Source restoration also identified missing flows; parser support alone does not establish completeness of an extracted model.

## Remaining failure coverage

These counts describe historical audit error text and overlap; they are not mutually exclusive diagnoses or fresh-source certification. Across 143 public failures: 82 mention unknown variables, five unknown functions, 41 nonfinite results, nine division by zero, four mathematical domain errors, two complex values, two unsupported AST node types, two syntax errors, and one reserved-name conflict. Four mention unsupported function arity. Current model repair work may already have resolved individual entries.

| Candidate / historical affected definitions | Engine versus input boundary / next evidence needed |
| --- | --- |
| `school-closure-initial-model` | Confirmed parser defect corrected here. Original source also contains dynamics omitted by extraction; separately restored. Current combined working tree default run completes 561 points, which is not an engine-only impact measurement. |
| `labor-market-dynamics-model-eco` | Unmatched closing parenthesis is malformed input. Recover the original formula rather than making the parser discard parentheses. |
| `world3-non-renewable-resources-sector-cla`, `global-carbon-cycle-model-cli`, `sea-level-rise-and-ice-sheet-dynamics-model-cli`, `workforce-model-eco` | Missing named response functions/tables and/or variables. Recover their original definitions. Do not invent a generic function or fuzzy variable alias. |
| `rookies-and-experts-workforce-model-man` | LOOKUP is used with input/inline-points arguments, then an ordinary auxiliary is called as a graphical function. There is no declared table. Recover the source graph and distinguish dialect semantics from extraction errors. This patch does not reinterpret its LOOKUP call. |
| `subscripted-population-model-massachusetts-towns-eco` | Arrays/subscripts remain unsupported; input also contains a literal ellipsis in a population vector and a four-argument DELAY of unverified dialect. Implementing arrays cannot recover missing numbers. |
| `sterman-workforce-hiring-man`, `lac-operon-gene-regulation-phy` | One-argument STEP remains explicit unsupported. The [official Vensim STEP example](https://www.vensim.com/documentation/20770.html) uses height and start time; no source establishes the intended missing argument. |
| `wright-fisher-genetic-drift-evo` | Bare RANDOM() remains explicit unsupported. The [official Vensim distributions](https://www.vensim.com/documentation/fn_random.html) distinguish RANDOM 0 1(), RANDOM UNIFORM and five-argument RANDOM NORMAL. They do not establish this bare spelling. Do not silently alias five-argument truncated normal to the existing two/three-argument normal. |
| `agricultural-water-demand-cli` | Defines reserved DT. Source correction requires an explicit intended name/meaning; do not overwrite simulation time-step semantics. |
| Other nonfinite/domain/zero-division cases | Finite output is insufficient evidence. Source equations, dimensions, initial conditions and convergence/domain checks are necessary before attributing these to the engine. |

A static scan of all 1,078 historical audit paths found no brace comments, comparison chains or excess arguments to the corrected context functions in the current definitions. These standards fixes prevent incorrect imported/new models; they do not account for existing library failures beyond the documented conditional case.

## Verification

Run from the WSL source repository:

```sh
.venv/bin/pytest -q tests/test_engine_sources_v14.py tests/test_engine_review.py tests/test_regressions.py tests/test_xmile_features.py tests/test_xmile_roundtrip.py tests/test_input_validation.py tests/test_model_investigation.py tests/test_analytics.py tests/test_workspaces.py tests/test_repair_manifest.py
```

Result: **281 passed**, one existing Pydantic-settings forward-reference warning. Analytic constant-rate stock integration exercises both Euler and RK4 through the new syntax: a rate of 2 over two time units yields stock 4 with half-unit output spacing. Negative tests retain unsupported dialect errors and reject data that was formerly silently truncated. No production deployment or remote model changes were performed by the engine reviewer.
