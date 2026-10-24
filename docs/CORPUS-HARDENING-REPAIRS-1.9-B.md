# Five explicit-integration defaults after the Radau guard review

The five saved defaults rejected by the new adaptive guard now use explicit
RK4. Every stock initializer, parameter, flow, auxiliary, lookup point, ID,
connector and geometry is preserved. The full requested horizons are unchanged.
The numerical-method change addresses unsupported adaptive behavior without
removing its guard or inventing a continuous replacement for a jump.

The receipt [corpus-hardening-repairs-v19-b.json](../operations/corpus-hardening-repairs-v19-b.json)
contains exact before text and SHA-256 from `cc010ae`, current SHA-256, all changed
fields, source evidence, causal chains, independent references and error arrays.
Tests use those portable bytes and literal source data, with no private Git
history dependency. Descriptions identify numerical adaptations and scientific
limits. Milgram also receives a corrected source DOI and an explicitly
illustrative title.

| Model | Original Radau rejection | RK4 default / half / quarter DT | Maximum normalized stock error at the three grids |
| --- | --- | --- | --- |
| Grid frequency | Reserve deadband has unequal branch limits | .04 / .02 / .01 seconds, full 60 s | Reserve: 9.18e-8 / 6.65e-8 / 3.37e-8; frequency and energy near 1e-14 |
| Traffic flow dynamics | Queue dissipation coefficient jumps at density 50 | .02 / .01 / .005, full 48 | Density: .009666 / .0003858 / .00001942 |
| Logistic network reach, Milgram context | Threshold counter jumps at half population | .0025 / .00125 / .000625, full 10 | Population: 8.02e-6 / 5.27e-7 / 3.38e-8 |
| Greenshields traffic | Queue growth jumps at density 120 | .02 / .01 / .005, full 24 | Density: .0004440 / .00002065 / .000001104 |
| WORLD2 | State-driven lookup features can be missed by adaptive steps | .5 / .25 / .125 years, full 1900–2100 | Worst of five stocks: 4.33e-6 / 9.32e-7 / 4.20e-7 |

Errors are maximum absolute trajectory errors divided by the maximum magnitude
of the independent stock reference, using scale at least 1. A finite result alone
was not accepted. All three grids are checked for full-horizon completion,
finite output, nonnegative stocks, domain conditions, retained-value limits and
the existing million-work-unit limit. Finest grids use at most 880,011 work units;
the largest retained-value count is 176,011. No capacity limits were raised.

## Physical and source checks

The grid reference independently eliminates one ODE using
`E=5000*(f/60)^2`, solves the resulting scalar swing equation, locates each
frequency deadband crossing by a bracketed root, and integrates the reserve
equation separately on every event interval. RK4 retains the physical invariant
to absolute energy error below 2e-9. Its small reserve error is measured against
explicit event localization, not against a second unsplit adaptive solve.
The larger .04 default permits two full refinements inside the engine budget;
the old .01 RK4 grid would already consume 780,026 work units before refinement.
The physical mapping remains [NREL/CP-5D00-73872](https://docs.nlr.gov/docs/fy20osti/73872.pdf),
printed p.4/PDF p.7 equation (12). Governor and reserve closures remain local
illustrative assumptions.

Traffic dynamics uses an independently handwritten three-state RHS. At density
0 its derivative is at least 30; at density 20 its derivative is at most
`70-1040<0`. Thus the original default's density interval [0,20] excludes the
queue threshold 50. The unchanged queue equation has the exact zero solution
from its zero initial condition. This is a reachable-domain argument, not a
fabricated constant trajectory. Density plus cumulative throughput agrees with
the analytically integrated external inflow to absolute error below 2e-8.
The default's largest density error is about 0.97% during the fast initial
transient, falling below 0.002% at quarter DT. The linear relaxation rate is about
60 per model time unit, explaining why the old .25 grid cannot simply be reused
with an explicit method. [Lighthill and Whitham (1955), Part II](https://doi.org/10.1098/rspa.1955.0089)
remains conceptual background; this local model is not a native LWR PDE
discretization, and its road-length/unit interpretation is not calibrated.

Greenshields uses an independent two-state RHS and the mathematical capacity
`60*150/4=2250`. Arrival is in [1000,2000]; at density 0 the derivative is positive,
and at density 50 the departure flow is 2000. Hence [0,50] is invariant, below the
unchanged queue trigger 120, and its zero queue is again the exact default
solution. The source's straight speed-density relation is on printed pp.468–469,
equation (1) and Figure 5 of [Greenshields (1935)](https://onlinepubs.trb.org/Onlinepubs/hrbproceedings/14/14P1-023.pdf).
The original study does not provide the saved sinusoidal arrival or queue ODE;
those remain explicitly illustrative. Changed scenarios may leave this verified
domain or reveal shortcomings in the queue closure.

Milgram's saved logistic equation has the independent exact solution
`P(t)=K/(1+(K-1)*exp(-50*t))`, `K=300000000`, and half-population hitting time
`log(K-1)/50`. The legacy Chain_Steps stock is a continuous elapsed-duration
counter, whose reference is `min(t,hit)`. Its absolute errors are approximately
3.09e-5, 1.78e-4 and 1.35e-4: all below half their respective DT, but nonmonotone
because the threshold falls at different step phases. Only the smooth population
is claimed to show fourth-order refinement. Population stays in (0,K], and all
logarithm arguments remain positive. This generated ODE does not reproduce an
acquaintance-chain experiment. Primary Crossref DOI registration additionally
establishes that the old DOI referred to Mills/Zytowski's unrelated *Helping
relationship: A structural analysis*. The corrected [Milgram DOI](https://doi.org/10.1037/e400002009-005)
registers *The small-world problem* (1967); it supplies conceptual context, not
the local logistic algorithm.

WORLD2 retains all 22 source table curves and the five source balances from
Forrester's [1970 D-1354 documentor](https://dome.mit.edu/bitstream/handle/1721.3/189645/39080024064039.pdf?isAllowed=y&sequence=1),
MIT PDF pp.82–91, equations 1–43. The source population listing explicitly uses
the DYNAMO Euler level update. RK4 is therefore described as a modern numerical
integration of those continuous equations, rather than exact native-DYNAMO
replay. The independent reference uses handwritten balances and 22 separately
transcribed literal curves, DOP853 with maximum step .025 years and tight
tolerances. Every table point is compared against those source literals.
Population/capital/resources/pollution remain positive, resources decline,
food and absorption denominators remain positive, and agricultural fraction
stays strictly between 0 and 1. Empirical validity beyond this historical
scenario is not claimed.

## Validation

`tests/test_corpus_hardening_v19_b.py` checks receipt integrity, all three full
grids against independent references, physical/accounting invariants and domain
conditions. Simulation completion and source-faithfulness remain separate claims:
these repairs make the saved default experiments reviewable under supported
numerical methods; they do not certify arbitrary inputs or turn illustrative
closures into native source models.
