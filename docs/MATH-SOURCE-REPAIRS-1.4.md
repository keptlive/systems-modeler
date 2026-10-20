# Mathematical reconstruction review 1.4

Four educational examples now have explicit input repairs and independent numerical checks. These checks establish consistency with stated equations, not empirical validity, calibration or exact reproduction of a cited paper. Field-level changes and original/replacement SHA256 hashes are in `operations/math-source-repairs-v14.json`. Model IDs, layouts and unrelated inputs are preserved.

## Sources and reconstruction boundaries

- **Kermack–McKendrick:** the [1927 paper](https://pdodds.w3.uvm.edu/files/papers/others/1927/kermack1927a.pdf), printed p.713 equation 29, gives the constant-rate SIR special case. Here its mass-action coefficient is beta/N and its removal coefficient gamma. The existing beta=.4, gamma=.1 and initial (999,1,0) are illustrative. Two diagnostics incorrectly referenced undeclared `R0`; they now reference the existing reproduction-number element exactly. No differential equation or initial value changed.
- **Anderson–May:** [the 1985 paper](https://indico.ictp.it/event/a02113/contribution/42/material/0/0.pdf), printed pp.324–325, discusses herd immunity and age heterogeneity. This local homogeneous model is a different educational simplification: beta=.5, gamma=.1, vaccination=.01*.9*S, births=.0001*N, no mortality, initial (100000,100,0,0). It is not the paper's age-structured model or a vaccination recommendation. Two diagnostics now reference the existing `Basic R0` element exactly. The population balance is N(t)=100100*exp(.0001*t), not a constant population.
- **SEIR:** [Hethcote's 2000 review](https://www.maths.usyd.edu.au/u/marym/populations/hethcote.pdf) describes the compartment interpretation and reproduction numbers. The former DOI identified a different van den Driessche–Watmough paper; the source now matches the named review, DOI10.1137/S0036144500371907. The missing initial equations now use the already supplied Total Population=100000 and Initial Exposed=10: S=N-E0, E=E0, I=R=0. beta=.5, latent period5 and infectious period7 remain illustrative. The diagnostic now references the actual R0 element. No claim of WHO data or a paper-specific parameterization remains.
- **Solow–Swan:** [Solow 1956](https://www.depfe.unam.mx/doctorado/teorias-crecimiento-desarrollo/solow_1956.pdf), printed pp.66–67 and76, provides the production/accumulation and labor-growth framework. This educational Cobb–Douglas example includes explicit depreciation. Broken short aliases now reference the existing capital, labor, productivity and share elements exactly. Initial equations use existing Initial Capital=100 and Initial Labor=100. s=.2, A=1, alpha=.33, delta=.05 and n=.02 were preserved. No empirical parameter provenance is claimed.

## Numerical findings

Checking only an epidemic's final state hid substantial errors during its peak. The former daily Euler vaccination default had a maximum absolute stock error of **15.6227% of initial population** against an independently coded DOP853 solution over every default output time. Halving the step still left 8.1476%. This was a numerical discretization issue under the existing illustrative equations.

All three repaired epidemic examples now explicitly select RK4 while preserving their time grids and coefficients. Maximum full-trajectory errors, normalized by initial population, are:

| Example | Previous Euler | Explicit RK4 | RK4 with half step |
| --- | ---: | ---: | ---: |
| SIR, dt=.1 | .0164404 | 6.04e-9 | 3.82e-10 |
| Vaccination, dt=1 | .1562274 | 9.96e-5 | 7.20e-6 |
| SEIR, dt=.0625 | .0087461 | 1.04e-10 | 6.50e-12 |

The tests bound the complete default trajectory, assert time alignment, positivity and refinement improvement, and compare 33 uniformly spaced reference times against a refined RK4 run. Population conservation is checked at every refined step for closed SIR/SEIR; exponential population growth is checked for vaccination. The SIR invariant S+I-(gamma*N/beta)*log(S) and reproduction diagnostics are also checked.

For Solow, with k=K/L, b=1-alpha and q=delta+n, the closed form is
`k(t)=[s*A/q + (k(0)^b-s*A/q)*exp(-b*q*t)]^(1/b)` and `L(t)=L0*exp(n*t)`.
Tests check all1,601 points of K, L and output for two distinct initial/parameter scenarios. SEIR initialization is additionally tested after changing Initial Exposed to20.

## Reproduction

`scripts/generate_math_reference_v14.py` contains explicit independent ODEs, stock ordering, parameters and grids. It imports no application code or equation evaluator. SciPy1.18.1 DOP853 with rtol2e-13 and atol2e-12 generated `tests/fixtures/math-models-v14.json`; numpy/SciPy are needed only to regenerate this fixture. The ordinary tests consume it offline. Run `python -m pytest tests/test_math_sources_v14.py`.

The source PDFs remain external; URLs, byte counts and SHA256 fingerprints are in the receipt. Source identity, equation fidelity, dimensions, numerical accuracy and empirical applicability remain separate review questions. This review addresses only the stated subset.
