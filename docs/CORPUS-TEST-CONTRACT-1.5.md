# Corpus as a test contract, version 1.5

The 1,078 tracked definitions are a test corpus, not a catalogue that can be called correct because it runs. A model can complete with a missing stock derivative, an incorrect sign, a discarded unit conversion or an unrelated citation. A failure can instead reveal a bad imported equation, an unsupported dialect, an unsafe time step or an engine defect. The harness records those observations separately and never rewrites a definition to improve its score.

## Reproduce the evidence

Run from the repository root with the application environment and pytest installed:

```bash
PYTHONPATH=. python scripts/audit_capability_coverage.py \
  --audit operations/library-full-v150.json \
  --output operations/capability-coverage-static-v150.json

PYTHONPATH=. python scripts/audit_capability_coverage.py \
  --audit operations/library-full-v150.json --execute --limit 1078 \
  --timeout 5 --reference-checks \
  --output operations/capability-coverage-v150.json

python -m pytest -q tests/test_corpus_contract_v15.py
```

Freeze engine and model sources while collecting a report. Every engine file and every model has an exact SHA-256; a change during the run invalidates the report and causes a nonzero exit. A historical library outcome is attached as passed/failed only if its model hash and the entire engine hash map match. Otherwise it is explicitly stale. Historical success is never silently promoted to current execution evidence.

The execution limit is explicit, deterministic and bounded. Every tracked model remains in the report, including unselected models, parse failures, unresolved calls, domain errors, worker errors and timeouts. Each selected full-default simulation receives an isolated process and a per-model wall-clock budget. Random models without a declared seed receive the recorded fallback seed 42. A timeout lacks complete invocation evidence and is not interpreted as proof that a function was never called. A legacy corpus failure remains a diagnostic failure in the report; it does not make the entire exploratory command exit unsuccessfully. Infrastructure/source drift or a failed/timed-out independent reference check does produce a nonzero exit.

## What the columns establish

| Evidence | Meaning | What it cannot establish |
| --- | --- | --- |
| Static call sites / containing models | An AST contains a supported call spelling after the real dialect preprocessing | The call executed, its arguments were valid, or its result was correct |
| Runtime invoked models | The evaluator actually entered that call, including a call which then failed | All branches executed, all inputs were covered, or the call caused a later model failure |
| Runtime completed / failed models | An invoking model completed its numerical defaults or failed | Correct function semantics, scientific fidelity, physical validity or calibration |
| Absent from parsed corpus | No parsed equation or string stock-initialization expression contains that name | The implementation is missing or defective; synthetic reference tests are required |
| Historical completed / failed models | A previous audit matches both model and engine hashes | A fresh run, correctness, or anything about unmatched/stale evidence |
| Trusted reference checks | Named independent analytic/reference/invariant tests passed for eight bounded examples | Every function/model is correct or any model is empirically calibrated |

Aliases are inventoried separately. Named graphical functions are recorded separately from builtins, using the runtime's table-name precedence. Comments, descriptions, connector names and quoted identifier text are not regex-counted as function invocations. Syntax errors remain visible instead of disappearing from the denominator. Unknown calls are unrecognized spellings or foreign-dialect/missing-table candidates, **not automatic engine implementation defects**. A model containing a function and failing elsewhere does not indict that function.

## Trusted positive cases

The compact public manifest `tests/fixtures/corpus-contract-v15.json` selects eight existing models and names the actual pytest selectors, independent expectations, source links and source-fidelity limits. The harness hashes the manifest, definitions, test sources, independent reference fixture/generator and provenance receipts, then optionally executes those tests. It does not generate expected outputs using the application engine.

- Educational SIR, vital-dynamics vaccination and SEIR: independently written SciPy/DOP853 equations, closed-population or demographic invariants, positivity, and SIR reproduction/invariant diagnostics. These are explicit illustrative reconstructions, not claims of exact historical-paper replication or fitted disease prediction.
- Educational Solow-Swan and the restored original-author Solow example: independently derived entire-trajectory capital/labor closed forms. Source equation restoration and empirical calibration remain distinct claims.
- Original-author School Closure initial model: pinned source reconstruction, independent epidemic reference trajectories and conserved group populations. Its closure flag is diagnostic; no intervention feedback is invented to make the model more interesting.
- Restored Atmospheric Bathtub: analytic exponential forced/unforced scenarios and the exact Euler recurrence. A zero default trajectory alone would not have exposed the formerly missing dynamics.
- Mechanistic oral two-compartment pharmacokinetics: independent eigenmode convolution, actual elimination/non-systemic sinks, mass conservation, bioavailability and AUC. Drug constants and therapeutic thresholds remain uncalibrated illustrations.

The existing SI library definition is not silently admitted as a trusted positive merely because a generic logistic/SI solution is known. A positive contract needs its particular equations, assumptions and source mapping; the advanced engine matrix separately tests analytic logistic behavior without falsely certifying a legacy definition.

These tests complement `tests/test_advanced_functions_v15.py`, whose synthetic independent cases are needed for absent corpus functions, boundary/domain/arity behavior, stateful trajectories, random replay and integration convergence. The corpus harness references meaningful earlier numerical tests instead of copying their expectations into another implementation.

## Recorded run

The final `operations/capability-coverage-v150.json` contains **1,078 current executions: 941 completed and 137 failed**, with all definitions retained. Its engine snapshot is equations SHA-256 `c6e396749ff0b149624673fcee5e08863fe20ac5b9564e98875abd8114e6e925` and integration SHA-256 `0de0993725c770bae1a5e4508bb0371ab4817c563f9764c9c50efb978c0a3276`; the complete engine map and every model hash are in the receipt. The selected independent reference suite passed **17 tests in 78.31 seconds**. The harness accounting/regression suite passed **13 tests**.

The initial five-second instrumented budget timed out on algorithmic trading, retail profitability and sales-agent market building. Only those three cases were retried at 30 seconds, completing in approximately 20.89, 7.98 and 9.96 seconds. Both attempts and their budgets remain in each row. These are wall-clock/resource observations, not mathematical failures or proof of correctness. To reproduce the completed coverage without the shorter exploratory attempt, use the same full command with `--timeout 30`. Timing and timeout behavior depend on host load.

The final invocation evidence was joined to the subsequent `operations/library-full-v150.json` ordinary audit only after checking the entire engine hash map and all model hashes. The receipt retains the prior audit SHA and explicitly records the rebind; actual invocation counts and independent test outcomes were not synthesized from that audit. The static report also binds to the fresh ordinary audit. The earlier run invalidated by concurrent engine edits is operator-retained separately and is not part of public acceptance evidence.

All 25 statically present function spellings were actually entered during at least one simulation; 24 occur in a completing model. **LOOKUP has no completing corpus example**: hares/lynxes and capability trap refer to missing tables/inputs, while rookies/experts uses `LOOKUP(input, list-points)` and another undeclared graphical-function call. The documented engine forms are named `LOOKUP(table, input)` and inline `WITH_LOOKUP(input, points)`; a legacy spelling mismatch is not proof that table interpolation is unimplemented. Recover original source tables and dialect intent, then add a source-backed positive case. The separate advanced suite tests interpolation semantics independently.

## Initial inventory and actionable gaps

The initial static scan finds 44 declared function/alias names, 25 present and 19 absent. The absent names are ACOS, ASIN, ATAN, DELAYN, DELAY_FIXED, DELAY_N, NORMAL, POW, RAMP, RANDOM_NORMAL, RANDOM_UNIFORM, ROUND, SMOOTH3, SMOOTH_N, SMTH1, SMTH3, SMTHN, TAN and WITH_LOOKUP. A library-only run therefore cannot verify those 19 advertised spellings. Use the independent advanced-function matrix and retain alias-specific checks even when another alias occurs in the corpus.

Five definitions contain unrecognized calls: World3 non-renewable resources, global carbon, sea-level/ice-sheet, workforce and rookies/experts. Their names resemble omitted graphical functions (`Resource_Usage_From_Industry`, `Resource_Extraction_Fraction`, `Fossil_Emission_Scenario`, `CO2_Scenario`, `Effect_of_Pressure_on_Hiring`). Recover original table definitions and units before classifying these as engine defects. Two definitions have parser errors: labor-market vacancy creation has an unmatched parenthesis, while Full Beer retains conflicting/placeholding source syntax. These require original-source reconciliation rather than silent parser guesses.

Case-colliding symbols, dimensional validity, conservation/positivity, missing mechanisms, solver suitability and empirical calibration are separate future corpus contracts. Numerical completion counts do not settle them. This contract is deliberately bounded: eight positive examples do not certify the remaining 1,070 definitions.

## Public-checkout reference portability

The public versions of the v1.4 mathematical/source repair receipts add a `baseline_scope` provenance annotation. Their original JSON fields are identical to the source receipts, but their byte hashes differ. Both public capability reports preserve the original reference inventory/results and canonical report SHA-256 under `canonical_reference_provenance`, and transparently rebind the current reference inventory to the public bytes. The exact 17 selected reference checks were actually rerun in this public checkout: **17 passed in 63.20 seconds**. `public_reference_rebind` records both receipt hash pairs, the annotation-only comparison and that fresh test output. Static model execution remains `not_executed`; its newly attached reference-test result is the separate public portability run.

Producer, every engine file and all 1,078 model bytes match the canonical invocation receipt. Its existing corpus runtime counts and timeout/retry attempts are retained as hash-bound canonical evidence; the public reference rebind does not claim to have rerun the full corpus or invent any outcomes.
