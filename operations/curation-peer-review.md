# Library curation peer review

Targeted read-only scientific review plus explicitly assigned metadata-only clarification of three retained calculators. No runtime or equation edits. Current inventory and screen receipts were examined, not a full source-fidelity audit of all definitions.

## Keep

- models/other/kingman-formula-variability-ops.json: proper Kingman mean waiting-time approximation; Wait_Time=4 at default utilization0.8 and process time1. Queue_Time is inert. Label as static approximate calculator; utilization must be below1.
- models/energy/solar-panel-power-output-ene.json: valid fixed-temperature PV correction and Power=320 at STC. Power_Output is inert. Label static calculator; no thermal or diurnal simulation.
- models/transportation/lighthill-whitham-richards-traffic-tra.json: valid linear speed-density calculator, Speed86.6667 and Flow1733.3333 at defaults. Not the LWR conservation PDE; Traffic_Flow is inert. Label static fundamental diagram calculator.

Metadata for these three now identifies outputs and limitations; tests/test_static_calculators.py checks independent default and changed-input outputs, plus invariant stocks. tests/fixtures/static-calculators-before.json records original complete definitions and hashes.

## Flat equilibrium cases to preserve

- models/economics/cournot-duopoly-competition-eco.json: initial30,30 equal both best responses (100-10-30)/2=30.
- models/economics/cobweb-agricultural-market-eco.json: Price10, Quantity50, ExpectedPrice10 satisfy clearing price(100-50)/5=10 and supply10+4*10=50.
- models/education/bathtub-dynamics-demo-edu.json: initial50 equals faucet5 times drain-time10, so inflow5 equals outflow5.

Flat trajectories alone never justify retirement. Other nonconstant-flow equilibrium cases require individual review.

## Proposed retirements

Approve repeated-failure quarantine using operations/retirement-recheck.json and docs/FAILURE-REGISTER-1.9.md evidence, and constant-zero-flow placeholder retirement with identity/evidence manifest. Exclude the independently assigned reconstructions.

- models/physics/simple-harmonic-oscillator-phy.json: both stocks initialize0 despite Initial Position50; Position also lacks a velocity inflow, so oscillator coupling is absent.
- models/economics/logistic-growth-model-eco.json: Population initializes0 despite unused Initial Population100. Quarantine presentation, but this is repairable initialization, not invalid logistic physics.
- models/economics/lotka-volterra-predator-prey-model-eco.json: Prey/Predators initialize0 despite explicit unused initial1000/20. Likewise repairable initialization rather than invalid equations.
- models/social/remote-work-adoption-soc.json: every worker stock initializes0 and transitions require existing workers. No population initialization parameters supply defensible repair values.
- models/economics/penny-distribution-model-eco.json: runtime app/core/equations.py uses PULSE(magnitude,start_time,repeat_interval=0); model PULSE(Production_Year,1)*Production_Volume fires at year1, outside1930–2014. Verify original dialect before repair.
- models/physics/lorenz-attractor-chaos-phy.json, models/physics/lorenz-chaotic-attractor-weather-phy.json, models/physics/lorenz-strange-attractor-phy.json: redundant same Lorenz ODEs, initial1,1,1, interval0–50/dt0.01, beta2.667. Keep more precise models/physics/lorenz-attractor-phy.json beta2.666666667. Extra radius outputs are diagnostics; strange-attractor Lyapunov Estimate0.9 is a constant, not an estimate. Consolidation is justified by redundancy, not invalid dynamics.

## Other definite defects supporting cull

- models/economics/ricker-stock-recruitment-eco.json: recruitment multiplies alpha*S*e*e*e*(-beta*S), yielding negative recruitment for positive inputs, rather than exp(-beta*S).
- models/finance/garman-kohlhagen-fx-options-fin.json: Forward_Rate=Spot*e*(rd-rf)*T becomes zero at equal rates, rather than Spot. No option valuation; strike and volatility unused.
- models/psychology/fitts-law-motor-control-psy.json: index3.32*distance/width omits logarithm.
- models/psychology/stevens-power-law-psy.json: Constant*Intensity*Intensity*Exponent multiplies by exponent rather than exponentiation.
- models/psychology/weber-fechner-psychophysics-psy.json: linear perceived change omits logarithm and ignores reference intensity. Weber JND relation alone could be salvaged, but not the combined claimed model.
- models/other/erlang-c-call-center-ops.json: Service_Level is literal0.8; no Erlang-C waiting probability or service-level calculation.
- models/economics/clark-optimal-harvesting-eco.json: K/2 and rK/4 are logistic maximum-sustainable-yield quantities, not discounted economic optimum; price, costs, discount rate unused. Possible future MSY calculator salvage.

Hill response models/other/hill-drug-response-pharm.json contains valid fixed-n=2 algebra but n is unused and drug input/elimination are disconnected; default concentration and effect are zero. Could be salvaged later as a fixed-n calculator with explicit inputs, but current cull is acceptable. Airport-capacity-model-tra.json contains a plausible M/M/1 waiting-time calculator but inert named outputs and unused runway capacity make the claimed airport simulation misleading; optional future calculator salvage, not a required keeper.
