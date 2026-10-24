from tests.model_history import model_path, find_model_path
"""Portable v1.9 partition B source, independent mathematics and domain checks."""
import hashlib
import json
import math
import re
from collections import deque
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.linalg import expm
from tests.model_history import pre_hardening_v19_bytes
from app.core.model import Model
from app.core.simulator import simulate
from app.core.integration import evaluate
from app.core.equations import EquationError

ROOT=Path(__file__).resolve().parents[1]
FIX=ROOT/'tests/fixtures/corpus-v19-b'


def load(slug,category='economics'):
    return Model.model_validate_json(model_path(ROOT,f'models/{category}/{slug}.json').read_text())


@lru_cache(None)
def run(slug,category='economics'):
    model=load(slug,category)
    return model,simulate(model)


def market_rhs(t,y):
    share,customers,brand,experience=y
    total=1e6*1.05**t
    price=130*(experience/1e6)**(-.15)
    quality=1000100
    attraction=110/price*(quality/100)*(brand/100)
    gain=.1*attraction
    loss=.1/attraction
    return [(1-share)*gain-share*loss,.05*total*share-customers*(.05+loss),
            5+quality/price*100*.005-.1*brand,2*customers]


def labor_rhs(t,y):
    employed,unemployed,outside,vacancies,wage,longterm=y
    force=employed+unemployed
    population=force+outside
    tight=vacancies/unemployed
    matching=.5*math.sqrt(unemployed)*math.sqrt(vacancies)
    fraction=longterm/unemployed
    hires=matching*(1-fraction)
    separations=employed*.15*(1-.5*(tight-1))
    creation=(employed*.04*(1+.2*(tight-1))-vacancies+hires+.5*vacancies)/.25
    entry=outside*.08*(1+.3*(tight-1))
    exit=unemployed*.05*(1+2*max(0,unemployed/force-.05))
    retired=.025*employed
    growth=.005*population
    aging=.02*outside
    pressure=.3*(tight-1)+.01
    wage_change=wage*pressure*.5*(1 if pressure>0 else .3)
    return [hires-separations-retired,separations+entry-hires-exit,
            exit+retired+growth-entry-aging,creation-hires-.5*vacancies,
            wage_change,2*(unemployed-longterm)-matching*fraction*.5-.15*longterm]


def grid_rhs(t,y):
    frequency,energy,reserve=y
    deviation=60-frequency
    imbalance=5*deviation-50*math.sin(.1*t)
    deployment=reserve*.05*deviation/60 if abs(deviation)>.02 else 0
    return [imbalance*frequency/(2*energy),imbalance,(1000-reserve)/30-deployment]


def test_market_stiffness_repair_against_independent_implicit_math():
    model,result=run('market-share-competition-model-eco')
    assert model.time_settings.integration_method=='radau'
    ts=model.time_settings
    reference=solve_ivp(market_rhs,(0,ts.end),[.5,5e5,100,1e6],method='Radau',
                        rtol=1e-11,atol=1e-11,t_eval=result.time)
    assert reference.success and reference.t[-1]==ts.end
    actual=np.array([result.values[s.name] for s in model.stocks])
    np.testing.assert_allclose(actual,reference.y,rtol=3e-7,atol=5e-4)
    assert actual.min()>=0
    assert actual[0].max()<=1+1e-9
    assert np.all(actual[1]<=1e6*1.05**np.array(result.time))
    # At both share boundaries the continuous vector field points inward.
    assert market_rhs(0,[0,5e5,100,1e6])[0]>0
    assert market_rhs(0,[1,5e5,100,1e6])[0]<0
    for divisor in (2,4):
        refined=model.model_copy(deep=True)
        refined.time_settings.dt/=divisor
        rerun=simulate(refined)
        for stock in model.stocks:
            np.testing.assert_allclose(rerun.values[stock.name][::divisor],result.values[stock.name],rtol=1e-10,atol=1e-7)


def test_labor_initial_inputs_cohorts_and_independent_rhs():
    model,result=run('labor-market-dynamics-model-eco')
    initial=np.array([152e6,8e6,40e6,5.6e6,60000,0])
    assert [result.values[s.name][0] for s in model.stocks]==pytest.approx(initial)
    states=np.array([result.values[s.name] for s in model.stocks])
    assert np.all(states>=0)
    assert np.all(states[5]<=states[1])
    # Independently derived demographic balance cancels every internal transfer.
    for j in (0,100,400,800):
        derivative=np.array(labor_rhs(result.time[j],states[:,j]))
        assert derivative[:3].sum()==pytest.approx(.005*states[:3,j].sum()-.02*states[2,j])
        values=evaluate(model,dict(zip([s.name for s in model.stocks],states[:,j])),result.time[j],model.time_settings.dt,{}, {})
        rhs=np.zeros(6)
        index={s.id:i for i,s in enumerate(model.stocks)}
        for flow in model.flows:
            if flow.from_stock:rhs[index[flow.from_stock]]-=values[flow.name]
            if flow.to_stock:rhs[index[flow.to_stock]]+=values[flow.name]
        np.testing.assert_allclose(rhs,derivative,rtol=1e-12,atol=1e-7)
    reference=solve_ivp(labor_rhs,(0,50),initial,method='Radau',rtol=1e-10,atol=1e-7,t_eval=result.time)
    assert reference.success and np.all(reference.y>=0)
    assert np.all(reference.y[5]<=reference.y[1])
    errors=[]
    for divisor in (1,2,4):
        modified=model.model_copy(deep=True);modified.time_settings.dt/=divisor
        got=simulate(modified)
        array=np.array([got.values[s.name][::divisor] for s in model.stocks])
        assert array.min()>=0 and np.all(array[5]<=array[1])
        errors.append(np.max(np.abs(array-reference.y)/(np.abs(reference.y)+1e5)))
    assert errors[1]<errors[0]*.55 and errors[2]<errors[1]*.55


def population_matrix():
    matrix=np.zeros((9,9))
    matrix[0,0]=.1;matrix[0,8]=-1
    matrix[1,0]=.1*8/70;matrix[1,1]=-8/70
    for i in range(2,9):matrix[i,i-1]=8/70;matrix[i,i]=-8/70
    return matrix


def test_massachusetts351_native_source_complete_and_member_mapping():
    source=(FIX/'massachusetts351-original.mdl').read_text()
    mapping=json.loads((FIX/'massachusetts351-mapping.json').read_text())
    assert hashlib.sha256((FIX/'massachusetts351-original.mdl').read_bytes()).hexdigest()==mapping['source_sha256']
    population_text=re.search(r'Initial Population\[Towns\]=(.*?)~',source,re.S)[1]
    towns_text=re.search(r'\nTowns:(.*?)~',source,re.S)[1]
    clean=lambda text:text.replace('\\','').replace('\n','').replace('\t','')
    values=[int(x) for x in clean(population_text).split(',')]
    towns=[x.strip() for x in clean(towns_text).split(',')]
    assert len(values)==len(towns)==351
    assert dict(zip(towns,values))==mapping['towns']
    assert sum(values)==mapping['total']==6547695
    assert mapping['towns']['Boston']==617660
    assert mapping['towns']['Yarmouth']==23793
    model,result=run('subscripted-population-model-massachusetts-towns-eco')
    assert len(result.values)==357
    assert result.time==list(range(21))
    matrix=population_matrix()
    state=np.array([1,*([1/70]*8)])
    expected=[state.copy()]
    for _ in range(20):
        state=state+matrix@state
        expected.append(state.copy())
    expected=np.array(expected)
    for town,initial in mapping['towns'].items():
        np.testing.assert_allclose(result.values[f'Population[{town}]'],initial*expected[:,0],rtol=1e-13,atol=1e-8)
    all_towns=np.array([result.values[f'Population[{town}]'] for town in towns])
    np.testing.assert_allclose(all_towns.sum(axis=0),result.values['Population'],rtol=1e-14)
    assert all_towns.min()>0
    # Exact matrix exponential is independent of the model parser and integrator.
    exact=np.array([(expm(matrix*t)@expected[0])[0] for t in range(21)])
    errors=[]
    for divisor in (1,2,4):
        modified=model.model_copy(deep=True);modified.time_settings.dt/=divisor
        got=simulate(modified)
        numerical=np.array(got.values['Population'][::divisor])/mapping['total']
        errors.append(np.max(np.abs(numerical-exact)))
    assert errors[1]<errors[0]*.55 and errors[2]<errors[1]*.55


def test_grid_energy_frequency_identity_and_convergence():
    model,result=run('grid-frequency-stability-ene','energy')
    historical=Model.model_validate_json(pre_hardening_v19_bytes(ROOT, 'models/energy/grid-frequency-stability-ene.json'))
    assert historical.time_settings.integration_method=='radau'
    # The new event guard requires explicit RK4; retain all original accuracy checks.
    assert model.time_settings.integration_method=='rk4'
    assert result.time[-1]==60
    assert result.values['Stored Kinetic Energy'][0]==5000
    reference=solve_ivp(grid_rhs,(0,60),[60,5000,500],method='DOP853',rtol=1e-12,atol=1e-10,t_eval=result.time,max_step=.02)
    assert reference.success
    errors=[]
    for divisor in (1,2,4):
        modified=model.model_copy(deep=True);modified.time_settings.dt/=divisor
        got=simulate(modified)
        values=np.array([got.values[s.name] for s in model.stocks])
        assert values.min()>0
        invariant=values[1]-5000*(values[0]/60)**2
        assert np.max(np.abs(invariant))<5e-7
        sample=values[:,::divisor]
        # Deadband discontinuities affect only the illustrative reserve equation.
        np.testing.assert_allclose(sample[:2],reference.y[:2],rtol=1e-9,atol=1e-6)
        errors.append(np.max(np.abs(sample[2]-reference.y[2])))
    assert max(errors)<.01


def test_discrete_growth_exact_native_ar1_recurrence_and_accounting():
    model,result=run('real-business-cycle-basic-eco')
    assert model.time_settings.discrete_period==1
    assert result.time[-1]==200
    capital=100.;technology=1.;output=0.;consumption=0.
    for i,t in enumerate(result.time):
        assert result.values['Capital'][i]==pytest.approx(capital,rel=1e-12)
        assert result.values['Technology'][i]==pytest.approx(technology,rel=1e-12)
        assert result.values['Cumulative Output'][i]==pytest.approx(output,rel=1e-12)
        assert result.values['Cumulative Consumption'][i]==pytest.approx(consumption,rel=1e-12)
        production=technology*capital**.36*100**.64
        assert result.values['Output'][i]==pytest.approx(production)
        assert result.values['Investment'][i]==pytest.approx(.2*production)
        assert result.values['Consumption'][i]==pytest.approx(.8*production)
        capital+=(.2*production-.025*capital)
        output+=production;consumption+=.8*production
        technology=math.exp(.95*math.log(technology)+.01*math.sin(t/5))
    assert all(min(result.values[s.name])>=0 for s in model.stocks)
    quiet=model.model_copy(deep=True)
    next(v for v in quiet.variables if v.name=='Epsilon').equation='0'
    constant=simulate(quiet)
    assert constant.values['Technology']==[1.]*201
    for change in ({'dt':.5},{'integration_method':'rk4'},{'discrete_period':None,'dt':.5}):
        settings=model.time_settings.model_copy(update=change)
        with pytest.raises((ValueError,EquationError)):
            simulate(model,settings)


def cohort_queue(dt,end=365):
    """Independent nonnegative cohort bookkeeping; no equation parser or DELAY."""
    exposed=deque([20*dt]*round(5/dt))
    infectious=deque([(10/7)*dt]*round(7/dt))
    susceptible=1e6;recovered=0.
    states=[]
    for _ in range(round(end/dt)+1):
        e=sum(exposed);i=sum(infectious)
        states.append([susceptible,e,i,recovered])
        entering=.5*susceptible*i/1000110*dt
        entering_i=exposed.popleft();leaving_i=infectious.popleft()
        susceptible-=entering;recovered+=leaving_i
        exposed.append(entering);infectious.append(entering_i)
    return np.array(states).T


@lru_cache(None)
def seir_method_of_steps():
    """Continuous DDE with independent piecewise incidence prehistory."""
    segments=[]
    def past(q):
        if q<0:return 20 if q>=-5 else 10/7
        s,e,i,r=segments[min(int(q),len(segments)-1)].sol(q)
        return .5*s*i/1000110
    def rhs(t,y):
        current=.5*y[0]*y[2]/1000110
        incubation=past(t-5);recovery=past(t-12)
        return [-current,current-incubation,incubation-recovery,recovery]
    initial=[1e6,100,10,0]
    for day in range(365):
        result=solve_ivp(rhs,(day,day+1),initial,method='DOP853',rtol=1e-11,
                         atol=1e-8,max_step=.2,dense_output=True)
        assert result.success
        segments.append(result);initial=result.y[:,-1]
    return np.column_stack([segments[min(i,364)].sol(i) for i in range(366)])


def test_delayed_seir_explicit_history_boundaries_queues_and_convergence():
    model,result=run('delay-differential-seir-epi','epidemiology')
    continuous=seir_method_of_steps()
    assert continuous.min()>-1e-5
    errors=[]
    for divisor in (1,2,4):
        modified=model.model_copy(deep=True);modified.time_settings.dt/=divisor
        got=simulate(modified);dt=modified.time_settings.dt
        states=np.array([got.values[s.name] for s in model.stocks])
        queues=cohort_queue(dt)
        assert queues.min()>=0
        np.testing.assert_allclose(states,queues,rtol=1e-11,atol=5e-7)
        np.testing.assert_allclose(states.sum(axis=0),1000110,rtol=0,atol=1e-7)
        assert states.min()>-1e-7
        incubation=np.array(got.values['End Incubation'])
        recovery=np.array(got.values['Recovery'])
        n5=round(5/dt);n7=round(7/dt);n12=round(12/dt)
        np.testing.assert_allclose(incubation[:n5],20)
        assert incubation[n5]==pytest.approx(.5*1e6*10/1000110)
        np.testing.assert_allclose(recovery[:n7],10/7)
        np.testing.assert_allclose(recovery[n7:n12],20)
        assert recovery[n12]==pytest.approx(incubation[n5])
        errors.append(np.max(np.abs(states[:,::round(1/dt)]-continuous)))
    assert errors[1]<errors[0]*.55 and errors[2]<errors[1]*.55
    shifted=model.model_copy(deep=True)
    shifted.time_settings.start=13;shifted.time_settings.end=378
    got=simulate(shifted)
    for stock in model.stocks:
        np.testing.assert_allclose(got.values[stock.name],result.values[stock.name],rtol=1e-12,atol=1e-7)


def test_v19_b_portable_receipt_hashes_and_preserved_original_geometry():
    ledger=json.loads((ROOT/'operations/corpus-repairs-v19-b.json').read_text())
    assert len(ledger['models'])==16
    for row in ledger['models']:
        before=row['before_text'].encode()
        assert hashlib.sha256(before).hexdigest()==row['before_sha256']
        if row['id']=='limits-to-growth-system-archetype-edu':continue
        after=pre_hardening_v19_bytes(ROOT,row['file'])
        assert hashlib.sha256(after).hexdigest()==row['after_sha256']
        old,new=json.loads(before),json.loads(after)
        for kind in ('stocks','flows','variables','connectors'):
            new_elements={e['id']:e for e in new.get(kind,[])}
            for element in old.get(kind,[]):
                assert element['id'] in new_elements
                assert element.get('position')==new_elements[element['id']].get('position')
        assert row['source_evidence'] and row['causal_chain']
        assert row['independent_math'] and row['current_probes'] and 'remaining_gaps' in row


def test_remaining_source_domain_counterexamples_are_not_numerical_repairs():
    cases=[
        ('platform-network-effects-advanced-eco','economics',{'User Perceived Value':51,'Provider Perceived Value':26},['User Churn','Provider Churn']),
        ('startup-ecosystem-dynamics-eco','economics',{'Available Funding':0},[]),
        ('trophic-cascade-ecosystem-eco','economics',{'Mesopredators':0},['Meso_Growth']),
        ('online-learning-platform-edu','education',{'Content_Quality':101,'Active_Learners':100},['Late_Dropout']),
        ('peer-vaccination-network-nudge-epi','epidemiology',{'Vaccinated':.9},['New Infections']),
    ]
    for slug,category,update,negative in cases:
        model=load(slug,category)
        stocks={s.name:s.initial_value for s in model.stocks};stocks.update(update)
        values=evaluate(model,stocks,0,model.time_settings.dt,{}, {})
        for name in negative:assert values[name]<0
        if slug=='startup-ecosystem-dynamics-eco':
            assert values['New Funding']-values['Funding Deployment']==-4250
    reference=json.loads((FIX/'independent-remaining.json').read_text())
    assert len(reference)==9
    # These independent solves exceeded the old6000-evaluation ceiling;
    # neither step-size exhaustion nor the explicit1e80 threshold proves blowup.
    for slug in ('platform-network-effects-advanced-eco','rd-investment-innovation-eco',
                 'semiconductor-chip-shortage-supply-chain-eco','leverage-cycle-dynamics-fin',
                 'momentum-trading-dynamics-fin'):
        assert reference[slug]['nfev']>6000
        assert reference[slug]['success'] is False
    peer=reference['peer-vaccination-network-nudge-epi']
    assert peer['success'] and peer['end']==365
    assert peer['maximum'][4]>1
