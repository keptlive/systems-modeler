"""Independent mathematics for five explicitly uncalibrated reconstructions."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import solve_ivp
from app.core.model import Model
from app.core.simulator import simulate

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/reconstruction-202610"
RECEIPT = json.loads((FIXTURES / "SHA256.json").read_text())


def load(path):
    return Model.model_validate_json((ROOT / path).read_text())


def run(path, divisor=1):
    model = load(path)
    model.time_settings.dt /= divisor
    return simulate(model)


@pytest.mark.parametrize("path", RECEIPT)
def test_default_full_horizon_finite_and_existing_canvas_preserved(path):
    original_bytes = (FIXTURES / Path(path).name).read_bytes()
    assert hashlib.sha256(original_bytes).hexdigest() == RECEIPT[path]
    original = json.loads(original_bytes)
    current = json.loads((ROOT / path).read_text())
    for key in ("id", "name", "stocks", "variables", "connectors", "created_at", "updated_at"):
        assert current[key] == original[key]
    for key in ("start", "end", "dt"):
        assert current["time_settings"][key] == original["time_settings"][key]
    result = run(path)
    assert result.time[-1] == pytest.approx(original["time_settings"]["end"])
    assert len(result.time) == round((original["time_settings"]["end"]-original["time_settings"]["start"])/original["time_settings"]["dt"])+1
    assert all(math.isfinite(value) for series in result.values.values() for value in series)
    assert any(max(result.values[s["name"]])-min(result.values[s["name"]]) > 1e-3 for s in original["stocks"])


def test_levins_full_trajectory_against_logistic_closed_form():
    result = run("models/economics/levins-metapopulation-eco.json")
    # p'= (c-e)p-cp^2, K=1-e/c; p(0)=0.3=K/2.
    exact = .6/(1+np.exp(-.3*np.asarray(result.time)))
    np.testing.assert_allclose(result.values["Occupied_Patches"], exact, atol=3e-10, rtol=0)
    assert all(0 <= p <= 1 for p in result.values["Occupied_Patches"])


def test_bolus_full_trajectory_against_exponential_solution():
    result = run("models/other/one-compartment-kinetics-pharm.json")
    exact = 100*np.exp(-.1*np.asarray(result.time))
    np.testing.assert_allclose(result.values["Drug_Amount"], exact, atol=4e-9, rtol=0)
    np.testing.assert_allclose(result.values["Concentration"], exact/5, atol=8e-10, rtol=0)


def test_oscillator_closed_form_and_dissipating_energy():
    result = run("models/engineering/mass-spring-damper-eng.json")
    t=np.asarray(result.time); a=.25; w=math.sqrt(10-a*a)
    exact=np.exp(-a*t)*(np.cos(w*t)+a/w*np.sin(w*t))
    np.testing.assert_allclose(result.values["Displacement"], exact, atol=4e-8, rtol=0)
    v=np.asarray(result.values["Velocity"]); x=np.asarray(result.values["Displacement"])
    energy=.5*v*v+5*x*x
    assert np.max(np.diff(energy)) <= 1e-10
    assert np.min(x) < 0  # signed flows must permit physical oscillation


@pytest.mark.parametrize("key", ["monod-bacterial-growth-bio", "chemostat-continuous-culture-bio"])
def test_microbiology_mass_balance_independent_solver_and_refinement(key):
    path=f"models/biology/{key}.json"
    results=[run(path, n) for n in (1,2)]
    batch=key.startswith("monod")
    # Independent handwritten ODE, no evaluator/model-expression reuse.
    def rhs(t,z):
        x,s=z
        if batch:
            growth=.5*s/(10+s)*x
            return [growth,-growth/.4]
        growth=.6*s/(1+s)*x
        return [growth-.3*x,.3*(10-s)-growth/.5]
    oracle=solve_ivp(rhs, (0,results[0].time[-1]), [.1,100] if batch else [.5,5],
                     method="DOP853", rtol=2e-12, atol=1e-13, dense_output=True)
    assert oracle.success
    errors=[]
    for result in results:
        x=np.asarray(result.values["Biomass"]); s=np.asarray(result.values["Substrate"])
        t=np.asarray(result.time)
        assert np.min(x)>=0 and np.min(s)>=0
        total=s+x/(.4 if batch else .5)
        expected=np.full_like(t,100.25) if batch else 10-4*np.exp(-.3*t)
        np.testing.assert_allclose(total,expected,atol=2e-8,rtol=0)
        errors.append(np.max(np.abs(np.array([x,s])-oracle.sol(t))))
    assert errors[0]<(5e-4 if batch else 3e-5)
    assert errors[1]<errors[0]/10  # fourth-order refinement across the full horizon
