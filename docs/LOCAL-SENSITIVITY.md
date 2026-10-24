# Native local final-stock sensitivity (core only)

The internal `analyze_local_sensitivity(model, parameters, output_stock_id, *, max_work_units=2000000, timeout_seconds=10, cancel_event=None)` service evaluates local partial derivatives of one simulated final stock with respect to explicitly selected constant variables. No HTTP/MCP/UI exposure, persistence, parameter application or existing feature changes are included. Independent resource-contract review is required before exposure.

`model` is an already validated Model. `parameters` is an ordered list of1–8 dictionaries containing exactly `id` and `step`; IDs identify variables, not names. The output selector identifies a stock ID. Steps are explicit positive finite absolute values. Numeric literals include signed/zero constants; computed constant expressions are intentionally not parameter selectors. All element IDs must be nonempty and unique, and names must satisfy existing unambiguous canonical engine rules.

Example, from a normal Python application guarded by `if __name__ == "__main__"` when appropriate for multiprocessing spawn:

```python
report = analyze_local_sensitivity(
    model, [{"id": "growth-rate-id", "step": 0.002}], "population-id"
)
```

## Deliberately narrow admission

Only scalar autonomous continuous Euler/RK4 models whose ordinary and initialization equations have pure dependency DAGs are admitted. No tables, report variables, arrays/modules, discrete periods, time/timestep references, random/stateful primitives, events, conditionals, comparisons, modulo, floor division, min/max/abs or unknown functions. Allowed arithmetic is addition/subtraction/multiplication/division, unary signs and literal integer powers0–16; allowed unary calls are SIN, COS, EXP and ATAN. Division and floating-point overflow can still fail along a trajectory; grammar admission is not a proof of domain validity, smoothness or existence.

Admission uses the canonical equation preprocessor/parser and dependency scheduler. It never evaluates source strings through Python eval or interprets expressions in a separate mathematical runtime. Initialization DAGs include parameter-dependent stock initializers, which are reevaluated from a fresh model copy every run. Flow endpoints must resolve unambiguously to declared stocks. Constant shadowing and quoted Unicode references follow the existing parser.

Before snapshotting, a non-copying recursive inspection rejects more than40000 source visits, nesting beyond32, oversized collection counts, over2MiB aggregate source text (UTF-8 counted in1024-character chunks), nonfinite metadata, integers over1024bits and cycles. Cheap element counts run before this traversal. This covers preserved source documents, connectors and unused metadata as well as numerical elements; a caller-owned huge Model cannot force an unbounded model_dump/json.dumps allocation before rejection. The subsequently serialized complete JSON must still fit2MiB. Input is then snapshotted through validated JSON before execution. Only the selected variable's literal equation changes in each copied simulation; no tuner clamps, stock edits or saved-model writes occur. Model content hash, engine hashes, sensitivity-module hash, contract version, exact settings and selected IDs are retained as provenance.

## Numerical meaning

Baseline is evaluated once. For each parameter p, runs use p-h,p-h/2,p+h/2,p+h while fixing all other selected parameters at baseline. Values must be finite and distinct. Actual floating-point displacements must agree with requested displacement within relative1e-6; materially distorted geometry is rejected before any run.

The reported derivative is the derivative at p of the quadratic interpolant through the actual inner sample coordinates and baseline. The outer interpolant supplies the coarse comparison. Unequal-coordinate weighting uses normalized distances, so even very large finite spacings do not overflow a+b. Opposite-signed output subtraction uses scaled quotients if subtraction overflows. Nonfinite final derivatives produce failed rows.

Refinement and one-sided slope disagreements are dimensionless and have no dimensionful normalization floor. A row is labeled `unstable_or_nonsmooth` when refinement disagreement exceeds.01 or one-sided disagreement exceeds.1; otherwise it is `locally_consistent`. These are conservative sampled diagnostics, not differentiability proofs, confidence intervals or guaranteed derivative error bounds. A smooth stationary quadratic can trigger the asymmetry warning. Oscillation can alias both scales. Equal sample/baseline outputs raise a resolution warning; the service cannot distinguish rounding/solver noise from exact zero influence.

Elasticity pD/F is optional. Zero baseline output gives null with a reason. Nonrepresentable elasticity gives null rather than infinity or a false zero: nonzero p and D whose binary-exponent result underflows to zero produce elasticity_underflow. True zeros from p=0 or D=0 remain zero. A nonzero baseline whose magnitude is at most1e-12 of the largest baseline/sample output magnitude raises small_baseline_warning while retaining finite raw derivative and elasticity. This ratio has no dimensionful floor and is invariant under multiplicative output-unit conversion. Binary-exponent arithmetic avoids intermediate overflow/underflow where the final value is representable. Raw derivative units are output units / parameter units; both labels are returned, without cross-unit percentage ranking.

The derivative is of the selected discretized solver's final sample. It approximates the continuous ODE sensitivity only with separate timestep/error evidence. Final sample time is checked for exact equality to the declared end, including translated starts and partial final intervals. Local zero partials do not establish global irrelevance or lack of interactions. No Sobol/Morris/global variance decomposition is claimed.

## Hard resource contract and proof

Admission caps:

| Resource | Limit |
| --- | --- |
| Model JSON snapshot |2MiB |
| Elements |100 |
| Element IDs/names/unit labels and settings unit label |128 characters each |
| Combined equation text |32768 characters |
| Combined canonical AST nodes |4096 |
| Retained sample points per run |2001 |
| Selected parameters / runs |8 /33 |
| Aggregate reserved engine work |2000000, caller may lower |
| Per-run reserved engine work |1000000 |
| Scalar report payload |65536 UTF-8 bytes before pipe publication |
| Worker deadline, including slot wait/startup |10s default, at most30s |

A uniquely created mode0600 temporary artifact holds the bounded JSON input. Process.start receives only small handles, its path and a function identity; it does not synchronously pickle/write the full model while the child imports its main module. The artifact is removed in cleanup on success/failure/interruption and never returned in provenance. This is temporary internal input, not a saved model. Cleanup failures propagate, with the concurrency slot still released.

One worker slot exists per calling Python process, guarded by a thread-safe bounded semaphore. This is not a cross-server/process-wide quota. There is no public endpoint; a future multiworker transport must supply its own shared admission/concurrency policy. Only POSIX platforms are admitted: worker publication is bounded JSON in a length-prefixed pipe frame. The parent reads the file descriptor nonblocking in4096-byte chunks, validates the maximum65536-byte frame and checks cancellation/deadline between reads. No blocking recv follows a readiness check, so a partial frame cannot evade the deadline. Malformed, incomplete or oversized frames are explicit worker failures; no valid partial row is returned.

Each experiment runs simulations sequentially in one spawned child and discards each trajectory after retaining its selected scalar. At most200100 scalar result values exist per run before reduction; copied source/AST and interpreter overhead are additionally bounded by input/admission caps. This is a finite structural memory bound, not an operating-system RSS limit.

For N admitted elements and S intervals, define ordinary engine charge
`O=(S*(5 for RK4 else1)+1)*max(1,N)`.
The engine includes all elements in this charge even though known stocks do not execute an equation at every stage; this is the engine's work unit, not a CPU instruction count. No random/history/report work is admitted.

A successful admitted DAG evaluates each equation once per stage and has no dependency retries. If an equation fails, completed stages have no retries and execution stops at the first failed stage. Its pending equation set contains at most N entries; every progressing pass removes at least one, and the final stalled pass terminates. Thus at most N² attempts bound that failed stage's extra retries conservatively. Reserve `R=O+N²` for every run, then reject before worker creation unless `(1+4P)*R <= aggregate_limit`. This includes failed runs and initializers without changing any existing engine global limit. Equations retain bounded AST/text, so one charged equation cannot introduce unbounded user code. This proof depends on the admitted grammar and current evaluator/scheduler semantics and must be rechecked when either changes.

`total_reserved_work` and `charged_reserved_work` are conservative allocations, explicitly **not measured actual work**. Every attempted run consumes its full reservation, including failures. `successful_engine_work` sums successful engine charges. Deterministic explicit successful DAG simulations currently omit their diagnostic dict when there were no retries; in that case the service derives the exact engine O formula. Tests independently intercept the engine's reserve_work calls and safe_eval attempts to verify these relationships for both methods and initialization/failure DAGs. Failed equation-attempt counts are not fabricated as successful engine measurements.

The parent process enforces a monotonic worker deadline. Cancellation can be supplied with an Event-like `is_set()` method; polling is at most20ms apart during slot wait/execution. Deadline/cancellation terminates and joins the child, escalates to kill if necessary, closes both pipe ends and releases the slot before returning. No partially completed row is returned as valid on interruption. If interruption happens after process start, exact completed work is unknown: the whole experiment reservation is charged and counts are null. If queued/pre-cancelled before start, charged work and counts are zero. Bounded admission/provenance preparation precedes this worker deadline. Process-creation infrastructure exceptions propagate after cleanup and slot release.

## Failure/result contract

Admission raises LocalSensitivityError with code invalid_request, invalid_selector, invalid_step, unsupported_model or capacity before starting a child. Baseline failure returns baseline_failed and no rows; any failed perturbation invalidates that entire row, preserves finite successful sample outputs and bounded failure messages, and returns partial_failure. Other independent parameter rows continue within the pre-reserved run allowance. Failed rows have no derivative. Output arithmetic failure also invalidates the row. Worker loss, deadline and cancellation are explicit statuses with provenance. No silent zero substitution, step clipping, one-sided fallback or implicit AI run occurs.

## Verification and release boundary

`tests/test_local_sensitivity.py` includes independent exponential continuous/discrete references for Euler/RK4, parameter-dependent initial conditions, exact endpoint handling, canonical Unicode/constant shadowing, zero parameters/output, actual sample geometry, transformed units, extreme finite stencil arithmetic, smooth stationary-point warnings, exact reservation boundaries, actual engine charge/attempt probes, failed baseline/perturbations, unsupported syntax/models/selectors, input immutability, real spawned process deadline/cancellation and concurrent-worker/slot-recovery checks.

The source research and primary references remain in [SENSITIVITY-RESEARCH.md](SENSITIVITY-RESEARCH.md). Numerical formulas are original elementary implementations; no new third-party runtime dependency is introduced.

Before exposure, independently review the proof and worker lifecycle, add shared quota policy for the actual transport/process topology, and test actual HTTP/MCP callers with preservation checks for existing tuner, variance analysis, scenarios and chart controls. This core implementation does not authorize or implement that exposure.


## Independent review corrections

The first review found that Connection.poll() followed by recv() could block after a partial frame; a spawned worker writing a header and one byte reproduced a deadline overrun. Publication now uses bounded JSON with nonblocking incremental POSIX reads. Real spawned regressions cover stalled partial publication (deadline), immediate incomplete EOF (worker failure), child cleanup and subsequent slot recovery.

The reviewer also identified retrospective snapshot admission: checking2MiB after model_dump/json.dumps allowed arbitrarily large caller metadata to allocate first. The new bounded pre-dump traversal and cheap count gates run before serialization. Regressions replace Model.model_dump with a forbidden callback and confirm early rejection of huge description/element lists, metadata breadth/depth, giant integers and cyclic diagnostics. Caller content is never changed.

Current focused suite:68 passed in3.45s. Existing scheduler/execution-plan checks are rerun alongside these before final review freeze.


Further startup review reproduced a deadline overrun when a spawned main module imported slowly and Process.start synchronously tried to publish a large model. The private bounded-input artifact/small bootstrap closes that request-payload path. A standalone script with a two-second child main import and200000-byte description now respects a.5-second deadline, leaves no child, and has a dedicated regression. Normal Python multiprocessing runtime/environment setup remains an execution prerequisite; the input payload is no longer carried in its synchronous bootstrap. Mutable Model snapshot validation failures now consistently wrap into LocalSensitivityError invalid_request instead of leaking Pydantic validation exceptions.

Latest focused suite:71 passed in4.27s.


Final diagnostic review additionally found a finite derivative whose nonzero elasticity underflowed to a false zero. The explicit underflow reason and unit-invariant small-baseline warning now have regressions, including true-zero controls. These are scalar reporting changes only; worker/admission/resource semantics are unchanged.
