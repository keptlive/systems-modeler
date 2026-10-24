# Isolated legacy quality repair proposals

2026-10-24. This is a review package, not an admission or permission to edit active definitions. See operations/remaining-library-quality-review.md for ranked source/equation findings. No active files or models.db were changed.

## Proposed capital repair

`operations/legacy-quality-repairs/world3-capital-fixed-allocation-proposed.json` preserves canonical ID world3-capital-sector-cla and two capital stocks while correcting the reversed output-ratio law. It is deliberately renamed **World3-inspired capital with fixed allocation fractions**. This identifies the useful mechanism without falsely claiming the full World3 industrial/service sector or a Limits to Growth trace.

Primary implementation: [pyworld3 capital.py](https://github.com/cvanwynsberghe/pyworld3/blob/cdfd0a8f3675c514f27ddc0e00c8d8bd4d1fefb8/pyworld3/capital.py), particularly _update_io, _update_so, _update_icir, _update_scir, _update_icdr and _update_scdr, reviewed2026-10-24. Source ICOR is in years and output divides capital by ICOR. Initial stocks210billion and144billion, capital/output ratios3years and1year and capital lifetimes14/20years follow its documented defaults. The retained .2service/.1agriculture/.43consumption allocations and .05resource fraction are explicitly frozen illustrative controls from the previous library scenario, not reproduction of the source endogenous allocation equations. Capacity utilization is fixed1. The full population, labor, resources, agriculture, pollution and allocation feedbacks remain excluded and are disclosed. Uniform dollars/years annotations are consistent; constant-dollar calibration is not established.

The exact frozen subsystem is I'=[(.95/3)*.27-1/14]I and S'=(.95/3)*.2I-S/20. Output diagnostics are IO=.95I/3 and SO=S/1. The old active IO=3*.95I was ninefold too high for the same declared ratio. A 1900?2100 RK4 grid with quarter-year steps is independently checked against the exact matrix exponential at every output; a half-step run, 100 random-state source-law balance probes and ratio sensitivity are also checked. Four tests pass in0.66s. No clamp or arbitrary growth cap was added.

This is an original mathematical transcription of documented source laws. No pyworld3 implementation, article figures or publication prose is bundled. The upstream implementation states CeCILL terms; no blanket relicensing of it is asserted. SOURCE-SNAPSHOT.json pins the reviewed upstream revision and exact source-file hash. A later full World3 reconstruction needs its own provenance/reference suite.

Recommendation if independently approved: replace only canonical models/classic/world3-capital-sector-cla.json through a hash-bound transaction; consider retiring models/classic/world3-industrial-capital-sector-cla.json as a second fixed-coefficient triangular sector with the same reversed law. The latter should not silently inherit this candidate under a second ID. Existing user copies remain outside this transaction.

## Quarantine recommendation: option pricing

models/finance/black-scholes-option-fin.json is **not repaired in this package**. Default Option_Value ends-6.181356866 despite a long call interpretation. Its deterministic sine path, rational delta and missing pricing terms are not the cited source law. Clamping its price or merely changing the initial value would be scientifically misleading. A complete replacement needs a documented normal-CDF implementation or independently bounded approximation, analytic call-price/delta/theta checks, source-consistent time units, a terminal-payoff treatment and an explicit deterministic-underlying or supported stochastic interpretation. Those have not been established in this package. Recommend quarantine/retirement at the exact hash below pending a separately reviewed complete reconstruction; no claim that an exact repair is impossible.

## Exact duplicate retirement recommendation

Retain models/physics/roessler-chaos-attractor-phy.json as canonical because source/reference identify R?ssler1976. Retire models/physics/rssler-attractor-phy.json only through the reviewed transaction process. Both use identical three-state RHS, .2/.2/5.7 constants, (.5,.5,.4) initials and0?100 Euler/.03125 grid. Independent simulation confirmed all stock outputs bit-for-bit equal under name/case mapping. Both descriptions also contain an unrelated Lorenz1963 citation requiring a separate reviewed metadata correction. No alternative dynamics are lost by consolidating this exact pair.

## Bound snapshots

PROPOSAL.json is a review receipt rather than an executable deployment manifest. Hash changes require a new review. Active snapshots:

| Active path | SHA-256 |
|---|---|
| models/finance/black-scholes-option-fin.json | `9800dffbb1ef0442bb065f82ad71a1d1de74951d8808038871cb6873450ad5e7` |
| models/classic/world3-industrial-capital-sector-cla.json | `21f934c4e007b71ffd929dbc33e1ab95890497e41ca30bb0aa2db2f5dbd824be` |
| models/classic/world3-capital-sector-cla.json | `c03b5139002d5f6c04faee7afbb7a5ecd5ff4e498ac97c0504856fc069d8954c` |
| models/physics/rssler-attractor-phy.json | `6caa6e40a7d9608b597a8457139bf4ce74a475a525b89ddfc65caf08c39308fe` |
| models/physics/roessler-chaos-attractor-phy.json | `ca08b64c9f50f6b7aaa57f2217eb9d90d2a628c78e7de926cacf7fe534924eba` |

Proposed replacement SHA-256: `459290e478027afaa7eedc6e6efb76cf1ce8fb70a0edae04dc328ce1629f1fda`.

Reproduce: `.venv/bin/python -m pytest tests/test_legacy_quality_repairs.py -q`. Numerical conformance and symbolic dimensional consistency do not establish empirical calibration.
