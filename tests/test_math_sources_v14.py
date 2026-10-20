"""Independent math checks for explicitly reconstructed educational models."""
import json
import math
from pathlib import Path
import pytest
from app.core.model import Model, TimeSettings
from app.core.simulator import simulate

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = json.loads((ROOT / 'tests/fixtures/math-models-v14.json').read_text())

def load(name):
    path, = list((ROOT / 'models').rglob(name + '.json'))
    return Model.model_validate_json(path.read_text())

@pytest.mark.parametrize('name', list(REFERENCE['cases']))
def test_compartment_trajectories_against_independent_dop853(name):
    model = load(name); expected = REFERENCE['cases'][name]
    # Reference times align to 32 equal intervals. Resolve each interval with
    # at least 64 RK4 steps, preserving the complete original horizon.
    ts = TimeSettings(**{**model.time_settings.model_dump(), 'integration_method':'rk4',
        'dt': (model.time_settings.end - model.time_settings.start) / 4096})
    result = simulate(model, ts)
    for k, time in enumerate(expected['time']):
        assert result.time[k * 128] == pytest.approx(time, abs=1e-10)
    for stock, values in expected['values'].items():
        for k, value in enumerate(values):
            assert result.values[stock][k * 128] == pytest.approx(value, rel=3e-7, abs=3e-5)
        assert min(result.values[stock]) >= -1e-8
    total = [sum(result.values[s.name][k] for s in model.stocks) for k in range(len(result.time))]
    initial = total[0]
    for t, value in zip(result.time,total):
        target = initial * math.exp(.0001 * t) if name.startswith('anderson') else initial
        assert value == pytest.approx(target, rel=2e-12)

@pytest.mark.parametrize('name', list(REFERENCE['cases']))
def test_defaults_are_positive_and_improve_under_refinement(name):
    model=load(name)
    default=simulate(model)
    assert all(min(default.values[s.name]) >= -1e-8 for s in model.stocks)
    fine=simulate(model,TimeSettings(**{**model.time_settings.model_dump(),'dt':model.time_settings.dt/2}))
    expected=REFERENCE['cases'][name]['values']
    reference=REFERENCE['cases'][name]
    assert default.time == pytest.approx(reference['default_time'], abs=1e-10)
    assert fine.time[::2] == pytest.approx(reference['default_time'], abs=1e-10)
    population=sum(reference['initial'])
    coarse_trajectory=max(abs(x-y) for s,values in reference['default_values'].items()
                          for x,y in zip(default.values[s],values))/population
    fine_trajectory=max(abs(x-y) for s,values in reference['default_values'].items()
                        for x,y in zip(fine.values[s][::2],values))/population
    # Bound full-trajectory errors as fractions of the initial population,
    # including epidemic peaks; this is numerical, not empirical accuracy.
    bounds={'kermack-mckendrick-epidemic-epi':1e-7,
            'anderson-may-herd-immunity-epi':1.1e-4,
            'seir-epidemic-model-epi':1e-8}
    assert model.time_settings.integration_method == 'rk4'
    assert coarse_trajectory < bounds[name]
    assert fine_trajectory < .6*coarse_trajectory
    # Compare the final state to an independent solver; finite alone is insufficient.
    coarse_error=max(abs(default.values[s][-1]-v[-1]) for s,v in expected.items())
    fine_error=max(abs(fine.values[s][-1]-v[-1]) for s,v in expected.items())
    assert fine_error < coarse_error

def test_sir_invariant_and_reproduction_diagnostics():
    model=load('kermack-mckendrick-epidemic-epi')
    r=simulate(model,TimeSettings(start=0,end=160,dt=.05,integration_method='rk4'))
    invariant=1000-250*math.log(999)
    for s,i,reff in zip(r.values['Susceptible'],r.values['Infected'],r.values['Effective Reproduction Number']):
        assert s+i-250*math.log(s) == pytest.approx(invariant,abs=1e-7)
        assert reff == pytest.approx(4*s/1000)
    assert set(r.values['Herd Immunity Threshold']) == {.75}

@pytest.mark.parametrize('capital,labor,saving',[(100,100,.2),(50,120,.3)])
def test_solow_entire_trajectory_against_closed_form(capital,labor,saving):
    model=load('solow-swan-growth-model-eco')
    for v in model.variables:
        if v.name=='Initial Capital':v.equation=str(capital)
        if v.name=='Initial Labor':v.equation=str(labor)
        if v.name=='Savings Rate':v.equation=str(saving)
    r=simulate(model,TimeSettings(start=0,end=200,dt=.125,integration_method='rk4'))
    a=.33;b=1-a;steady=saving/.07
    for idx,t in enumerate(r.time):
        lab=labor*math.exp(.02*t)
        perworker=(steady+((capital/labor)**b-steady)*math.exp(-b*.07*t))**(1/b)
        cap=perworker*lab
        assert r.values['Labor Force'][idx] == pytest.approx(lab,rel=2e-11)
        assert r.values['Capital Stock'][idx] == pytest.approx(cap,rel=2e-9)
        assert r.values['Output'][idx] == pytest.approx(cap**a*lab**b,rel=2e-9)
    assert r.values['Steady State Capital per Worker'][-1] == pytest.approx(steady**(1/b))

def test_solow_default_and_seir_initial_parameters_are_used():
    solow=simulate(load('solow-swan-growth-model-eco'))
    assert solow.values['Capital Stock'][0] == 100
    assert solow.values['Labor Force'][0] == 100
    model=load('seir-epidemic-model-epi')
    for v in model.variables:
        if v.name=='Initial Exposed':v.equation='20'
    r=simulate(model)
    assert r.values['Susceptible'][0] == 99980
    assert r.values['Exposed'][0] == 20
    assert r.values['Infectious'][0] == 0
    assert sum(r.values[s.name][0] for s in model.stocks) == 100000
