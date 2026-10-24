# Repairing inert model scaffolds — 1.8

## Morris–Lecar

The earlier completion was false reassurance: two stock initializers and eight channel inputs existed, but no differential balances connected them. The repair adds the voltage/current balance and potassium gate relaxation, with type-II gating parameters from [Ermentrout's executable XPP tutorial](https://sites.pitt.edu/~phase/bard/bardware/tut/newstyle.html). The tutorial gives the tanh/cosh gates; algebraically identical logistic/exponential expressions work with the scalar engine. The [official Brian example](https://brian2.readthedocs.io/en/stable/examples/frompapers.Morris_Lecar_1981.html) independently confirms the balance form and units, but uses different experimental parameters.

All existing conductances, reversal potentials, applied current, initial values, IDs, positions and the 400-ms Euler grid remain. Added gating values are explicit inputs; this is a documented teaching adaptation rather than a reconstruction of an experimental trace. One misleading conductance connector now targets the voltage balance. Two signed flows supply actual derivatives.

Independent DOP853 integration uses literal tanh/cosh equations, not the application evaluator. Across all 40,001 output samples, maximum voltage error is 0.348 mV and gate error 0.000940. Potassium activation stays in [0,1] and the voltage has repeated spikes. Over 100 ms the voltage error is 0.04924, 0.02464 and 0.01232 mV at dt=0.01,0.005,0.0025: expected first-order Euler convergence. Four regression tests also verify original-input preservation and initial signed balances. This demonstrates implemented dynamics and numerical convergence, not biological calibration.

Exact original and repaired hashes, preserved baseline bytes and numerical evidence are in operations/corpus-repairs-v18-root.json and tests/fixtures/corpus-baseline-v18-root.json.

## Oregonator

The three-stock shell lacked all derivatives and the fast bromide timescale. The [model author's account](https://www.scholarpedia.org/article/Oregonator), equations 4–6, supplies three balances and an illustrative epsilon-prime of 1.98e-5. The repair implements all three independent scaled concentrations and explicitly adds that parameter while retaining the existing epsilon=.01, q=.001, f=1 and initial values. These remain teaching inputs, not a calibrated chemical experiment. No two-variable reduction or concentration clamp is used.

The new Radau method resolves the stiff bromide kinetics. A 30-unit default observation window, with the original .01 output spacing, produces seven spikes within 272,980 work units. This deliberately changes the inert shell's former 300-unit window: an independent full-300-unit reference completes positively with 62 spikes, but its 185,854 RHS evaluations plus Jacobian/output work exceed the server budget. The shorter default demonstrates the dynamics within that budget rather than concealing an unstable equation.

Independent BDF integration at rtol=1e-10/atol=1e-12 agrees across all 3,001 default samples: maximum absolute errors are 3.94e-7, 1.67e-4 and 4.74e-8 for the three states; maximum error scaled by 1+absolute reference value is 5.26e-6. All concentrations remain positive, and each boundary derivative points into the positive domain. Both original settings and the intentional new solver/window are recorded in the repair receipt. Six root-owned tests cover both restored models.
