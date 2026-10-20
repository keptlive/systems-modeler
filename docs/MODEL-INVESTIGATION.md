# Model input investigation — October 20, 2026

The current frozen v1.3.0 audit checks all 1,078 tracked library files at their full original horizons: **935 completed and 143 failed explicitly**, using seed 42 for reproducible stochastic runs. `operations/library-full-v130.json` records this result and exact input/core hashes. The preceding engine repair baseline had 929 completed and 149 failed. Five additional models now complete after stochastic/engine coverage repairs, and the Sales Agency reconstruction resolves one input failure. Three other source-backed repairs correct misleading finite runs without changing the pass count.

Completion does not establish scientific validity. The 13 additional production definitions were checked privately in the earlier release: 11 completed and two failed. They need a separate refresh against this engine; user definitions are not copied into source control. Public totals above cover tracked definitions only.
`operations/library-full.json` records file and core-source SHA256 values. `operations/library-investigation.json` covers the union of initial and later failures (160 models). Its overlapping diagnostic groups include missing definitions, syntax/function coverage, ambiguous names, workload limits and numerical/domain failures. These findings are evidence to investigate, not instructions to substitute zero or silently clamp stocks.

## Reusable bounded numerical investigation

`app/core/diagnostics.py` exposes `investigate_model(model, max_runs=3)`. It checks the original full horizon with the supplied method at dt, dt/2 and dt/4. It never invents equations, shortens a horizon, calls AI, saves a model or invokes a network service. Existing simulator bounds apply to every run; at most three attempts give a conservative upper bound of 3,000,000 element intervals, including hidden stages, stochastic calls and method-specific work accounting. Oversized grids remain explicitly unattempted. Identical static/initial-time failures suppress repeated invalid runs, unless initialization references DT.

Successful stochastic baselines record their effective random seed for replay; this does not make timestep paths comparable. Equations that reference DT/TIME_STEP carry a warning because refinement can change initial conditions or algebraic inputs as well as integration error. The report contains exact settings, normalized model SHA256, relevant engine-file hashes, input issues, unresolved-symbol equations, domain-sensitive operations, per-stock extrema/negative-value leads, closed-transfer sums and timestep comparisons. Full series remain internal. Differences compare each stock over the entire coarse time grid against the refined trace, using linear interpolation if necessary. Each difference is scaled by that stock's largest absolute value across the two runs. A small difference means at most 0.001 of that scale on the checked grids; it is an explicit descriptive threshold, not a convergence proof or an error estimate against the true solution.

Stochastic calls are identified through the engine's parser, including NORMAL aliases and named-table precedence. Their pathwise refinement comparisons are inapplicable without coupled noise, even with a seed. Stateful/fixed-delay limitations are reported by the engine. No stock means there is no dynamic stock trajectory to compare.

A closed component means every attached flow transfers between stocks in that component. The sum should remain constant algebraically for both integrators. Units and physical meaning still require review; adding people to capital is not a meaningful physical invariant merely because a diagram connects them. Negative stocks and fraction-like names outside zero-to-one are review leads only. Stocks with no attached flows receive an explicit transcription warning. A no-stock model is marked as having no dynamic stock trajectory to compare.

Run the reproducible CLI:

```sh
PYTHONPATH=. .venv/bin/python scripts/investigate_models.py \
  --audit operations/library-full-v130.json --also-rk4 \
  --output operations/model-diagnostics-v130.json
# Optional focused selection:
PYTHONPATH=. .venv/bin/python scripts/investigate_models.py \
  --model sir --model greenshields-traffic-flow-model-tra \
  --output operations/model-diagnostics-focused.json
# Explicit read-only primary-source check (fetches pinned SDX files):
PYTHONPATH=. .venv/bin/python scripts/investigate_models.py \
  --model sir --verify-sir-source --output operations/sir-source-check.json
```

Default selection includes every failed audited model plus representative finite-run concerns. `--also-rk4` runs a separate bounded three-grid investigation with RK4 for eligible originally Euler models; that CLI-only pair of investigations can consume up to six run budgets per model. Input-byte hashes and before/after engine hashes bind the output. Changed files must be re-audited before using a stale audit as the selection baseline.

## Completed deeper investigation

`operations/model-diagnostics-v130.json` covers **150 models**: every one of the 143 failed defaults and seven finite-run representatives. The frozen run took 130.49 seconds. `operations/model-diagnostics-summary-v130.json` is a compact, reproducible summary. Across the default and separate RK4 investigations there were 897 bounded run slots: 94 completed, 415 failed explicitly and 388 were intentionally not attempted because of structural errors, stochastic comparison limits or workload bounds. Counts describe numerical experiments, not distinct scientifically validated models.

Static findings overlap: 65 models reference missing symbols, seven have ambiguous element names, three have malformed syntax and five call absent named functions/graphical functions. The absent calls include fossil/CO2 scenarios, workforce hiring-pressure effects and World3 resource lookups; implementing a generic math function cannot recover their missing data.

Seventeen failed defaults complete on at least one alternate grid or method. That completion is only a lead. Eleven models have domain warnings on completed traces; for example, World2 RK4 at dt=0.5 completes with minimum population −665.8 million, while dt=0.25 still fails. None of the checked closed-transfer sums drifted by more than 1e-10 of the largest component stock.

Greenshields illustrates why final values alone are weak analytics. Euler dt=0.05 and dt=0.025 produce nearly equal final density, yet differ by **22.3% of the trajectory scale** over the full horizon. The same RK4 pair differs by 2.08%. Smaller steps are still needed before interpreting transient behavior. Forest-fire runs retain the square-root domain failure around t=12 under both methods and all three checked grids; reducing a timestep does not restore an omitted physical constraint or a wrong source equation.

No defaults were automatically altered because an alternate run completed. Every report retains exact tested settings and source/input hashes. Re-run the CLI with `--summary-output operations/model-diagnostics-summary-v130.json` to reproduce the compact findings, and `--repair-receipt operations/model-source-repairs.json` to recheck the four source-backed repairs against the recorded original Git revision.
## Exact source-backed repairs

Four tracked definitions were repaired only after the original source was inspected. All other model definitions remain unchanged in this phase. `operations/model-source-repairs.json` records original/new hashes, source hashes and checks. Git retains the originals; deployment must back up and replace these four exact files explicitly rather than synchronizing the model directory.

### SIR benchmark: restore the computed initial stock

`models/other/sir.json` lost the susceptible initial equation during extraction. The [pinned original SIR.mdl](https://raw.githubusercontent.com/SDXorg/test-models/21aab02739dc5187bc9564e4d3de14e575905d2f/samples/SIR/SIR.mdl) initializes that stock from the population parameter. The repair changes only `stocks[name=Susceptible].equation` from empty to `Total_Population`; the numerical fallback, other equations, settings, positions and provenance remain intact.

The [pinned canonical output](https://raw.githubusercontent.com/SDXorg/test-models/21aab02739dc5187bc9564e4d3de14e575905d2f/samples/SIR/output.csv) has 3,201 samples. All three stock trajectories were compared before and after the candidate change. Before repair, the susceptible trajectory was zero. After repair, maximum discrepancies scaled by each stock's full-series peak are below 2.5e-6. The offline regression preserves all 3,201 canonical rows for the three stocks and checks a 5e-6 bound; fixture metadata records the upstream output and subset hashes. No original model source text is bundled.

Source fidelity requires initial susceptible 1,000, infectious five and recovered zero, conserving 1,005 while the infection denominator parameter remains 1,000. Replacing susceptible with 995 would change the benchmark's intended inputs. The parameter's name is not sufficient evidence to reinterpret its equation.

### SI example: restore initialization and missing reporting flow

`models/other/si.json` similarly lost its susceptible initialization and the reporting inflow. The [pinned Cookbook SI.mdl](https://raw.githubusercontent.com/SDXorg/PySD-Cookbook/d7ebddadad9cd87cf796b9b6031ea2b5c45da4c4/source/models/Epidemic/SI.mdl) defines susceptible initially from its population parameter and accumulates incident infections in the reported-cases counter. The repair restores `Total_Population` as that initial equation and adds `New_Reported_Cases = Infection_Rate` as an external diagnostic inflow to `Cumulative_Reported_Cases`. Other inputs/settings remain intact.

Checks verify the conserved susceptible-plus-infected total of 10,001 and reported cases equal infected minus its initial one at every sample. An independent analytic logistic solution, derived from the source's constant contact/infectivity equations, verifies the entire RK4 trace at a half timestep to within 2e-8 of the population scale. This establishes implementation fidelity for this mathematical example, not real epidemic calibration.

### SIR Simple: recover missing flows and a reporting stock

The [pinned Cookbook SIR_Simple.mdl](https://raw.githubusercontent.com/SDXorg/PySD-Cookbook/d7ebddadad9cd87cf796b9b6031ea2b5c45da4c4/source/models/SD_Fever/SIR_Simple.mdl) has four stocks and three stock-changing flows. `sir-simple.json` had three stocks and no flows, so its completed default run was entirely flat. The repair restores computed susceptible initialization, adds the missing cumulative-cases stock, and converts the existing infect/recover/report-case auxiliaries into their source-defined flows. Every existing element ID, position, equation and metadata field is preserved except the evidenced initialization change and the primitive types/endpoints being recovered.

The checked epidemic compartment total remains 1,005, while the separate reported-cases counter equals initial susceptible minus current susceptible. An independent SciPy DOP853 integration of the source ODEs provides golden values at eight times through t=100, using rtol/atol 1e-12. The repaired engine's refined RK4 trace is checked against those values. The source's original default Euler timestep remains unchanged.

### Sales Agency: recover missing parameter and stock dynamics

The [pinned Sales Agency model](https://raw.githubusercontent.com/SDXorg/PySD-Cookbook/d7ebddadad9cd87cf796b9b6031ea2b5c45da4c4/source/models/Sales_Agents/Sales_Agency_Fit_Adjustment.mdl) supplies the good-fit fraction 0.2, valid hiring expressions and four hiring/turnover flows. The extraction omitted that parameter and all flows and left two expressions with unquoted space-containing references. The repair restores that exact parameter, corrects those two references, and converts the four existing hiring/turnover auxiliaries to their source-defined flows while preserving IDs and layout.

Independent closed-form solutions are good-fit agents = 9.6 × (1 − exp(−t/48)) and poor-fit agents = 4.8 × (1 − exp(−t/6)), both initially zero. Productivity is good-fit agents plus half the poor-fit agents. Tests compare every RK4 sample to these equations, alongside the unchanged source default Euler run.

## Other confirmed input problems still pending
- Simple Global Carbon Cycle references `CO2_Fertilization` but defines `CO2 Fertilization Factor`. The name mismatch is concrete; an exact original four-box implementation and its units have not been recovered, so no guessed substitution was applied.
- Beer Distribution Game references absent inventory-adjustment parameters. `Population65+` versus `Population_65plus` also requires reconciliation with original identifiers rather than fuzzy matching.

## Numerical and provenance concerns

Greenshields traffic's default Euler grid is too coarse for the supplied density dynamics; smaller steps or RK4 improve numerical behavior. That does not validate the added queue dynamics or their units. Its stored DOI is independently wrong: [the publisher's DOI record](https://www.nationalacademies.org/publications/22229) identifies a 2014 pavement-program letter, not the claimed 1935 paper. The [Transportation Research Board's historical symposium](https://onlinepubs.trb.org/Onlinepubs/circulars/ec149.pdf), printed pages 6 and 10, describes the linear speed-density relation and cites the original paper. It supports the basic relation, not this generated stock/flow implementation or its parameters. Correct metadata should distinguish the historical relationship from the constructed demonstration.

Forest-fire and DICE examples have domain failures that persist at finer steps. World2 can complete with negative population; its generated simplified multipliers and incomplete source fidelity need review. A title calling a model “Original” does not establish correspondence to a published implementation.

The editor's **Check inputs** exposes definitions and provenance; numerical investigation adds full-horizon grid evidence. Library statuses remain **Default run completed**, **Needs investigation**, or **Not yet checked**, bound to exact bytes. They must never become “scientifically valid” badges based on a finite run.

## Verification

```sh
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_model_investigation.py
```

Tests cover bounded cost, no horizon truncation, no repeated identical invalid attempts, random alias/table precedence, full-time comparisons including a short final step, RK4/Euler analytic examples, closed-transfer sums, signed-stock leads, source changes, stable model hashes and all four repaired source-backed models. They do not require network access or paid providers.

The repository includes the compact sweep summary. Generate the full detailed report with the documented CLI; large diagnostic run output is kept outside the public change set.
