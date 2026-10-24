# Analytics contract and review

Analytics describes a particular run's recorded samples. It cannot establish that equations match a source, that units are consistent, that a numerical method converges, or that a proposed intervention will work. Input checks and the library investigation remain separate evidence.

## Deterministic calculations

`POST /api/analyze/statistics` works without AI. All original response fields remain: `statistics`, `patterns`, `peaks`, `equilibria`, `correlations` and `time_range`. Additional fields expose qualifications and coverage.

The API and browser fallback require nonempty, aligned finite numeric series with strictly increasing finite times. Strings, booleans, nulls, NaN, infinity, mismatched lengths and duplicate times are rejected; samples are never silently dropped. Bounds match the simulator: 500 series, 10,001 samples and 1,000,000 values. A single sample supports summary statistics but no rate, time average, correlation or pattern inference.

- `mean`, `median` and population `std` describe equally weighted samples. `time_weighted_mean` integrates the piecewise linear trace by the trapezoidal rule and divides by duration. It differs from the sample mean when intervals differ, including a shorter final integration interval.
- Percent change retains `(final - initial) / initial * 100`; it is null at a zero initial value. A negative initial value can make the sign counterintuitive. It is not a growth rate or a measure of improvement.
- Calculations normalize large finite values before summation, dispersion and correlation. Unrepresentable derived quantities become JSON null, with `unrepresentable_metrics` identifying affected summary metrics. No infinity or NaN is emitted as a result.
- Browser interval rates use actual sample spacing. Average rate means net change divided by duration. Acceleration is the difference of neighboring interval rates divided by the separation of their midpoint times. There is no fabricated zero derivative at the start. Unavailable rates are null.
- Raw variance shares are preserved under the existing historical method name `computeSensitivity`, but displayed as **Variance Comparison**. They depend on each series' units and scale and are not causal influence, explained variance or parameter sensitivity. True sensitivity needs explicit perturbation experiments with selected parameters and outcomes.

## Pattern and stability limits

Patterns are conservative shape heuristics. Linear behavior checks interval slopes against the actual time axis. Exponential labels require at least four positive samples with nearly constant logarithmic rates; acceleration alone does not qualify. Other monotonic traces receive descriptive accelerating, slowing or monotonic labels. These rules do not fit or establish a governing equation. Very small nonzero signals are not automatically rounded into a constant series.

Strict local peaks/troughs require a sample to exceed/below both immediate neighbors. Endpoints and plateaus are excluded. This is not statistical significance, interpolation or a frequency analysis.

The legacy `equilibria` field is retained for compatibility. `reached` means the observed final 20% of samples (at least three, only assessed for series with ten or more samples) spans at most 1% of the tail mean magnitude. A floor of 1e-12 of the full-series magnitude handles zero tails. `start_index` marks the assessed window, not an estimated equilibrium onset. `proves_equilibrium` is always false. A slow drift, long-period oscillation or numerical artifact can appear stable in a short window; use longer horizons and convergence checks.

## Correlation coverage and names

Pearson sample correlation requires at least three samples and two varying series. Constant-series correlations are undefined and omitted. Scaled, centered arithmetic avoids cancellation from squaring large raw offsets. Association of two time trends can be strong without any causal connection.

At most 2,000 unordered pairs are assessed in input order to bound request cost. `correlation_coverage` reports total, assessed and omitted pairs; the UI shows omissions explicitly. This is not a ranking-based selection. `correlation_pairs` contains original names in a two-element `variables` array and preserves names containing `|`. The original delimiter-keyed `correlations` mapping remains for old clients; use the new array for unambiguous names.

## Optional AI interpretation

`POST /api/analyze` provides the deterministic fallback when the configured Gemini client is unavailable. `/api/analyze/ask` requires provider configuration and a nonempty question. All three analysis routes validate samples before provider access. `ai_available` and `/analyze/status` indicate configuration presence, not a successful health check. `ai_used` identifies an interpretation that actually completed and parsed successfully. Provider errors produce useful descriptive fallback, with no raw provider exception text exposed publicly.

The prompt supplies actual summary numbers and recorded extrema and requires uncertainty about source fidelity, patterns, equilibrium and causation. Output remains a model-generated interpretation, not validated scientific advice. Tests stub the provider; they incur no paid calls.

## Browser safety and verification

The offline fallback mirrors server formulas and shape rules. A request version prevents a slow previous analytics response from replacing the latest run. Variable names are escaped at rendering, sparkline IDs use numeric indices, and correlation records avoid delimiter ambiguity. Sparklines respect actual time and normalize the vertical domain for large finite values. Collapsible section headers support keyboard activation and expanded state; wide tables scroll within focusable labeled wrappers.

Run:

```sh
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_analytics.py
```

The focused suite checks analytical values, nonuniform time, correct exponential decay versus quadratic acceleration, zero tails, large finite samples, malformed input, pair limits, AI error fallback and configuration/success distinction. If Node is installed, it executes the real browser module to check API/fallback parity, irregular-step derivatives, stable variance shares and escaped correlation markup. Actual browser/platform interaction remains part of the UI QA matrix.