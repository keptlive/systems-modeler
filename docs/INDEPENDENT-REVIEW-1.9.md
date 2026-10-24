# Independent review — 1.9

Reviewed the report-output and fixed-period changes against baseline `3597bbc`, including model validation, report AST handling, numerical integration, Radau budgeting, REST validation/investigation/simulation, MCP sampling, workspace edits/results and desktop/mobile rendering. The reviewer did not modify runtime files. Root implemented the corrections below; independent regressions exercise them.

## Defects found and corrected

1. **Targeted workspace settings edits could erase a recurrence declaration.** Starting from `Balance=8`, flow `−0.5*Balance`, period/DT 1 and end 3, a targeted MCP element edit with `TimeSettings(dt=.5)` and omitted period replaced the entire settings object. `run_workspace` then returned `1.423828125` instead of the native recurrence's `1`. Targeted settings now retain the stored period and validate the complete proposed model atomically. An invalid timing edit leaves both revision and initial stock unchanged. Explicit whole-model replacement remains a deliberate way to change the definition.
2. **Different duration/grid tolerances could create an extra partial recurrence.** End time `3.0000000005`, period 1 passed the old whole-period tolerance but `ceil(count−1e−10)` produced `[0,1,2,3,3.0000000005]`. The shared interval-count function now accepts only representational roundoff, and discrete integration uses the resulting integer count and the exact declared period for each update. The counterexample is rejected.
3. **The first rounding correction rejected translated decimal periods.** Three `.1` periods at origin zero passed, while origin 1000 or 2000 failed because subtracting endpoints introduces cancellation error larger than an ULP of the resulting count. The shared check now accounts for endpoint ULPs. Independent tests require exactly three updates and `[8,4,2,1]` at all three origins, including a numeric report with exactly four retained values.

The same recurrence contract now applies to direct simulation overrides, all three REST paths, MCP simulation overrides, targeted workspace edits and saved workspace results. Decimal roundoff does not add a fractional update. The Beer Game now declares its actual weekly period rather than permitting a fractional approximation to be presented as the same board game.

## Report isolation and budgeting

Independent tests verify identical numeric trajectories with and without reports for Euler, RK4 and Radau; seeded binomial inputs also retain identical streams. Report aliases cannot feed numeric equations or other reports, including inactive branches and quoted/underscored aliases. Random/stateful report calls are rejected before integration. Named table lookup remains available, and actual retained values determine lazy report branches.

Report output is separate from numeric statistics and chart data. MCP report samples use the same retained indices; workspace result serialization preserves roles and text. Both desktop and mobile use the same rendering method, which escapes names and values. The review checked this security-sensitive rendering path; root separately ran the actual desktop/mobile browser checks.

Worst-case retained label characters and report evaluation work are reserved before numerical integration. The independent preflight test deliberately includes a bad stock equation and confirms the report-capacity error occurs first. Report work is included in the combined Euler/RK4/Radau accounting; placeholders retain element/series accounting and are removed from numeric results. JSON preserves the new fields, while XMILE export explicitly rejects unsupported roles and recurrence declarations.

## Scientific spot checks

The reconstructed rigid-column pipe equation now includes pipe area in volumetric-flow acceleration. Its laminar force simplifies exactly to `8πρνLV`, with the correct zero-flow limit; turbulent Darcy force is `fρπDLV|V|/8`. This is consistent with its stated rigid-column and quasi-steady-friction scope, not an exact radial Navier–Stokes startup solution.

Reactor precursor release removes the precursor once and creates the delayed neutron once. Separate fuel/coolant tendencies divide the same heat transfer by their respective heat capacities, preserving the thermal energy transfer. The reconstruction review confirmed that the original KTH Example 3-2 specifies the unusual `n_e=200 m⁻³` and power factor `7×10⁶ J m³ s⁻¹`; those are literal educational-source values, not a claim of plant calibration.

The options benchmark's finite-threshold value and delta satisfy the usual value-matching/smooth-pasting expressions for its declared regime. The `mu=r` branch represents the no-finite-exercise-threshold limit explicitly. The description correctly identifies deterministic sinusoidal noise and the limited exercise-policy scope; this is not a Monte Carlo GBM simulation or a generally path-dependent construction model.

These are equation and implementation checks, not empirical validation or certification of every scientific assumption.

## Verification

The independent suite is [test_independent_review_v19.py](../tests/test_independent_review_v19.py). The combined focused run includes the existing report/discrete suites and the six source-adaptation checks in partition A:

```text
.venv/bin/python -m pytest tests/test_independent_review_v19.py tests/test_report_outputs.py tests/test_discrete_period.py tests/test_corpus_repairs_v19_a.py -q
55 passed, 1 warning in 41.17s
```

Historical probe runtime hashes remain hashes of the engine actually used for those probes. They are not rewritten to masquerade as later runtime evidence; the final full-library audit is a separate root-owned release check.
