"""Source equations, independent references and conservation checks for v1.9 A."""
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.linalg import expm

from app.core.model import Model
from app.core.simulator import simulate
from app.core.integration import evaluate
from app.core.equations import EquationError

ROOT = Path(__file__).resolve().parents[1]
SOURCES = json.loads((ROOT/'tests/fixtures/corpus-v19-a-sources.json').read_text())
REPAIRED = [
    'beer-distribution-game-cla', 'world3-non-renewable-resources-sector-cla',
    'global-carbon-cycle-model-cli', 'ocean-heat-content-dynamics-cli',
    'phosphorus-lake-eutrophication-cli', 'solar-irradiance-and-climate-model-cli',
]

def model(name):
    return Model.model_validate_json(next(ROOT.glob('models/*/'+name+'.json')).read_text())

@lru_cache(None)
def run(name, divisor=1, strict=False):
    m=model(name)
    settings=m.time_settings.model_copy(update={'dt':m.time_settings.dt/divisor})
    if strict: settings=settings.model_copy(update={'rtol':1e-10,'atol':1e-12})
    return simulate(m,settings)

def carbon_rhs(t,y):
    """Hand transcription of Bice's simple terrestrial and ocean equations."""
    a,v,s,o,d,c=y
    ppm=a*280/600; temp=(ppm-280)*.01
    g=125*(ppm-30)/(ppm-30+62.5)*(1+.04*temp)
    litter=50*v/610; soil=49.4*s/1580*(1+.1*temp); runoff=.6*s/1580
    carbon=o/12000/.0363; alk=2.22; kc=.000575+.000006*10
    h=(carbon-math.sqrt(carbon*carbon-alk*(2*carbon-alk)*(1-4*kc)))/(1-4*kc)
    carbonate=(alk-h)/2; poc=280*(.035+.0019*10)*h*h/carbonate
    exchange=.278*(ppm-poc); down=90.6*o/891.62591; up=100*d/38000
    return [6+.6+1.5-.5*g+soil-exchange,
            .5*g-litter-1.125,litter-soil-.375-runoff,
            exchange+runoff+up-down-10,down-up+10-.6,7.5]

def phosphorus_rhs(t,y):
    p,s,a=y[:3]
    growth=.3*a*p/(5+p); loss=.1*a
    sediment=.1*p; release=.01*s*(1+2*max(0,(a-20)/20))
    return [1-p/365-sediment+release-growth+loss,
            sediment-release,growth-loss,p/365]

def beer_step(y,t):
    """Native weekly board accounting, independent of expression evaluator."""
    labels=['Retailer','Wholesaler','Distributor','Factory']
    a=['R','W','D','F']; incoming=[4 if t<5 else 8]+[y['Incoming Orders '+x] for x in a[:3]]
    receiving=[y['In Transit Two '+x] for x in a]
    shipping=[min(incoming[i]+y[labels[i]+' Backlog'],y[labels[i]+' Inventory']+receiving[i]) for i in range(4)]
    place=[]
    for i,x in enumerate(a):
        ri=y[labels[i]+' Inventory']+receiving[i]-shipping[i]
        rb=y[labels[i]+' Backlog']+incoming[i]-shipping[i]
        esl=y['Supply Line '+labels[i]]-receiving[i]
        wanted=y['Expected Order Rate '+x]+.26*((12 if i==3 else 17)-(ri-rb)-.34*esl)
        place.append(4 if t<5 else max(0,math.floor(wanted+.5)))
    out=dict(y)
    for i,x in enumerate(a):
        label=labels[i]
        out[label+' Inventory']+=receiving[i]-shipping[i]
        out[label+' Backlog']+=incoming[i]-shipping[i]
        out['Supply Line '+label]+=place[i]-receiving[i]
        transit_inflow=y['Orders Placed F'] if i==3 else shipping[i+1]
        out['In Transit One '+x]+=transit_inflow-y['In Transit One '+x]
        out['In Transit Two '+x]+=y['In Transit One '+x]-receiving[i]
        out['Orders Placed '+x]+=place[i]-y['Orders Placed '+x]
        if i!=3:out['Incoming Orders '+x]+=y['Orders Placed '+x]-y['Incoming Orders '+x]
        out['Expected Order Rate '+x]+=.25*(incoming[i]-y['Expected Order Rate '+x])
    return out

def test_portable_before_after_receipts_and_preserved_geometry():
    ledger=json.loads((ROOT/'operations/corpus-repairs-v19-a.json').read_text())
    assert len(ledger['models'])==16
    for row in ledger['models']:
        before=row['before_text'].encode();after=(ROOT/row['file']).read_bytes()
        assert hashlib.sha256(before).hexdigest()==row['before_sha256']
        assert hashlib.sha256(after).hexdigest()==row['after_sha256']
        old,new=json.loads(before),json.loads(after)
        assert old['id']==new['id']
        new_elements={e['id']:e for k in ('stocks','flows','variables','connectors') for e in new.get(k,[])}
        for k in ('stocks','flows','variables','connectors'):
            for e in old.get(k,[]):
                assert e['id'] in new_elements
                assert e.get('position')==new_elements[e['id']].get('position')
        assert old['time_settings']['start']==new['time_settings']['start']
        assert old['time_settings']['end']==new['time_settings']['end']

@pytest.mark.parametrize('name',REPAIRED)
def test_defaults_and_refinements_reach_full_horizon(name):
    m=model(name)
    divisors=(1,) if m.time_settings.discrete_period is not None else (1,2,4)
    for divisor in divisors:
        r=run(name,divisor)
        assert r.time[-1]==m.time_settings.end
        for s in m.stocks:
            ys=np.array(r.values[s.name]);assert np.isfinite(ys).all()
            if name!='solar-irradiance-and-climate-model-cli':assert ys.min()>=-1e-7

def test_world3_matches_native_standalone_euler_and_tables():
    m=model(REPAIRED[1]);r=run(REPAIRED[1]);n=1e12;c=2.1e11
    for k,t in enumerate(r.time):
        assert r.values['Non-Renewable Resources'][k]==pytest.approx(n,rel=2e-14)
        assert r.values['Industrial Capital'][k]==pytest.approx(c,rel=2e-14)
        fraction=np.interp(n/1e12,np.arange(11)/10,[1,.9,.7,.5,.2,.1,.05,.05,.05,.05,.05])
        pop=1.65e9*math.exp(.012*(t-1900));io=c*(1-fraction)/3
        pcrum=np.interp(io/pop,np.arange(9)*200,[0,.85,2.6,4.4,5.4,6.2,6.8,7,7])
        n-=pop*pcrum;c+=io*.33-c/14
    assert len(m.tables)==2
    for v in (0,1e-4,.2,.7,1):
        vals=evaluate(m,{'Non-Renewable Resources':v*1e12,'Industrial Capital':2.1e11},1900,1,{}, {})
        assert 0<=vals['Resource Extraction Capital Requirement']<=1

def test_beer_native_weekly_replication_and_queue_invariants():
    m=model(REPAIRED[0]);r=run(REPAIRED[0]);y={s.name:s.initial_value for s in m.stocks}
    for k,t in enumerate(r.time):
        for name,v in y.items():assert r.values[name][k]==pytest.approx(v,abs=2e-12)
        y=beer_step(y,t)
    for x,label,up in [('R','Retailer','Wholesaler'),('W','Wholesaler','Distributor'),('D','Distributor','Factory'),('F','Factory',None)]:
        queue=np.array(r.values['Orders Placed '+x])+r.values['In Transit One '+x]+np.array(r.values['In Transit Two '+x])
        if up:queue+=np.array(r.values['Incoming Orders '+x])+r.values[up+' Backlog']
        assert np.allclose(r.values['Supply Line '+label],queue,atol=1e-12)
    # The source board game is weekly; fractional overrides must not change it.
    assert m.time_settings.discrete_period==1
    for divisor in (2,4):
        with pytest.raises(EquationError,match='Discrete'):
            run(REPAIRED[0],divisor)

def test_ocean_matches_independent_matrix_and_energy_budget():
    name=REPAIRED[3];c0,c1,c2=3.62,9.47,98.66;k0,k1,k2=.54,2.39,.63;eps=1.59
    a=np.zeros((5,5));a[:3,:3]=[[-(k0+k1)/c0,k1/c1,0],[k1/c0,-(k1+eps*k2)/c1,eps*k2/c2],[0,k2/c1,-k2/c2]]
    a[0,3]=.0093;a[0,4]=.465;a[3,4]=1
    exact=(expm(a*100)@np.array([0,0,0,0,1]))[:3]
    errors=[]
    for divisor in (1,2,4):
        r=run(name,divisor);q=np.array([r.values[s][-1] for s in ['Surface_Layer_Heat','Intermediate_Layer_Heat','Deep_Ocean_Heat']])
        errors.append(np.max(abs(q-exact)))
        assert np.allclose(r.values['Sea_Surface_Temperature'],np.array(r.values['Surface_Layer_Heat'])/c0,atol=5e-14)
        total=sum(np.array(r.values[s]) for s in ['Surface_Layer_Heat','Intermediate_Layer_Heat','Deep_Ocean_Heat'])
        external=np.array(r.values['Radiative_Forcing_Uptake'])-r.values['Ocean_Heat_Release']-np.array(r.values['Efficacy Feedback'])
        assert np.allclose(np.diff(total),external[:-1]*.5/divisor,atol=5e-14)
    assert errors[2]<errors[1]<errors[0]<.003*np.max(exact)
    assert .45<errors[1]/errors[0]<.55 and .45<errors[2]/errors[1]<.55

def test_carbon_independent_radau_bdf_and_conservation():
    name=REPAIRED[2];m=model(name);r=run(name);initial=[600,610,1580,891.62591,38000,0]
    refs=[solve_ivp(carbon_rhs,(0,250),initial,method=method,rtol=1e-10,atol=1e-11,t_eval=np.arange(251)) for method in ('Radau','BDF')]
    assert all(s.success for s in refs)
    actual=np.array([r.values[s.name] for s in m.stocks])
    assert np.allclose(refs[0].y,refs[1].y,rtol=2e-8,atol=2e-6)
    assert np.allclose(actual,refs[0].y,rtol=2e-8,atol=2e-6)
    assert np.allclose(actual[:5].sum(axis=0),sum(initial[:5])+6*np.arange(251),atol=1e-7)
    assert np.allclose(actual[5],7.5*np.arange(251),atol=1e-7)
    strict=run(name,1,True)
    for s in m.stocks:assert np.allclose(strict.values[s.name],r.values[s.name],rtol=2e-8,atol=2e-6)
    assert r.values['Airborne Fraction'][0]==pytest.approx(1,abs=1e-7)

def test_phosphorus_independent_stiff_reference_and_nutrient_budget():
    name=REPAIRED[4];r=run(name);m=model(name)
    a=solve_ivp(phosphorus_rhs,(0,3650),[10,100,5,0],method='Radau',rtol=1e-10,atol=1e-11,t_eval=np.arange(3651))
    b=solve_ivp(phosphorus_rhs,(0,3650),[10,100,5,0],method='BDF',rtol=1e-10,atol=1e-11,t_eval=np.arange(3651))
    assert a.success and b.success
    assert np.allclose(a.y,b.y,rtol=1e-7,atol=3e-5)
    actual=np.array([r.values[s.name] for s in m.stocks])
    assert np.allclose(actual,a.y[:3],rtol=1e-7,atol=3e-5)
    assert np.allclose(a.y[:3].sum(axis=0)+a.y[3],115+np.arange(3651),atol=1e-7)
    assert SOURCES['phosphorus']['Y_cp']==1
    assert actual.min()>=0
    strict=run(name,1,True)
    for s in m.stocks:assert np.allclose(strict.values[s.name],r.values[s.name],rtol=1e-7,atol=3e-5)

def test_solar_real_tsi_alignment_and_independent_heat_response():
    name=REPAIRED[5];m=model(name);points=np.array(SOURCES['solar']['points'])
    assert points[0,0]==1849 and points[-1,0]==2021 and len(points)==173
    assert np.ptp(points[:,1])>1
    def rhs(t,y):
        f=(np.interp(t,points[:,0],points[:,1])-1361)*.7/4
        exchange=.52*(y[0]-y[1]/89.29)
        return [(f-.63*y[0]-1.52*exchange)/7.73,exchange]
    ref=solve_ivp(rhs,(1850,2020),[0,0],method='DOP853',rtol=1e-11,atol=1e-12,max_step=.1,dense_output=True)
    assert ref.success
    errors=[]
    for divisor in (1,2,4):
        r=run(name,divisor);values=np.array([np.array(r.values['Temperature'])-287.5,r.values['Ocean_Heat']])
        errors.append(np.max(abs(values-ref.sol(r.time))))
        assert np.allclose(r.values['TSI'],np.interp(r.time,points[:,0],points[:,1]),atol=1e-10)
    assert errors[2]<errors[1]<errors[0]<.01

def coral_rhs(t,y):
    c,a,h,s,ph,d=y
    severity=min(1,s/8)
    sst=27+.02*(t-2000)+1.5*math.sin(2*3.14159*t)+.5*math.sin(2*3.14159*t/4)
    growth=c*.1*(1-c/80)*max(.3,1-3*(8.1-ph))*(1-severity*.5)
    recruit=5*(100-c-a)*c/100*max(.1,1-a/50)
    mortality=c*.05*(1+.1+.05*(1+2*severity))+c*.3*severity
    return [growth+recruit-mortality,
            a*.5*(1-(c+a)/100)*1.2-a*.4*h/50-a*c/100*.02,
            h*.3*a/30*c/50-h*(.2+.1),
            max(0,sst-29)*4-12*s,-.002,
            -d*.02*(1-c/40)+(100-d)*.01*c/40]

def test_coral_solver_only_change_is_not_a_valid_repair():
    # Hardcoded full-horizon independent RHS: finite integration still violates diversity's0-100 domain.
    ref=solve_ivp(coral_rhs,(2000,2100),[40,20,50,0,8.1,100],method='DOP853',rtol=1e-9,atol=1e-11,max_step=.02)
    assert ref.success and ref.y[5,-1]>450
    assert ref.y[3].min()>=-1e-8
    # Outward vector field at the advertised100% boundary proves it is structural.
    assert coral_rhs(2050,[90,5,10,0,8,100])[5]>0
