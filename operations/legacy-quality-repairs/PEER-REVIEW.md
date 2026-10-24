# Independent repair and retirement review

2026-10-24. Read-only review; no active definitions or database changed. **Approve the exact canonical replacement below and recommend retirement of the five exact active definitions below through the parent's reviewed transaction.** Approval does not extend to a full World3 reconstruction or a repaired option/network/portfolio model.

## Canonical fixed-allocation capital replacement

Approved `world3-capital-fixed-allocation-proposed.json` SHA256 `459290e478027afaa7eedc6e6efb76cf1ce8fb70a0edae04dc328ce1629f1fda`, replacing only `models/classic/world3-capital-sector-cla.json` SHA256 `c03b5139002d5f6c04faee7afbb7a5ecd5ff4e498ac97c0504856fc069d8954c`.

Independently downloaded [pinned capital.py](https://raw.githubusercontent.com/cvanwynsberghe/pyworld3/cdfd0a8f3675c514f27ddc0e00c8d8bd4d1fefb8/pyworld3/capital.py); exact SHA256 `f7fd93e7aea2ab2e8ff99638e37bda0cf9e2e6f0f75c64d1f8bcddf7e2fe866e` matches receipt. Source output divides capital by its output ratio; investment and depreciation laws match the proposed transcription. Defaults for stocks, ratios and lifetimes match. Fixed resource/allocation factors, utilization and omitted feedbacks are expressly authored specialization assumptions. CeCILL upstream rights are disclosed; no source implementation is redistributed or relicensed here.

Independently derived a scalar closed-form reference, separate from the author's matrix-exponential test: a=.95*.27/3−1/14, d=−1/20, b=.95*.2/3; I(t)=I0 exp(at), S(t)=S0 exp(dt)+bI0[exp(at)−exp(dt)]/(a−d). Against actual candidate execution at every801output samples, maximum relative discrepancies are3.58e−12 and2.09e−11. Independently reran all four repair tests:4passed0.68s, including100random-state balances, half-step refinement, ratio sensitivity, input inspection and dimensional consistency. Title and description honestly delimit the two-state frozen-factor subsystem. Source fidelity here means these selected laws and defaults, not full endogenous World3 behavior or historical calibration.

## Five retirement recommendations, exact snapshots

| Active file | SHA256 | Independent basis |
|---|---|---|
| models/classic/world3-industrial-capital-sector-cla.json | `21f934c4e007b71ffd929dbc33e1ab95890497e41ca30bb0aa2db2f5dbd824be` | Reversed capital/output-ratio law and same triangular fixed-coefficient mechanism; canonical replacement provides the reviewed educational mechanism. Do not silently migrate its second ID to the replacement. |
| models/physics/rssler-attractor-phy.json | `6caa6e40a7d9608b597a8457139bf4ce74a475a525b89ddfc65caf08c39308fe` | Independently simulated three corresponding stock outputs: all3201samples bit-identical to retained canonical roessler-chaos-attractor-phy. Equations, parameters, initials and grid match. |
| models/finance/black-scholes-option-fin.json | `9800dffbb1ef0442bb065f82ad71a1d1de74951d8808038871cb6873450ad5e7` | Actual final long-call value −6.18135686576 with underlying105.149745069 and strike100. Deterministic sine underlying, rational delta, incomplete theta and nonterminal time floor do not implement claimed pricing. No clamp or cosmetic relabel is an adequate repair. |
| models/social/watts-strogatz-small-world-soc.json | `f2f753d9ffc31ff7cf4fb1f67b07f76d2eac8803844d74e4cccf546e2ae0a0a0` | Actual final purported mean graph distance .157736753009 is below1; only edge-count transfer stocks exist. No adjacency or shortest-path algorithm supplies the claimed statistic. |
| models/finance/markowitz-portfolio-fin.json | `f7b48c70671182924e7ccc5530706cb3890b96fc9be4aa82c317f0557339d5ab` | Actual initial risk .121655250606 omits the covariance term despite correlation .2. Independent two-asset calculation gives .125538838612. Target weight is literal .6; no optimizer/frontier exists despite description. |

Retained canonical Rössler file `models/physics/roessler-chaos-attractor-phy.json` SHA256 `ca08b64c9f50f6b7aaa57f2217eb9d90d2a628c78e7de926cacf7fe534924eba`. Identical chaotic trajectories establish duplicate execution, not long-horizon numerical accuracy. Its unrelated Lorenz citation needs separate metadata correction. The ranked report's phrase “implicit Euler” should be read as an implicitly selected default Euler setting, not backward Euler; execution is explicit Euler.

Independently accessed [Watts–Strogatz original paper](https://snap.stanford.edu/class/cs224w-readings/watts98smallworld.pdf), whose network construction and graph distances require connectivity information absent from the candidate. Independently accessed [Markowitz original paper](https://traders.berkeley.edu/papers/Markowitz.pdf), which selects portfolios from expected returns and covariance; fixed rebalancing with unused correlation does not supply that method. Neither publication is redistributed. Black–Scholes direct original-paper access was not independently re-established here; negative long-call value and inspected equations already establish the claimed model's failure without relying on inaccessible text.

## Ranked audit scope

Read the full remaining-library report. The three high-priority scientific failures above and exact duplicate are independently confirmed; the capital replacement is source-backed and bounded. Other lower-ranked source/consolidation findings are useful triage, not blanket retirement approvals. Equal abstract RHS shapes or honest static calculators alone do not establish a duplicate. Preserve user-owned copies and use hash-bound active transactions; this review itself performs no admission or retirement.
