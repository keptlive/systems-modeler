# Independent numerical-engine review — 2026-10-20

Scope: `the repository`, branch `codex/restore-sites-mcp`, production baseline `fc8dd03` plus the restoration changes. This review began independently and read-only. The parent subsequently assigned the reviewer exclusive implementation of `app/core/integration.py`, `app/core/equations.py`, this report and `tests/test_engine_review.py`. No remote deployment, provider call or library-model equation edit was made by this reviewer.

## Answer to the central question

Both engine defects and model defects exist. A full run that returns finite numbers demonstrates computational completion only. It does not establish a model's mathematics, assumptions, units or empirical validity. Earlier `operations/library-full.json` and four-step audit counts were generated against changing source and must not be described as certification of the current engine. A fresh full audit needs source/model hashes and its execution settings.

## Confirmed engine defects and repairs

1. **Endpoint integration of hidden states.** Before correction, Euler `SMOOTH(TIME,1,0)` and `DELAY1(TIME,1,0)` returned `[0,1,2,3]` at times `[0,1,2,3]`. For the corresponding hidden-stock equation `dS/dt=(TIME-S)`, Euler must return `[0,0,1,2]`. Ordinary and hidden stocks now compute derivatives from the same previous-time values and commit simultaneously.
2. **Changing smoothing time reset state.** `SMOOTH(1,TIME+1,0)` returned `[0,.5,.333333,.25]`, because the time constant was part of the state key. It now returns Euler `[0,1,1,1]`. Stable identity uses equation name and AST location. Changing material-delay duration or delay/smooth order is explicitly unsupported.
3. **Feedback initialization falsely appeared cyclic.** `Output=SMOOTH(1-Output,1,0)` now initializes from its explicit initial argument before evaluating its input. Its Euler series with unit steps is `[0,1,0,1,0]`. Genuine unresolved initialization still produces an error.
4. **Evaluation used to advance hidden time.** State outputs are now read without advancement. All stages advance simultaneously once per timestep. Conditional expressions choose an output branch; every syntactically present hidden stock continues through elapsed simulation time, including an inactive branch. Fixed-delay history is sampled once per committed time and uses sample-and-hold for fractional delays. Its time-comparison tolerance now scales with floating-point precision rather than assuming a particular time unit.
5. **Constants shadowed user parameters.** Equations using a user parameter named `e` used Euler's constant instead. At least seven library models define `e` or `Pi`. User identifiers now resolve before built-in constants. Built-in constants are case-insensitive when no user parameter matches.
6. **Nested XMILE conditionals were damaged by regex replacement.** `(IF 1 THEN 2 ELSE 3)+(IF 0 THEN 4 ELSE 5)` failed; nested true-branch conditionals could become four-argument function calls. Token-based translation now preserves nesting, grouping and function-argument boundaries, and translates `<>`, boolean operators, exponentiation and single-equals comparisons without changing quoted table names. Validation and connector-reference extraction share the same preprocessed bounded AST, alias rules and reserved names. Named lookup calls accept case/space/punctuation aliases consistently.
7. **Alias/reference collisions were silently accepted.** Name uniqueness now uses the same case/space/punctuation normalization as equation lookup. Duplicate stock IDs or IDs colliding with another stock's name are rejected before flow accumulation. `TIME`, `DT` and `TIME_STEP` are reserved. User `e`/`Pi` remain permitted. Nonfinite initial stock values, nonrepresentable time grids, duplicate table names and hidden-stage work budgets also fail explicitly. Used lookup tables reject empty/nonfinite data and duplicate X coordinates, while intentional single-point constant lookups remain supported.

`SMTH1`, `SMTH3`, `SMTHN`, `DELAYN` and fixed `DELAY` aliases follow the documented function signatures. Existing `SMOOTH`, `SMOOTH3`, `SMOOTH_N`, `DELAY_N` and `DELAY_FIXED` names remain supported. `DELAY(input,time,initial)` treats its third argument as an initial value; four-argument `DELAY` remains unsupported.

## XMILE findings sent to parent

The reviewer reproduced valid single-quoted XML namespaces importing as an empty model; reciprocal DT importing its denominator as a duration; and embedded auxiliary graphical functions discarding their input equation. These were assigned to the parent's parser/export/model changes. The reviewer wired the new table interpolation setting into evaluation: continuous tables clamp endpoints, discrete tables select the lower step and clamp, and extrapolate tables preserve legacy JSON behavior. Round-trip tests are included in the passing verification command below.

The authoritative reference is [OASIS XMILE 1.0](https://docs.oasis-open.org/xmile/xmile/v1.0/xmile-v1.0.html), especially §§3.1.4, 3.4, 3.5.3 and 4.1.3. It describes hidden stocks for smoothing, fixed and material-delay functions, reciprocal DT, and graphical-function interpolation modes. Compatibility with those covered features is not a claim of complete XMILE support; arrays, submodels, macros and other unimplemented constructs need explicit investigation.

## Representative library failures: independent experiments

The following comparisons used the same stored equations, initial conditions and full requested horizon. Only integration method and DT changed. Results below were collected during review before the final source hash snapshot; rerun with the command below for current-source evidence.

| Model ID | Experiment | Evidence and interpretation |
|---|---|---|
| `greenshields-traffic-flow-model-tra` | Default Euler DT=.1 fails at t=1.1; Euler DT=.01 and RK4 DT=.01 finish t=24 | Final density 24.41699 and 24.41726 respectively. Strong evidence of coarse-step numerical instability, rather than an undefined equation. |
| `forest-fire-spread-cli` | Euler/RK4 with DT=.25 and .025 all fail around t=12–12.15 | Fuel depletion can make the fuel stock and then spread rate negative; negative active-fire area reaches `SQRT`. Smaller DT does not remove the domain failure. This is a model-domain/constraint investigation, not proof the engine's square-root implementation is wrong. |
| `nordhaus-dice-integrated-assessment-cli` | Euler/RK4 at DT=5 and .5 fail around 2107.5–2110 | Negative capital reaches a fractional power, producing a complex value. The engine now reports this explicitly. Scientific equations, units and domains require review; changing the method alone does not repair it. |
| `world2-forrester-original-cla` | DT=1 fails for both methods. DT=.1 finishes for both | Euler's final population is -169,763,769.65, while RK4 gives +388,368,204.49. Finite completion and even a smaller timestep do not establish valid population behavior or convergence. |
| `ice-albedo-feedback-model-cli` | Euler/RK4 at DT=1 and .1 all eventually overflow | Failure time moves from roughly t=16.5–24 to t=112.2–113.2. Further unit, physical-domain and convergence analysis is required. |

Other failure classes include missing parameters, mismatched names, duplicate aliases, unsupported arrays/functions, genuine dependency cycles, singular expressions at initial conditions and request-budget limits. A timeout or budget rejection must not be relabeled an invalid scientific model. No equations were invented, clamped or removed to manufacture passing runs.

Reproduction from the WSL source directory:

```python
from pathlib import Path
from app.core.model import Model
from app.core.simulator import simulate

ids = ["greenshields-traffic-flow-model-tra", "forest-fire-spread-cli",
       "nordhaus-dice-integrated-assessment-cli", "world2-forrester-original-cla",
       "ice-albedo-feedback-model-cli"]
for model_id in ids:
    path = next(Path("models").rglob(model_id + ".json"))
    model = Model.model_validate_json(path.read_text())
    for method, divisor in [("euler", 1), ("euler", 10), ("rk4", 1), ("rk4", 10)]:
        settings = model.time_settings.model_copy(update={
            "integration_method": method, "dt": model.time_settings.dt / divisor})
        try:
            result = simulate(model, settings)
            print(model_id, method, divisor, "completed", {
                s.name: result.values[s.name][-1] for s in model.stocks})
        except Exception as error:
            print(model_id, method, divisor, type(error).__name__, str(error))
```

Run with `.venv/bin/python`; no provider credentials or external requests are needed.

## Verification and remaining limits

Command:

```sh
.venv/bin/pytest -q tests/test_engine_review.py tests/test_regressions.py tests/test_xmile_features.py tests/test_xmile_roundtrip.py
```

Latest bounded compatibility pass: **114 passed**, one Pydantic-settings forward-reference warning, 2.83 seconds, including `tests/test_input_validation.py` in addition to the command above. `git diff --check` is clean. The new review tests cover analytical ramp input, changing smoothing time, explicit feedback initial values, simultaneous three-stage updates, fixed/fractional delays, inactive conditional state, mixed ordinary/hidden stocks, parsing, parameter/alias semantics, budgets and time precision.

Running bare `pytest` also discovers legacy root `test_smart.py` / `test_tuner*.py` scripts that require `.env`; collection fails without it. A broad `tests/` run was interrupted because it had loaded an earlier in-progress engine version. Its legacy API tests created three local API/Get/Update test models; their contents and generated names were checked and only those three records were removed. Legacy tests that merely return `(success,message)` do not make assertions under pytest and should not be treated as strong evidence. The explicit regression suites above do use assertions.

Remaining deliberate limits:

- RK4 rejects delay/smooth/random functions instead of pretending to provide RK4 semantics for unsupported hidden state or stochastic operations.
- Material delays require fixed duration and fixed order. Information smoothing allows changing positive finite duration. Nonpositive durations fail explicitly.
- Fixed delays use sample-and-hold history; off-grid delay accuracy is limited by DT. Changing fixed-delay duration is unsupported.
- Random functions are unseeded by the model schema and should not be used to promise repeatable stochastic experiments.
- Finite results, acceptable domain values, numerical convergence, unit consistency, source fidelity and empirical validity are separate checks. Negative stocks are not globally clamped because some quantities legitimately have a sign.
- Full-model unsupported constructs, scientific source citations and broader MCP/API workflows remain the parent's investigation/release responsibility.

## Bounded compatibility pass before release

Added `SIGN(x)`, `ATAN2(y,x)` and the XMILE infix `MOD` operator with floor-modulus sign and multiplication/division precedence. Existing `MOD(a,b)` remains supported. Added safe token encoding for double-quoted UTF8 identifiers and Python keyword variables such as `lambda`; equation evaluation, table references, static validation and connector reference extraction decode the same tokens. Quoted names support the XMILE quote/newline/backslash escapes, while invalid escape forms produce explicit equation errors. Legacy single-quoted strings remain available for `LOOKUP('table name',x)`.

Identifier aliases now preserve Unicode characters, normalize composed/decomposed forms with NFC plus casefold, and collapse equivalent space/newline/nonbreaking-space/underscore runs. Historical punctuation aliases remain supported; ambiguous alias collisions still cause explicit errors. This bounded implementation does not claim complete Unicode Collation Algorithm or full XMILE language coverage. The exporter can use `decode_identifier` and `restore_identifiers` after AST transformations to preserve quoted names; internal encoded names must not be emitted as external identifiers.

Targeted full runs after these changes:

- `building-energy-performance-simulation-urb`: completed, 97 points.
- `circadian-molecular-clock-phy`: completed, 961 points.
- `duck-curve-solar-grid-ene`: completed, 289 points.
- `hivaids-progression-model-epi`: now parses its `lambda` parameter and runs to t=7.9, where infection becomes nonfinite. This exposes a subsequent model/step investigation; it is not a reason to alter the stored equations.
- `heat-transfer-and-diffusion-model-phy`: retains explicit missing `Interior_Temperature` reference failure; adding MOD cannot repair missing model definitions.

`RANDOM(min,max[,seed])` and nonstandard zero-argument `RANDOM()` remain unsupported. Proper support requires isolated per-run/per-call RNG streams, seed lifecycle validation, and repeated-evaluation caching so dependency resolution or stateful inputs cannot consume extra draws at one simulation time. Aliasing the function directly to global `random.uniform` would conceal these semantics. Existing `RANDOM_UNIFORM`/`RANDOM_NORMAL` compatibility functions are unchanged and remain unseeded at the model-schema level.

## Exact reviewer-owned source snapshot

SHA-256 at handoff:

- `app/core/integration.py`: `087ca590ea505d29494aa6827a1ca9df724cba0d1f53f3551fa1a6c927ef1eb4`
- `app/core/equations.py`: `ea23e27fc6d534389971d32399b109d11f415137c7d9c7133a80fba4b44a8f25`
- `tests/test_engine_review.py`: `8c47940cc6cbedc4d49dc3ed8c6f75ec44198f2cab5fb9c53475254602076a0f`
