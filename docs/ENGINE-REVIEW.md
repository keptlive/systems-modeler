# Independent numerical-engine review — 2026-10-20

Scope: the repository's shared numerical engine and restoration changes. An independent review was followed by implementation and regression checks for integration, equation evaluation and engine behavior.

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

- RK4 now integrates exponential delay/smooth stages together with visible stocks. Fixed-history delays and stochastic calls remain explicitly Euler-only; no stochastic differential-equation interpretation is claimed.
- Material delays require fixed duration and fixed order. Information smoothing allows changing positive finite duration. Nonpositive durations fail explicitly.
- Fixed delays use sample-and-hold history; off-grid delay accuracy is limited by DT. Changing fixed-delay duration is unsupported.
- Supported random functions use isolated per-run/per-call streams, explicit seeds and a returned effective run seed. Reproducibility is defined for this engine/runtime; identical seeds do not imply cross-vendor bit identity or coupled paths under timestep changes.
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

The subsequent stochastic/RK4 pass below implements the previously deferred seeded stochastic runtime. Nonstandard zero-argument `RANDOM()` remains explicitly unsupported; no library equation was rewritten to assume a distribution.

## Seeded stochastic evaluation and hidden-state RK4

This iteration implements `RANDOM(min,max[,seed])`, `RANDOM_UNIFORM(min,max[,seed])`, `NORMAL(mean,sd[,seed])` and `RANDOM_NORMAL(mean,sd[,seed])`. Function seeds must be integer-valued numbers in `[0,2**32)`, with booleans and fractional values rejected. A changing function seed causes an explicit error rather than silently resetting its sequence. Bounds and distribution parameters must be finite; reversed uniform bounds and negative normal deviation are errors. Zero-width uniform distributions remain exact even at the largest finite floating-point value.

Each run creates an isolated runtime and returns its effective `random_seed` when the model contains stochastic calls. When the caller omits a run seed, a fresh 32-bit seed is chosen and can be replayed through `TimeSettings.random_seed`. Each call site has a separate stream; explicitly supplied function seeds initialize that stream directly, while omitted function seeds derive stable streams from the run seed and equation/call identity. Reordering equations or adding unrelated stochastic equations does not perturb existing streams. No process-global RNG is read or mutated.

A call retains one unit draw for the current logical timestep/time. Dependency retries, initial hidden-state evaluation and derivative evaluation reuse it. Conditional branches remain lazy: an inactive direct random call consumes no draws until used. A hidden smooth/delay continues evolving even when its output's IF branch is inactive, so its input noise is still sampled when its derivative is needed. These rules are tested explicitly. Uniform draws use Python's isolated `random.Random.random()` stream; normal draws use the same isolated generator's Gaussian operation. The contract promises replay for this implementation/runtime, not identical sequences in every vendor or Python version.

RK4 now treats every exponential delay/smooth stage as an additional stock and evaluates four simultaneous visible/hidden derivative stages. It supports first-/third-/N-order fixed-duration material delays, information smoothing with positive changing duration, explicit feedback initialization, and coupled visible/hidden equations. Verification covers closed-form ramp/step/feedback responses, fourth-order convergence, a damped visible/hidden oscillator, and exact conservation of origin + destination + material in transit. Fixed-history `DELAY`/`DELAY_FIXED` and all stochastic calls still require Euler; RK4 is not silently substituted for an unverified stochastic or history algorithm.

Work bounds count hidden stages and stochastic call sites. RK4 charges five evaluations per step (four derivative stages plus accepted output), with a one-million-work-unit ceiling in addition to the 10,000-step and 500-element limits. Flow connectivity is compiled once; derivative accumulation now scales with the number of flows rather than stocks multiplied by flows. Existing fixed-history queues retain only the existing bounded simulation history, and random caches retain one draw per call rather than all past draws.

The compatibility sweep also caught and repaired MOD function disambiguation after IF/THEN/NOT; e.g. `IF MOD(TIME,7)<5 THEN ...` now remains a function call. XMILE NOT now has its specified unary arithmetic precedence instead of Python's lower-precedence logical-not grammar. Internal unary AST representation is restored to external NOT syntax during export transformations.

Latest focused command: `.venv/bin/pytest -q tests/test_engine_review.py tests/test_regressions.py tests/test_xmile_features.py tests/test_xmile_roundtrip.py tests/test_input_validation.py`: **180 passed**, one existing Pydantic-settings warning, 2.39 seconds. Parent-owned tests now also check the new capability/seed schema; exact release verification should run again against the final complete source snapshot.

Targeted source-unchanged library evidence:

| Model | Result with this iteration |
|---|---|
| `uncertain-seiar-covid19-epi` | Full 1,461-point run with seed 42; two runs match bit for bit. |
| `sird-ekf-covid19-epi` | Full 721-point run with seed 42; two runs match bit for bit. |
| `weitzman-prices-quantities-eco` | Full 51-point run with seed 42; two runs match bit for bit. |
| `skill-learning-forgetting-edu` | Full 401-point default run after MOD disambiguation. |
| `diabetes-glucose-regulation-hea` | Full 241-point default run after MOD disambiguation. |
| `learning-and-forgetting-curves-model-edu` | MOD now parses; missing model parameters remain explicit. |
| `inventory-and-supply-chain-dynamics-eco` | Full 401-point Euler and RK4 runs, including DELAY3. |
| `sterman-expectation-formation-cla` | Full 401-point Euler and RK4 runs, including DELAY1. |
| `service-quality-dynamics-man` | Full 313-point Euler and RK4 runs, including SMOOTH. |

### Concrete remaining coverage and source backlog

These counts come from a syntax/function scan of the 1,078 unchanged JSON models and the previous 929-completed/149-failed full-run candidate list. They are impact leads, not a replacement for the parent's fresh source-hashed full audit. The previous investigation had 160 union entries; changes above supersede some classifications.

| Remaining feature or investigation | Exact observed impact | Required next evidence / boundary |
|---|---|---|
| Nonstandard `RANDOM()` | 1 model: `wright-fisher-genetic-drift-evo` | Recover the original dialect/source before assuming U(0,1). Current error names the unsupported arity. |
| Nonstandard single-argument `STEP` | 2 models: `sterman-workforce-hiring-man`, `lac-operon-gene-regulation-phy` | OASIS STEP takes height and start time; verify whether the source dialect intended a unit-height step. No guessed default. |
| Array/subscript integration | 1 model: `subscripted-population-model-massachusetts-towns-eco` | The supplied initial array also contains an ellipsis, so array support alone cannot recover missing population data. |
| Inline lookup dialect / scalar auxiliary invoked as a function | `rookies-and-experts-workforce-model-man`; related missing graph in `workforce-model-eco` | One model has explicit inline pairs but later calls a scalar auxiliary as a graph; establish original declared graphical-function semantics rather than ignoring the argument. Current errors remain explicit. |
| Missing application-specific graph functions | 6 names across 5 models: `Effect_of_Pressure_on_Hiring` (2 workforce models), `Fossil_Emission_Scenario` (`global-carbon-cycle-model-cli`), `CO2_Scenario` (`sea-level-rise-and-ice-sheet-dynamics-model-cli`), `Resource_Usage_From_Industry` and `Resource_Extraction_Fraction` (`world3-non-renewable-resources-sector-cla`) | These are missing model-specific functions/tables, not omitted standard math built-ins. Recover authoritative tables and inputs. |
| Request workload exceeds service policy | 6 old default failures: FitzHugh–Nagumo, Morris–Lecar, Oregonator, double pendulum, nuclear plant, simple pendulum | Do not weaken global request limits or silently change DT/horizon; a separately bounded long-running job mode is a possible extension. |
| Malformed or incomplete expression data | `full-beer-model` placeholders and `1/R ALPHA`; unquoted spaced symbol in `sales-agency-fit-adjustment`; `IF THEN ELSE(...)` in `school-closure-initial-model`; unmatched closing parenthesis in `labor-market-dynamics-model-eco` | Recover/verify source equations. Tokenization must not invent the intended formula. |
| Missing named lookup tables | Examples include hares/lynxes and capability trap | Their stored table placeholders are zero-valued scalar variables and contain no points; no interpolation implementation can recover erased data. |
| Ambiguous names / reserved simulation controls | 7 old alias collisions and `agricultural-water-demand-cli`'s DT element | Resolve each against source intent; the engine cannot choose between colliding quantities or silently shadow simulation DT. |
| Numerical instability, domain failure, dependency cycles | 65 union-investigation entries under the previous engine | Use full-horizon timestep/solver diagnostics and original equations/units. An adaptive solver or implicit method may be a future feature, but cannot be claimed to fix undefined formulas or negative physical quantities without evidence. |
| Fixed-history delay RK4 and changing material-delay duration | Explicitly unsupported | Needs a verified history interpolation/discontinuity algorithm or material-conserving variable-delay design. Exponential delays are now covered by RK4. |
| Remaining unused XMILE standard functions / units algebra | No specific failing library model currently identified by the scan | Examples include INIT/PREVIOUS, additional statistical distributions and dimensional algebra. Implement only with exact semantics and regressions; current errors are explicit. |

## Exact reviewer-owned source snapshot

SHA-256 at handoff:

- `app/core/integration.py`: `3a9b7030f3a269918d115497018c2eca7ed62f35409da5677d3cf12c7f1a4590`
- `app/core/equations.py`: `1e967ef7d52e8aaac3a64b64eff562b9a22041373f995de4f1284cf3bb60dab1`
- `tests/test_engine_review.py`: `9a3a5f15a78ee823c152798d694ad0f5c5cc386ca30879831a41c5bd9fc319ef`
