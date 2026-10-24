from tests.library_admission import baseline_models
"""Independent equations, invariant domains and discrete references for review candidates."""
import json
import math
from pathlib import Path
from functools import lru_cache
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from app.core.model import Model
from app.core.simulator import simulate
from app.core.units import analyze_units

ROOT=Path(__file__).resolve().parents[1]/'operations/library-candidates-biology'
SLUGS=sorted(p.stem for p in ROOT.glob('*.json') if p.name!='manifest.json')

@lru_cache(None)
def candidate(slug):
    return Model.model_validate_json((ROOT/(slug+'.json')).read_text())

@lru_cache(None)
def trajectory(slug):
    return simulate(candidate(slug))

# Hand-written numerical equations use no authored expression parser or model
# parameter reading. Changes to a fixture must therefore justify reference edits.
def reference(slug):
    if slug.startswith('goodwin-'):
        return lambda t,y: [1/(1+y[2]**10)-.12*y[0],2*y[0]-.08*y[1],4*y[1]-.1*y[2]]
    if slug.startswith('repressilator-'):
        return lambda t,y: [216/(1+y[5]**2)+.216-y[0],216/(1+y[3]**2)+.216-y[1],216/(1+y[4]**2)+.216-y[2],5*(y[0]-y[3]),5*(y[1]-y[4]),5*(y[2]-y[5])]
    if slug.startswith('selkov-'):
        return lambda t,y: [1-y[0]*y[1]**2,.8*(y[0]*y[1]**2-y[1])]
    if slug.startswith('gierer-'):
        return lambda t,y: [y[0]**2/y[1]-y[0],y[0]**2-2*y[1]]
    if slug.startswith('droop-'):
        def rhs(t,y):
            s,q,x=y
            uptake=.5*s/(.5+s)
            growth=1-.1/q
            return [-uptake*x,uptake-growth*q,growth*x]
        return rhs
    if slug.startswith('goldbeter-mitotic-'):
        def rhs(t,y):
            c,m,x=y
            return [.025-.25*x*c/(.02+c)-.01*c,
                    3*c/(.5+c)*(1-m)/(.005+1-m)-1.5*m/(.005+m),
                    m*(1-x)/(.005+1-x)-.5*x/(.005+x)]
        return rhs
    if slug.startswith('goldbeter-koshland-'):
        return lambda t,y: [.1*(1-y[0])/(.01+1-y[0])-.09*y[0]/(.01+y[0])]
    if slug.startswith('schnakenberg-'):
        return lambda t,y: [.1-y[0]+y[0]**2*y[1],.9-y[0]**2*y[1]]
    raise AssertionError('Discrete references are tested separately')

@pytest.mark.parametrize('slug',SLUGS)
def test_candidate_metadata_units_finite_changing_default(slug):
    model=candidate(slug)
    result=trajectory(slug)
    assert model.source.startswith('https://') and model.reference
    assert 'clamp' in model.description.lower() or 'clipp' in model.description.lower()
    assert len(model.flows)==len(model.stocks)>0
    assert analyze_units(model)['status']=='consistent'
    for stock in model.stocks:
        series=np.asarray(result.values[stock.name])
        assert len(series)==len(result.time)
        assert np.isfinite(series).all()
        assert np.ptp(series)>1e-6
        assert series.min()>=-1e-9

CONTINUOUS=[s for s in SLUGS if not s.startswith(('leslie-','nicholson-'))]
@pytest.mark.parametrize('slug',CONTINUOUS)
def test_full_horizon_against_independent_dop853_reference(slug):
    model=candidate(slug); result=trajectory(slug)
    rhs=reference(slug)
    expected=solve_ivp(rhs,(0,model.time_settings.end),[s.initial_value for s in model.stocks],
                       method='DOP853',t_eval=result.time,rtol=2e-11,atol=2e-13)
    assert expected.success
    actual=np.array([result.values[s.name] for s in model.stocks])
    error=np.max(np.abs(actual-expected.y)/(1+np.abs(expected.y)))
    assert error<2e-5,(slug,error)

@pytest.mark.parametrize('slug',['selkov-basic-glycolysis-biology','gierer-meinhardt-well-mixed-biology','schnakenberg-well-mixed-biology','goodwin-feedback-oscillator-biology'])
def test_rk4_timestep_refinement_reduces_reference_error(slug):
    model=candidate(slug); coarse=trajectory(slug)
    settings=model.time_settings.model_copy(update={'dt':model.time_settings.dt/2})
    fine=simulate(model,settings)
    expected=solve_ivp(reference(slug),(0,settings.end),[s.initial_value for s in model.stocks],
                       method='DOP853',t_eval=coarse.time,rtol=2e-11,atol=2e-13).y
    a=np.array([coarse.values[s.name] for s in model.stocks])
    b=np.array([fine.values[s.name][::2] for s in model.stocks])
    coarse_error=np.max(np.abs(a-expected)/(1+np.abs(expected)))
    fine_error=np.max(np.abs(b-expected)/(1+np.abs(expected)))
    assert fine_error<=.2*coarse_error+1e-9


def test_droop_closed_batch_conservation_and_quota_domain():
    values=trajectory('droop-batch-quota-biology').values
    external=np.array(values['External_Nutrient'])
    quota=np.array(values['Quota'])
    biomass=np.array(values['Biomass'])
    assert external+quota*biomass==pytest.approx(np.full(len(external),10.2),abs=2e-7)
    assert quota.min()>=.1-1e-10
    assert biomass[-1]==pytest.approx(102,abs=1e-5)


def test_mitotic_fractions_invariant_without_clipping_and_repeated_cycles():
    from scipy.signal import find_peaks
    values=trajectory('goldbeter-mitotic-cascade-biology').values
    for name in ['Active_Kinase','Active_Protease']:
        assert min(values[name])>=0
        assert max(values[name])<=1
    peaks,_=find_peaks(values['Cyclin'],prominence=.1)
    assert len(peaks)>=2


def test_gierer_and_selkov_analytical_steady_states():
    for slug,target in [('gierer-meinhardt-well-mixed-biology',[2,2]),('selkov-basic-glycolysis-biology',[1,1])]:
        assert reference(slug)(0,target)==pytest.approx([0,0],abs=1e-12)
        result=trajectory(slug)
        final=[result.values[s.name][-1] for s in candidate(slug).stocks]
        assert np.linalg.norm(np.array(final)-target)<.005


def test_covalent_switch_stationary_solution_and_ultrasensitivity():
    slug='goldbeter-koshland-dynamic-switch-biology'
    root=brentq(lambda x:reference(slug)(0,[x])[0],0,1)
    assert trajectory(slug).values['Modified_Fraction'][-1]==pytest.approx(root,abs=1e-5)
    def steady(forward):
        return brentq(lambda x:forward*(1-x)/(.01+1-x)-.09*x/(.01+x),0,1)
    # A twenty-percent capacity increase produces much larger fraction change.
    assert steady(.1)-steady(.08)>.7


def test_leslie_all_censuses_against_independent_matrix_powers():
    slug='leslie-three-age-classes-biology'
    matrix=np.array([[0,1.2,.8],[.5,0,0],[0,.7,0]])
    result=trajectory(slug)
    for n in range(21):
        expected=np.linalg.matrix_power(matrix,n)@np.array([100,40,10])
        actual=[result.values[s.name][n] for s in candidate(slug).stocks]
        assert actual==pytest.approx(expected,rel=2e-13,abs=2e-12)
    assert candidate(slug).time_settings.discrete_period==1


def test_nicholson_bailey_exact_recurrence_and_unstable_equilibrium():
    slug='nicholson-bailey-parasitoids-biology'
    result=trajectory(slug)
    h,p=140.,70.
    for n in range(21):
        assert [result.values['Hosts'][n],result.values['Parasitoids'][n]]==pytest.approx([h,p],rel=2e-13)
        escaped=math.exp(-.01*p)
        h,p=2*h*escaped,h*(1-escaped)
    equilibrium=np.array([200*math.log(2),100*math.log(2)])
    # Linearization of the actual recurrence has spectral radius sqrt(2log2)>1.
    assert math.sqrt(2*math.log(2))>1
    initial=np.linalg.norm(np.array([140,70])-equilibrium)
    final=np.linalg.norm(np.array([result.values['Hosts'][-1],result.values['Parasitoids'][-1]])-equilibrium)
    assert final>5*initial


def test_candidates_are_review_only_and_not_repeated_active_definitions():
    repo=ROOT.parents[1]
    active=baseline_models(repo, {candidate(slug).id for slug in SLUGS})
    existing_ids={m.get('id') for m in active}
    existing_names={m.get('name') for m in active}
    assert len(SLUGS)==10
    for slug in SLUGS:
        assert candidate(slug).id not in existing_ids
        assert candidate(slug).name not in existing_names
    manifest=json.loads((ROOT/'manifest.json').read_text())
    assert len(manifest)==10
    assert all(entry['parameter_provenance'] and entry['license'] for entry in manifest)
