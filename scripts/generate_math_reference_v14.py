"""Regenerate independent ODE evidence, without importing the application engine.

Run from the repository with Python, numpy and scipy (reference: SciPy 1.18.1).
The constants below reproduce the educational definitions, not fitted source
data. See docs/MATH-SOURCE-REPAIRS-1.4.md for source and assumption boundaries.
"""
from pathlib import Path
import json
import numpy as np
import scipy
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]


def sir(t, y):
    s, i, r = y
    incidence, recovery = .4*s*i/1000, .1*i
    return [-incidence, incidence-recovery, recovery]


def vaccination(t, y):
    s, i, r, v = y
    n = sum(y)
    incidence, recovery, vaccination_rate = .5*s*i/n, .1*i, .01*.9*s
    return [-incidence-vaccination_rate+.0001*n,
            incidence-recovery, recovery, vaccination_rate]


def seir(t, y):
    s, e, i, r = y
    incidence, progression, recovery = .5*s*i/100000, e/5, i/7
    return [-incidence, incidence-progression, progression-recovery, recovery]


CASES = [
    ('kermack-mckendrick-epidemic-epi', sir, [999, 1, 0],
     ['Susceptible', 'Infected', 'Recovered'], 160, .1),
    ('anderson-may-herd-immunity-epi', vaccination, [100000, 100, 0, 0],
     ['Susceptible', 'Infected', 'Recovered', 'Vaccinated'], 365, 1),
    ('seir-epidemic-model-epi', seir, [99990, 10, 0, 0],
     ['Susceptible', 'Exposed', 'Infectious', 'Recovered'], 200, .0625),
]


def generate():
    cases = {}
    for name, rhs, initial, names, end, dt in CASES:
        times = np.linspace(0, end, 33)
        default_times = np.linspace(0, end, round(end/dt)+1)
        sol = solve_ivp(rhs, (0, end), initial, method='DOP853',
                        rtol=2e-13, atol=2e-12, dense_output=True)
        if not sol.success:
            raise RuntimeError(sol.message)
        sampled, defaults = sol.sol(times), sol.sol(default_times)
        cases[name] = {
            'time': times.tolist(),
            'values': {n: sampled[k].tolist() for k, n in enumerate(names)},
            'default_time': default_times.tolist(),
            'default_values': {n: defaults[k].tolist() for k, n in enumerate(names)},
            'initial': initial, 'reference_nfev': sol.nfev,
        }
    out = {
        'generator': 'scripts/generate_math_reference_v14.py; independent explicit '
                     f'ODEs, SciPy {scipy.__version__} DOP853 rtol=2e-13 atol=2e-12; '
                     'no application imports or equation evaluator',
        'scope': 'Numerical references for illustrative assumptions; not empirical validation',
        'cases': cases,
    }
    (ROOT/'tests/fixtures/math-models-v14.json').write_text(json.dumps(out, indent=2)+'\n')


if __name__ == '__main__':
    generate()
