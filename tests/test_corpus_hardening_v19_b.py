"""Independent full-horizon mathematics for explicit integration defaults."""
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from app.core.model import Model
from app.core.simulator import simulate
from tests.test_corpus_repairs_v18_b import WORLD2_SOURCE_TABLES

ROOT=Path(__file__).resolve().parents[1]
PLAN={'grid-frequency-stability-ene':('energy',.04),
      'traffic-flow-dynamics-soc':('social',.02),
      'milgram-small-world-soc':('social',.0025),
      'greenshields-traffic-flow-model-tra':('transportation',.02),
      'world2-forrester-original-cla':('classic',.5)}


def load(slug):
    return Model.model_validate_json((ROOT/'models'/PLAN[slug][0]/(slug+'.json')).read_text())


def world2_rhs(t,y):
    def table(name,x):
        dx,ys=WORLD2_SOURCE_TABLES[name]
        return float(np.interp(x,np.arange(len(ys))*dx,ys))
    p,c,n,pol,a=y;cir=c/p;crowd=p/(135e6*26.5);pollution=pol/3.6e9
    material=cir*(1-a)*table('NREM',n/900e9)/.7
    food=table('FPCI',cir*a/.3)*table('FCM',crowd)*table('FPM',pollution)
    birth=p*.045*table('BRMM',material)*table('BRCM',crowd)*table('BRFM',food)*table('BRPM',pollution)
    death=p*.025*table('DRMM',material)*table('DRCM',crowd)*table('DRFM',food)*table('DRPM',pollution)
    desired=table('CFIFR',food)*table('CIQR',table('QLM',material)/table('QLF',food))
    return [birth-death,p*.05*table('CIM',material)-c*.025,-p*table('NRMM',material),
            p*table('POLCM',cir)-pol/table('POLAT',pollution),(desired-a)/15]


def traffic_rhs(t,y):
    density,queue,throughput=y
    inflow=50*(1+.4*math.sin(t/12*3.14159));outflow=density*60*(1-density/150)
    return [inflow-outflow,max(0,density-50)*.1-queue*.2*(1 if density<50 else .2),outflow]


def greenshields_rhs(t,y):
    density,queue=y;arrival=1500+500*math.sin(.5*t);capacity=60*150/4
    departure=min(density*60*(1-density/150),capacity)
    return [arrival-departure,arrival-capacity if density>120 else 0]


@lru_cache(None)
def grid_reference():
    # Eliminate energy using the exact physical invariant, independently of the
    # model's two integrated equations. Locate every deadband crossing explicitly.
    def frequency(t,y):return [(5*(60-y[0])-50*math.sin(.1*t))*60**2/(10000*y[0])]
    f=solve_ivp(frequency,(0,60),[60],method='DOP853',rtol=2e-13,atol=1e-12,max_step=.02,dense_output=True)
    assert f.success
    grid=np.linspace(0,60,3001);switches=[]
    for threshold in (59.98,60.02):
        for left,right in zip(grid,grid[1:]):
            if (f.sol(left)[0]-threshold)*(f.sol(right)[0]-threshold)<0:
                switches.append(brentq(lambda t:f.sol(t)[0]-threshold,left,right,xtol=1e-12))
    boundaries=[0,*sorted(switches),60];pieces=[];initial=500.
    for left,right in zip(boundaries,boundaries[1:]):
        active=abs(60-f.sol((left+right)/2)[0])>.02
        def reserve(t,y):
            deviation=60-f.sol(t)[0]
            return [(1000-y[0])/30-(y[0]*.05*deviation/60 if active else 0)]
        solution=solve_ivp(reserve,(left,right),[initial],method='DOP853',rtol=2e-13,atol=1e-11,max_step=.1,dense_output=True)
        assert solution.success
        pieces.append((left,right,solution));initial=solution.y[0,-1]
    def reference(times):
        frequency=f.sol(times)[0];reserve=np.empty(len(times))
        for i,t in enumerate(times):
            piece=next(s for left,right,s in pieces if left-1e-12<=t<=right+1e-12)
            reserve[i]=piece.sol(t)[0]
        return np.array([frequency,5000*(frequency/60)**2,reserve])
    return reference


@lru_cache(None)
def reference(slug,times):
    times=np.array(times)
    if slug.startswith('grid-'):return grid_reference()(times)
    if slug.startswith('milgram-'):
        reached=3e8/(1+(3e8-1)*np.exp(-50*times))
        hit=math.log(3e8-1)/50
        return np.array([reached,np.minimum(times,hit)])
    model=load(slug);rhs=world2_rhs if slug.startswith('world2-') else traffic_rhs if slug.startswith('traffic-') else greenshields_rhs
    result=solve_ivp(rhs,(times[0],times[-1]),[s.initial_value for s in model.stocks],method='DOP853',
                     rtol=2e-12,atol=1e-11,max_step=.025,t_eval=times)
    assert result.success
    return result.y


@lru_cache(None)
def runs(slug):
    model=load(slug);results=[]
    for divisor in (1,2,4):
        settings=model.time_settings.model_copy(update={'dt':PLAN[slug][1]/divisor,'integration_method':'rk4'})
        results.append(simulate(model,settings))
    return model,results


def metrics(slug):
    model,results=runs(slug);expected=reference(slug,tuple(results[0].time));errors=[]
    for divisor,result in zip((1,2,4),results):
        values=np.array([result.values[s.name] for s in model.stocks])
        sampled=values[:,::divisor]
        scale=np.maximum(np.max(np.abs(expected),axis=1),1)
        errors.append(np.max(np.abs(sampled-expected),axis=1)/scale)
    return np.array(errors)


def test_exact_before_receipts_and_only_explicit_numerical_fields_change():
    ledger=json.loads((ROOT/'operations/corpus-hardening-repairs-v19-b.json').read_text())
    assert {row['id'] for row in ledger['models']}==set(PLAN)
    for row in ledger['models']:
        assert hashlib.sha256(row['before_text'].encode()).hexdigest()==row['before_sha256']==row['baseline_sha256']
        after=(ROOT/row['file']).read_bytes()
        assert hashlib.sha256(after).hexdigest()==row['after_sha256']
        before=json.loads(row['before_text']);current=json.loads(after)
        for field in ('description','name','time_settings','source','reference'):
            before.pop(field,None);current.pop(field,None)
        assert before==current
        old=json.loads(row['before_text'])['time_settings'];new=load(row['id']).time_settings
        assert new.start==old['start'] and new.end==old['end']
        assert row['primary_source_url'] and row['source_evidence'] and row['remaining_gaps']


@pytest.mark.parametrize('slug',PLAN)
def test_full_horizon_refinements_against_independent_equations(slug):
    model,results=runs(slug)
    assert model.time_settings.integration_method=='rk4'
    assert model.time_settings.dt==PLAN[slug][1]
    errors=metrics(slug)
    limits={'grid-frequency-stability-ene':1e-7,'traffic-flow-dynamics-soc':.01,
            'milgram-small-world-soc':.0002,'greenshields-traffic-flow-model-tra':.00045,
            'world2-forrester-original-cla':5e-6}
    assert errors.max()<limits[slug]
    for result in results:
        assert result.time[0]==model.time_settings.start and result.time[-1]==model.time_settings.end
        assert all(math.isfinite(value) for series in result.values.values() for value in series)
        assert all(min(result.values[s.name])>=0 for s in model.stocks)
        if result.integration_diagnostics:
            assert result.integration_diagnostics['work_units']<=1_000_000
        assert len(result.time)*len(result.values)<=1_000_000
    # A discontinuous threshold counter has a phase error bounded by DT, rather
    # than a claimed fixed-order convergence rate. Smooth population still refines.
    if slug.startswith('milgram-'):
        assert errors[1,0]<errors[0,0]/10 and errors[2,0]<errors[1,0]/10
        hit=math.log(3e8-1)/50
        for divisor,result in zip((1,2,4),results):
            times=np.array(result.time)
            np.testing.assert_allclose(result.values['Chain_Steps'],np.minimum(times,hit),rtol=0,atol=model.time_settings.dt/divisor/2)
            assert max(result.values['People_Reached'])<=3e8
            assert min(result.values['Steps_Remaining'])>=0
    elif not slug.startswith('grid-'):
        assert errors[1].max()<errors[0].max() and errors[2].max()<errors[1].max()


def test_grid_physical_energy_identity_and_event_reference():
    model,results=runs('grid-frequency-stability-ene')
    for result in results:
        frequency=np.array(result.values['Grid Frequency']);energy=np.array(result.values['Stored Kinetic Energy'])
        np.testing.assert_allclose(energy,5000*(frequency/60)**2,rtol=0,atol=2e-9)
        assert min(result.values['Spinning Reserve'])>=500


def test_traffic_external_balance_and_reachable_domain_make_zero_queue_exact():
    for result in runs('traffic-flow-dynamics-soc')[1]:
        density=np.array(result.values['Traffic_Density']);times=np.array(result.time)
        omega=3.14159/12
        total=20+50*times+20/omega*(1-np.cos(omega*times))
        np.testing.assert_allclose(density+result.values['Cumulative_Throughput'],total,rtol=0,atol=2e-8)
        # At density0, derivative>=30>0; at density20, derivative<=70-1040<0.
        # This invariant interval excludes both queue branches and proves zero Q.
        assert density.min()>0 and density.max()<=20
        assert result.values['Queue_Length']==[0.]*len(times)
        assert max(result.values['Queue_Formation'])==0


def test_greenshields_capacity_and_default_queue_domain():
    for result in runs('greenshields-traffic-flow-model-tra')[1]:
        density=np.array(result.values['Vehicle_Density'])
        # Arrival in[1000,2000]; q(0)=0, q(50)=2000 imply invariant[0,50].
        assert density.min()>0 and density.max()<50<120
        assert result.values['Capacity']==[2250.]*len(result.time)
        np.testing.assert_allclose(result.values['Flow'],density*60*(1-density/150),rtol=1e-14)
        assert result.values['Queue_Length']==[0.]*len(result.time)


def test_world2_retains_all_native_table_points_and_positive_domain():
    model,results=runs('world2-forrester-original-cla')
    assert len(model.tables)==22
    for table in model.tables:
        dx,ys=WORLD2_SOURCE_TABLES[table.name.removeprefix('World2_')]
        assert table.to_list()==[(i*dx,y) for i,y in enumerate(ys)]
    for result in results:
        fraction=result.values['Capital in Agriculture Fraction']
        assert min(fraction)>0 and max(fraction)<1
        resources=np.array(result.values['Natural Resources'])
        assert np.all(np.diff(resources)<0) and resources[-1]>0
        assert min(result.values['Food Ratio'])>0
        assert min(result.values['Pollution Absorption Time'])>=1
