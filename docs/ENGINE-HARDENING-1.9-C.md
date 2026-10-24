# Engine boundary hardening, review C

This review tests the same mathematical request through direct Python, REST, MCP,
and the page-workspace store. It changes no corpus model, default solver, or user
interface. The release remains held for the coordinating review.

## Reproduced defects and repairs

1. **Partial settings replaced omitted model settings.** A model configured for
   Radau over 5–6 with DT=.1, submitted to REST with only `{ "dt": .2 }`, ran
   Euler over 0–100. A start-only edit beyond 100 could fail validation before
   inheriting a valid model end time. Workspace edits had the same replacement
   problem. `TimeSettingsPatch` retains supplied-field information and merges
   first, then validates the resulting full grid. All three numerical endpoints
   use the same target/merge helper. Both/neither model targets return 422;
   an absent saved model returns 404.
2. **A translated single step could mask the real equation error.** For start=5,
   DT=.1, the endpoint 5.1 subtracts to slightly less than .1. Validation rejected
   the diagnostic step before evaluating the model. Grid validation and declared
   discrete-period counting now allow representational endpoint roundoff while
   retaining nominal DT. Significant partial periods and origins too imprecise
   to justify a whole interval remain rejected.
3. **MCP discarded causal error metadata.** The SDK converted an engine exception
   into its message alone. Numerical MCP calls now preserve `isError=true` and
   carry JSON `{ "failure": ... }` in the error text. Root errors, blocked
   dependents, capacity codes, effective random seed, model/engine hashes and
   settings remain available. Direct Python still raises the original engine
   exception. Validation's one-step failure also includes this structured cause.
4. **Duplicate IDs silently selected the first element.** Targeted workspace edits
   now reject ambiguous IDs before publishing a batch. Selection similarly
   rejects ambiguity. Static input review flags duplicate IDs, normalized-name
   collisions, reserved simulation names, duplicate lookup names and ambiguous
   stock references even when numerical checks are disabled.
5. **Nonfinite result data could be stored.** `SimulationResult` now rejects
   nonfinite time, numeric trajectories, numeric report leaves and nested
   diagnostic numbers, including dictionary keys. Workspace publication validates
   direct dictionary payloads and performs strict finite-JSON serialization
   before changing revision, result, byte accounting, or view. The final strict
   serialization also catches a mutated/model-copy result that bypassed Pydantic
   field validation. Text report labels such as `Infinity` and `NaN` remain text.
6. **Invalid Unicode identifiers changed in transport.** A variable named by an
   unpaired UTF-16 surrogate directly simulated but REST returned replacement
   characters as its key. Model and result boundaries now reject non-scalar
   Unicode text, including nested dictionary keys, using a cycle-aware iterative
   traversal. Names are never case-folded or Unicode-normalized by this guard.
   Valid supplementary characters and decomposed combining sequences roundtrip
   unchanged. The existing production request-validation handler already omits
   invalid raw inputs and returns a JSON 422; a minimal FastAPI app without that
   handler can fail while echoing invalid text, so tests install the production
   handler. The coordinating report-parser repair separately rejects escaped
   surrogate labels after AST decoding.

## Timing and seed contract

Omitted fields inherit the model, including method, tolerances, origin, endpoint,
seed and recurrence period. An explicitly null random seed requests a new seed;
numeric timing fields cannot be null. An existing declared recurrence cannot be
removed or changed by a simulation override or targeted workspace timing edit.
Changing that mathematical declaration requires replacing the model. Existing
Python callers supplying a complete `TimeSettings` object to `SimulationRequest`
remain supported. Plain JSON objects and `TimeSettingsPatch` are partial edits.

MCP's scalar optional overrides retain their established omission semantics.
Successful sampled output retains both endpoints, original report labels and the
effective seed. Its statistics are computed over the full run. No extra random
draw is made to assemble diagnostics or sampling.

## Evidence

`tests/test_engine_hardening_v19_c.py` contains 46 executable regression cases.
They compare every retained value, report and solver diagnostic for Euler, RK4
and Radau across direct/REST/MCP/workspace execution; exercise start/DT/null/seed
patches and recurrence protection; verify rollback after ambiguous edits and
invalid result publication; check exact Unicode transport; and validate failure
causes and reproduction context.

The real MCP stdio client initializes an SDK session, verifies four-point output
sampling and full-run statistics, replays an automatic seed, and parses a causal
failure from an `isError` tool response. A separate failed stochastic run tests
the effective auto-seed, sampled stock state, and identical failure JSON through
direct Python, REST and MCP replay. Tests use public in-memory fixtures and no
private Git history or service credentials.

Validation: 46 C cases passed; the combined C, API, workspace, input-validation,
discrete-period, report, failure-diagnostic, investigation, independent-review and
root-hardening selection passed 162 cases. The only warning is the pre-existing
MCP/Pydantic settings `lifespan` forward-reference warning.
