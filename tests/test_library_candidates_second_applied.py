"""Independent full-horizon/reference/balance checks for unapplied candidates."""
import hashlib,json,math
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.linalg import expm
from app.core.model import Model
from app.core.simulator import simulate
from app.core.validation import inspect_inputs
from app.core.units import analyze_units
from tests.library_admission import baseline_models
ROOT=Path(__file__).parents[1];D=ROOT/'operations/library-candidates-second-applied'
ENTRIES=json.loads((D/'MANIFEST.json').read_text())['candidates']
def rhs(key):
    if key=='planar-vtol-coupled-flight':
        def f(t,z):
            x,y,a,v,w,r=z;u=np.clip(-.12*a-.08*r,-3.92,3.92)
            return [v,w,r,(u*np.cos(a)-39.2*np.sin(a)-.05*v)/4,(u*np.sin(a)+39.2*np.cos(a)-39.2-.05*w)/4,.25*u/.0475]
        return f
    if key=='dc-motor-armature-speed':return lambda t,z:[-10*z[0]+z[1],2-.02*z[0]-2*z[1]]
    if key=='quarter-car-road-suspension':
        def f(t,z):
            x,y,v,w=z;r=.05*(1-np.cos(np.pi*t/.2)) if t<.2 else .1;rd=.25*np.pi*np.sin(np.pi*t/.2) if t<.2 else 0
            force=80000*(x-y)+350*(v-w)
            return [v,w,-force/2500,(force-500000*(y-r)-15020*(w-rd))/320]
        return f
    if key=='exothermic-cstr-cooling':
        def f(t,z):
            c,T=z;r=7.2e10*np.exp(-8750/T)*c
            return [1-c-r,350-T+50000/239*r+50000/23900*(295-T)]
        return f
    if key=='binary-distillation-thirty-two':
        def f(t,u):
            y=1.6*u/(1+.6*u);v=np.empty(32);v[0]=8*(y[1]-u[0]);v[1:16]=(3*(u[:15]-u[1:16])-4*(y[1:16]-y[2:17]))/.25
            v[16]=(1+3*u[15]-5*u[16]-4*(y[16]-y[17]))/.25
            v[17:31]=(5*(u[16:30]-u[17:31])-4*(y[17:31]-y[18:32]))/.25;v[31]=(5*u[30]-u[31]-4*y[31])/.1
            return v
        return f
    if key=='averaged-boost-duty-response':return lambda t,z:[1000-40*z[1],400*z[0]-100*z[1]]
    if key=='countercurrent-exchanger-wall-storage':
        def f(t,z):
            a,b,w=np.split(z,3);ain=np.r_[300,a[:-1]];bin=np.r_[b[1:],310]
            qa=2000*(w-(ain+a)/2);qb=2000*((bin+b)/2-w)
            return np.r_[ain-a+qa/4000,bin-b-qb/4000,(qb-qa)/1000]
        return f
    if key=='kalman-bucy-riccati-tracker':
        def f(t,z):
            x,v,m,n,a,b,c=z;acc=.1*np.sin(.4*t);err=x+.2*np.sin(5*t)+.1*np.sin(13*t)-m
            return [v,acc,n+a*err,acc+b*err,2*b-a*a,c-a*b,.1-b*b]
        return f
    if key=='van-de-vusse-selectivity':
        k=1.287e12*np.exp(-9758.3/403.15);d=9.043e9*np.exp(-8560/403.15)
        return lambda t,z:[20*(5.1-z[0])-k*z[0]-d*z[0]**2,k*z[0]-(20+k)*z[1],k*z[1]-20*z[2],.5*d*z[0]**2-20*z[3]]
    if key=='three-tank-nonlinear-hydraulics':
        def f(t,z):
            a,b,c=z;p=.00005*np.sign(a-c)*np.sqrt(19.62*abs(a-c));q=.00005*np.sign(c-b)*np.sqrt(19.62*abs(c-b));o=.00004*np.sqrt(19.62*b)
            return np.array([.0001-p,.0001+q-o,p-q])/.00154
        return f
    raise KeyError(key)

@pytest.mark.parametrize('entry',ENTRIES,ids=lambda e:e['file'])
def test_full_horizon_and_refinement(entry):
    key=Path(entry['file']).stem;m=Model(**json.loads((D/entry['file']).read_text()));r=simulate(m)
    actual=np.array([r.values[s.name] for s in m.stocks]);t=np.array(r.time);init=np.array([s.initial_value for s in m.stocks]);f=rhs(key)
    if key=='three-tank-nonlinear-hydraulics':
        expected=np.empty_like(actual);expected[:,0]=init
        for i in range(len(t)-1):expected[:,i+1]=expected[:,i]+f(t[i],expected[:,i])
    else:
        ref=solve_ivp(f,(0,t[-1]),init,t_eval=t,method='DOP853',rtol=2e-11,atol=1e-12,max_step=.02 if key=='quarter-car-road-suspension' else np.inf)
        assert ref.success;expected=ref.y
    error=np.max(abs(actual-expected)/np.maximum(1,np.max(abs(expected),axis=1))[:,None]);assert error<3e-6
    assert np.isfinite(actual).all() and any(np.ptp(row)>1e-6 for row in actual)
    assert inspect_inputs(m,numerical_check=False)['valid'];assert not analyze_units(m)['errors']
    if key!='three-tank-nonlinear-hydraulics':
        fine=m.model_copy(deep=True);fine.time_settings.dt/=2;fr=simulate(fine);fv=np.array([fr.values[s.name][::2] for s in m.stocks])
        assert np.max(abs(fv-actual)/np.maximum(1,np.max(abs(expected),axis=1))[:,None])<3e-6
    if key=='van-de-vusse-selectivity':np.testing.assert_allclose(actual[0]+actual[1]+actual[2]+2*actual[3],5.1,atol=1e-10)
    if key=='binary-distillation-thirty-two':assert actual.min()>0 and actual.max()<1 and actual[0,-1]>actual[0,0]+.1
    if key=='averaged-boost-duty-response':assert actual[1,1]<20 and abs(actual[1,-1]-25)<1e-5 and actual[0].min()>0
    if key=='kalman-bucy-riccati-tracker':
        assert np.min(actual[4]*actual[6]-actual[5]**2)>0
        np.testing.assert_allclose(actual[4:,-1],[np.sqrt(2*np.sqrt(.1)),np.sqrt(.1),np.sqrt(2*np.sqrt(.1))*np.sqrt(.1)],atol=1e-7)
    if key=='countercurrent-exchanger-wall-storage':assert actual.min()>=300-1e-10 and actual.max()<=310

def test_hashes_and_duplicate_screen():
    active=baseline_models(ROOT,{e['id'] for e in ENTRIES});known={m['id'] for m in active};fps={tuple(sorted(f.get('equation','').replace(' ','').lower() for f in m.get('flows',[]))) for m in active};seen=set()
    for e in ENTRIES:
        p=D/e['file'];m=json.loads(p.read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==e['candidate_sha256'];assert m['id'] not in known
        fp=tuple(sorted(f['equation'].replace(' ','').lower() for f in m['flows']));assert fp not in fps and fp not in seen;seen.add(fp)
        for other in (ROOT/'operations').glob('library-candidates*/*.json'):
            if other.parent==D:continue
            value=json.loads(other.read_text())
            if not isinstance(value,dict) or not value.get('stocks') or not value.get('flows'):continue
            assert m['name'].lower()!=value.get('name','').lower()
            assert fp!=tuple(sorted(f.get('equation','').replace(' ','').lower() for f in value['flows']))
    receipt=json.loads((D/'EVIDENCE.json').read_text())
    assert {e['candidate_sha256'] for e in ENTRIES}=={e['sha256'] for e in receipt['candidates']}
    for s in receipt['retained_sources']:assert hashlib.sha256((D/s['file']).read_bytes()).hexdigest()==s['sha256']

def test_independent_linear_matrix_and_energy_laws():
    for key,n in [('dc-motor-armature-speed',2),('averaged-boost-duty-response',2),('countercurrent-exchanger-wall-storage',9)]:
        f=rhs(key);zero=np.zeros(n);b=f(0,zero);a=np.column_stack([np.array(f(0,np.eye(n)[i]))-b for i in range(n)])
        e=next(x for x in ENTRIES if x['file']==key+'.json');initial=np.array(list(e['initials'].values()));equilibrium=np.linalg.solve(a,-np.array(b));end=e['settings']['end']
        r=solve_ivp(f,(0,end),initial,rtol=1e-11,atol=1e-12,method='DOP853');np.testing.assert_allclose(r.y[:,-1],equilibrium+expm(a*end)@(initial-equilibrium),atol=2e-8)
    rng=np.random.default_rng(13)
    for _ in range(100):
        speed,current=rng.uniform(-2,2,2);ds,di=rhs('dc-motor-armature-speed')(0,[speed,current]);assert abs(.01*speed*ds+.5*current*di-(current-current**2-.1*speed**2))<1e-12
        i,v=rng.uniform(1,30,2);di,dv=rhs('averaged-boost-duty-response')(0,[i,v]);assert abs(.01*i*di+.001*v*dv-(10*i-v*v/10))<1e-10

def test_random_conservation_and_dissipation_laws():
    rng=np.random.default_rng(51)
    for _ in range(100):
        # Summing all tray inventories cancels every internal vapor/liquid flux.
        z=rng.uniform(.05,.95,32);f=rhs('binary-distillation-thirty-two')(0,z)
        assert abs(np.dot(np.r_[.5,np.full(30,.25),.1],f)-(1-z[0]-z[31]))<1e-12
        # Oppositely directed film terms cancel including wall energy storage.
        z=rng.uniform(300,310,9);f=rhs('countercurrent-exchanger-wall-storage')(0,z)
        assert abs(np.dot(np.r_[np.full(6,4000),np.full(3,1000)],f)-4000*(300-z[2]+310-z[3]))<1e-8
        # Tire is stationary after the road rise: stored energy can only decay.
        x,y,v,w=rng.normal(size=4);f=rhs('quarter-car-road-suspension')(1,[x,y,v,w])
        de=2500*v*f[2]+320*w*f[3]+80000*(x-y)*(v-w)+500000*(y-.1)*w
        assert abs(de+350*(v-w)**2+15020*w*w)<1e-8
        # Elemental A-equivalents, including two A units per dimer molecule.
        z=rng.uniform(.01,4,4);f=rhs('van-de-vusse-selectivity')(0,z)
        assert abs(np.dot([1,1,1,2],f)-20*(5.1-np.dot([1,1,1,2],z)))<1e-10
        z=rng.uniform(.2,4,3);f=rhs('three-tank-nonlinear-hydraulics')(0,z)
        assert abs(.00154*np.sum(f)-(.0002-.00004*np.sqrt(19.62*z[1])))<1e-18
        c=rng.uniform(.1,1);T=rng.uniform(310,360);dc,dt=rhs('exothermic-cstr-cooling')(0,[c,T])
        assert abs(dt+50000/239*dc-(350-T+50000/239*(1-c)+50000/23900*(295-T)))<1e-10

def test_riccati_independent_hamiltonian_solution():
    # Fractional linear matrix-exponential solution, independent of scalar RHS.
    a=np.array([[0,1],[0,0]]);q=np.diag([0,.1]);s=np.diag([1,0]);h=np.block([[-a.T,s],[q,a]])
    init=np.vstack([np.eye(2),np.eye(2)])
    sol=solve_ivp(rhs('kalman-bucy-riccati-tracker'),(0,10),[0,1,-1,0,1,0,1],rtol=1e-11,atol=1e-12,dense_output=True)
    for t in np.linspace(0,10,31):
        uv=expm(h*t)@init;p=uv[2:]@np.linalg.inv(uv[:2]);z=sol.sol(t)
        np.testing.assert_allclose(p,[[z[4],z[5]],[z[5],z[6]]],atol=2e-10)
