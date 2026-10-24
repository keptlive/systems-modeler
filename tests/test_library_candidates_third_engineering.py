"""Independent admission checks; no active catalog mutation."""
import json,hashlib,math
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.linalg import expm
from app.core.model import Model
from app.core.simulator import simulate
from app.core.units import analyze_units
from app.core.validation import inspect_inputs
from tests.library_admission import baseline_models
ROOT=Path(__file__).parents[1];D=ROOT/'operations/library-candidates-third-engineering'
ENTRIES=json.loads((D/'MANIFEST.json').read_text())['candidates']
def rhs(key):
    if key=='lyapunov-model-reference-adaptation':
        def f(t,z):
            x,m,kr,kx=z;r=np.sin(np.pi*.1*t)+.5*np.sin(.7*t);e=m-x
            return [-x+.5*(kx*x+kr*r),-2*m+2*r,r*e,x*e]
        return f
    if key=='magnetic-levitation-inverse-square':
        def f(t,z):
            x,v=z;u=.02*np.sqrt(.2*9.81/.000313)+100*(x-.02)+3*v
            return [v,9.81-.000313/.2*u*u/(x*x)-v]
        return f
    if key=='aircraft-longitudinal-pitch':return lambda t,z:[-.313*z[0]+56.7*z[1]+.00232,-.0139*z[0]-.426*z[1]+.000203,56.7*z[1]]
    if key=='tethered-kite-crosswind':
        def f(t,z):
            a,b,c=z;u=.5*np.sin(.1*t);e=6-.028*u*u;v=10*e*np.cos(a);dphi=-v*np.sin(c)/(400*np.sin(a))
            return [v/400*(np.cos(c)-np.tan(a)/e),dphi,v*u/400+dphi*np.cos(a)]
        return f
    if key=='tire-slip-dynamic-vehicle':
        def f(t,z):
            x,y,psi,v,w,r=z;delta=.1
            af=-np.arctan2(r*.178+w,v)+delta;ar=np.arctan2(r*.147-w,v)
            front=134.585*np.sin(.085*np.arctan(9.242*af));rear=159.919*np.sin(.133*np.arctan(17.716*ar));drive=(20-.000000692*v)*.6-.67*v*v-3.99
            return [v*np.cos(psi)-w*np.sin(psi),v*np.sin(psi)+w*np.cos(psi),r,(drive-front*np.sin(delta))/5.692+w*r,(rear+front*np.cos(delta))/5.692-v*r,(front*.178*np.cos(delta)-.178*drive*np.sin(delta)-.147*rear)/.204]
        return f
    if key=='battery-polarization-thermal':return lambda t,z:[-100/360000,-z[1]/30-.002,(4-100*z[1]-10*(z[2]-z[3]))/1000,(10*(z[2]-z[3])-10*(z[3]-25))/500]
    if key=='compressor-plenum-surge':
        b=.8319;h=.18;w=.25;phi=.3;k3=h/(2*w**3);k2=3*h/(2*w*w)*(phi/w-1);k1=3*h*phi/(2*w*w)*(phi/w-2)
        return lambda t,z:[(z[1]-.411*(np.sqrt(z[0]+.533)-np.sqrt(.533)))/b,b*(-k3*z[1]**3-k2*z[1]**2-k1*z[1]-z[0])]
    if key=='bouc-wen-hysteretic-isolator':
        def f(t,z):
            x,v,h=z
            return [v,np.sin(1.2*t)-.1*v-.1*x-.9*h,v-.5*abs(v)*h-.5*v*abs(h)]
        return f
    if key=='batch-crystallization-moments':
        def f(t,z):
            a,b,c,d,s=z;g=.5*(s-1);birth=.2*(s-1)**2
            return [birth,g*a,2*g*b,3*g*c,-3*g*c]
        return f
    if key=='three-generator-sine-network':
        weights=np.array([[0,1,.5],[1,0,.8],[.5,.8,0]])
        return lambda t,z:np.r_[z[3:],(-.4*z[3:]-np.sum(weights*np.sin(z[:3,None]-z[None,:3]),axis=1))/2]
    if key=='industrial-polymerization-heat-loops':
        def f(t,z):
            water,mon,poly,tr,ts,tj,te,tc,acc=z;total=water+mon+poly;u=poly/(mon+poly)
            kr=7*np.exp(-8500/(8.314*tr))*(4*(1-u)+32*u);ke=7*np.exp(-8500/(8.314*te))*(4*(1-u)+32*u)
            transfer=(water*17280+mon*3600+poly*360)/total;rr=kr*mon*(1-200/total);re=ke*mon/total*200
            return [333,667-rr-re,rr+re,(3000*(298.15-tr)-transfer*65*(tr-ts)-100000*(tr-te)+950*rr)/(5*total),transfer*65*(tr-2*ts+tj)/(.47*39000),(1260000*(333.15-tj)+transfer*65*(ts-tj))/21000,(100000*(tr-te)-3600000*(te-tc)+950*re)/1000,(420000*(298.15-tc)+3600000*(te-tc))/4200,1000]
        return f
    raise KeyError(key)

@pytest.mark.parametrize('e',ENTRIES,ids=lambda e:e['file'])
def test_full_series_refinement_and_admission(e):
    m=Model(**json.loads((D/e['file']).read_text()));r=simulate(m);actual=np.array([r.values[s.name] for s in m.stocks]);f=rhs(Path(e['file']).stem)
    ref=solve_ivp(f,(0,r.time[-1]),actual[:,0],t_eval=r.time,method='DOP853',rtol=2e-11,atol=1e-12)
    assert ref.success;scale=np.maximum(1,np.max(abs(ref.y),axis=1));err=np.max(abs(actual-ref.y)/scale[:,None]);assert err<3e-6
    fine=m.model_copy(deep=True);fine.time_settings.dt/=2
    if fine.time_settings.integration_method=='radau':fine.time_settings.rtol/=10;fine.time_settings.atol/=10
    fr=simulate(fine);fv=np.array([fr.values[s.name][::2] for s in m.stocks]);assert np.max(abs(actual-fv)/scale[:,None])<3e-6
    assert np.isfinite(actual).all() and any(np.ptp(row)>1e-6 for row in actual)
    assert inspect_inputs(m,numerical_check=False)['valid'];assert not analyze_units(m)['errors']
    if e['file'].startswith('magnetic-'):assert actual[0].min()>.015 and abs(actual[0,-1]-.02)<1e-6
    if e['file'].startswith('tethered-'):assert actual[0].min()>.5 and actual[0].max()<1.5
    if e['file'].startswith('tire-slip'):assert actual[3].min()>2 and actual[3].max()<4
    if e['file'].startswith('battery-'):np.testing.assert_allclose(actual[0],.5-np.array(r.time)/3600,atol=1e-12)
    if e['file'].startswith('batch-cryst'):
        np.testing.assert_allclose(actual[4]+actual[3],1.2125,atol=1e-10);assert actual[4].min()>1
        assert np.min(actual[0]*actual[2]-actual[1]**2)>-1e-10
        assert np.min(actual[1]*actual[3]-actual[2]**2)>-1e-10
    if e['file'].startswith('industrial-'):np.testing.assert_allclose(np.sum(actual[:3],axis=0),10879.5+1000*np.array(r.time),atol=2e-8)
    if e['file'].startswith('lyapunov-'):
        v=(actual[1]-actual[0])**2+.5*((actual[2]-4)**2+(actual[3]+2)**2)
        assert np.max(np.diff(v))<1e-8 and v[-1]<.2*v[0]
    if e['file'].startswith('compressor-'):assert np.min(actual[0]+.533)>0 and np.ptp(actual[1])>.5
    if e['file'].startswith('bouc-'):assert np.max(abs(actual[2]))<1+1e-8
    if e['file'].startswith('three-generator-'):
        energy=np.sum(actual[3:]**2,axis=0)+(1-np.cos(actual[0]-actual[1]))+.5*(1-np.cos(actual[0]-actual[2]))+.8*(1-np.cos(actual[1]-actual[2]))
        assert np.max(np.diff(energy))<1e-9 and energy[-1]<.001*energy[0]
        np.testing.assert_allclose(np.sum(actual[:3],axis=0),0,atol=1e-12)

def test_matrix_exponential_and_analytic_references():
    for key,n in [('aircraft-longitudinal-pitch',3),('battery-polarization-thermal',4)]:
        e=next(e for e in ENTRIES if e['file']==key+'.json');initial=np.array(list(e['initials'].values()));f=rhs(key);b=np.array(f(0,np.zeros(n)));a=np.column_stack([np.array(f(0,np.eye(n)[i]))-b for i in range(n)])
        augmented=np.block([[a,b[:,None]],[np.zeros((1,n+1))]])
        m=Model(**json.loads((D/e['file']).read_text()));r=simulate(m);values=np.array([r.values[s.name] for s in m.stocks])
        for i in np.linspace(0,len(r.time)-1,31).astype(int):np.testing.assert_allclose(values[:,i],(expm(augmented*r.time[i])@np.r_[initial,1])[:n],atol=1e-7)

def test_random_physical_invariants_and_lyapunov_laws():
    rng=np.random.default_rng(17)
    for _ in range(100):
        x,m,kr,kx=rng.uniform(-2,2,4);t=rng.uniform(0,100);f=rhs('lyapunov-model-reference-adaptation')(t,[x,m,kr,kx]);e=m-x
        # V=e²+|B|/gamma[(kr-4)²+(kx+2)²], exact derivative=-4e².
        assert abs(2*e*(f[1]-f[0])+(kr-4)*f[2]+(kx+2)*f[3]+4*e*e)<1e-12
        x,v,z=rng.uniform(-1,1,3);t=rng.uniform(0,40);f=rhs('bouc-wen-hysteretic-isolator')(t,[x,v,z]);loss=.9*(.5*abs(v)*z*z+.5*v*z*abs(z))
        assert loss>=-1e-15;assert abs(v*f[1]+.1*x*f[0]+.9*z*f[2]-(np.sin(1.2*t)*v-.1*v*v-loss))<1e-12
        z=rng.uniform(-.5,.5,6);f=rhs('three-generator-sine-network')(0,z);w=np.array([[0,1,.5],[1,0,.8],[.5,.8,0]])
        pe=np.sum(w*np.sin(z[:3,None]-z[None,:3]),axis=1)
        assert abs(np.sum(pe))<1e-15;assert abs(np.dot(2*z[3:],f[3:])+np.dot(pe,z[3:])+.4*np.dot(z[3:],z[3:]))<1e-14
        s,v,tc,tj=rng.uniform(0,30,4);f=rhs('battery-polarization-thermal')(0,[s,v,tc,tj]);assert abs(1000*f[2]+500*f[3]-(4-100*v-10*(tj-25)))<1e-10

def test_ids_hashes_and_rhs_fingerprints_against_active_and_staged():
    seen=set()
    others=baseline_models(ROOT,{e['id'] for e in ENTRIES})
    for p in (ROOT/'operations').glob('library-candidates*/*.json'):
        if p.parent!=D:others.append(json.loads(p.read_text()))
    for e in ENTRIES:
        p=D/e['file'];m=json.loads(p.read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==e['candidate_sha256']
        fp=tuple(sorted(f['equation'].replace(' ','').lower() for f in m['flows']));assert fp not in seen;seen.add(fp)
        for raw in others:
            if not isinstance(raw,dict) or not raw.get('stocks') or not raw.get('flows'):continue
            assert raw.get('id')!=m['id'];assert raw.get('name','').lower()!=m['name'].lower()
            assert fp!=tuple(sorted(f.get('equation','').replace(' ','').lower() for f in raw['flows']))

def test_expanded_rhs_screen_and_source_receipts():
    import importlib.util
    spec=importlib.util.spec_from_file_location('engineering_duplicate_screen',D/'duplicate_screen.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    report=module.screen(ROOT,D)
    assert report['compared']>=978
    assert all(not row['exact_expanded_matches'] for row in report['candidates'])
    assert all(not row['constant_abstracted_shape_matches'] for row in report['candidates'])
    if (D/'EVIDENCE.json').exists():
        receipt=json.loads((D/'EVIDENCE.json').read_text())
        assert {e['candidate_sha256'] for e in ENTRIES}=={e['sha256'] for e in receipt['candidates']}
        for row in receipt['retained_sources']:assert hashlib.sha256((D/row['file']).read_bytes()).hexdigest()==row['sha256']

def test_expanded_rhs_resolves_legacy_stock_name_endpoints():
    import importlib.util
    spec=importlib.util.spec_from_file_location('engineering_endpoint_screen',D/'duplicate_screen.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    by_id=dict(stocks=[dict(id='s',name='Quantity')],variables=[dict(name='Rate',equation='2')],flows=[dict(name='Inflow',equation='Rate',to_stock='s')])
    by_name=json.loads(json.dumps(by_id));by_name['flows'][0]['to_stock']='Quantity'
    assert module.fingerprint(by_id)==module.fingerprint(by_name)
    assert "('num', 2.0)" in module.fingerprint(by_name)

def test_crystal_characteristic_birth_cohort_integrals():
    from scipy.integrate import quad
    def augmented(t,z):return [*rhs('batch-crystallization-moments')(t,z[:5]),.5*(z[4]-1)]
    sol=solve_ivp(augmented,(0,80),[.1,.05,.025,.0125,1.2,0],method='DOP853',rtol=1e-12,atol=1e-13,dense_output=True)
    for t in [1,10,30,80]:
        z=sol.sol(t);shift=z[5]
        for j in range(4):
            # Monodisperse seeds translate by total growth. Each birth cohort
            # has size equal to growth integrated since its birth time.
            cohort=quad(lambda s:.2*(sol.sol(s)[4]-1)**2*(shift-sol.sol(s)[5])**j,0,t,epsabs=1e-12,epsrel=1e-11)[0]
            assert z[j]==pytest.approx(.1*(.5+shift)**j+cohort,rel=1e-10,abs=1e-12)

def test_equilibria_source_geometry_and_polymer_mass_closure():
    lev=rhs('magnetic-levitation-inverse-square');np.testing.assert_allclose(lev(0,[.02,0]),[0,0],atol=1e-14)
    # Independent analytic local poles: derivative of inverse-square force and
    # voltage feedback about the levitation gap, not a numerical fit.
    u=.02*np.sqrt(.2*9.81/.000313);a=2*9.81/.02-2*9.81*100/u;b=-1-2*9.81*3/u
    assert np.max(np.real(np.linalg.eigvals([[0,1],[a,b]])))<0
    np.testing.assert_allclose(rhs('compressor-plenum-surge')(0,[0,0]),[0,0],atol=0)
    assert np.max(np.real(np.linalg.eigvals([[-.411/(2*.8319*np.sqrt(.533)),1/.8319],[-.8319,-.8319*(3*.18*.3/(2*.25**2)*(.3/.25-2))]])))>0
    rng=np.random.default_rng(31)
    for _ in range(100):
        a,b,c=rng.uniform(.6,1.2),rng.uniform(-1,1),rng.uniform(-.5,.5);t=rng.uniform(0,120)
        da,db,dc=rhs('tethered-kite-crosswind')(t,[a,b,c]);steer=.5*np.sin(.1*t);airspeed=10*(6-.028*steer**2)*np.cos(a)
        assert abs(dc-np.cos(a)*db-airspeed/400*steer)<1e-16
        z=np.r_[rng.uniform([8000,100,10],[12000,1000,4000]),rng.uniform(300,370,5),0]
        f=rhs('industrial-polymerization-heat-loops')(0,z);assert abs(sum(f[:3])-1000)<1e-12
