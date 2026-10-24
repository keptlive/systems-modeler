"""Independent numerical, analytic and invariant checks for staged science models."""
import ast,hashlib,json,math
from functools import lru_cache
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from app.core.model import Model
from app.core.simulator import simulate
from app.core.units import analyze_units
from app.core.validation import inspect_inputs
ROOT=Path(__file__).resolve().parents[1]/'operations/library-candidates-third-science'
MANIFEST=json.loads((ROOT/'manifest.json').read_text());SLUGS=[Path(e['file']).stem for e in MANIFEST]
def slug(prefix):return next(s for s in SLUGS if s.startswith(prefix))
@lru_cache(None)
def model(name):return Model.model_validate_json((ROOT/(name+'.json')).read_text())
@lru_cache(None)
def run(name):return simulate(model(name))
def matrix(r,m):return np.array([r.values[s.name] for s in m.stocks])

def reference(name):
    if name.startswith('rayleigh-'):
        def rhs(t,y):
            r,v,loss=y;pg=100144*(.001/r)**4.2
            return [v,(pg-100000-.144/r-.004*v/r)/(1000*r)-1.5*v*v/r,16*math.pi*.001*r*v*v]
        return rhs
    if name.startswith('lane-'):return lambda x,y:[y[1],-2*y[1]/x-y[0]**3]
    if name.startswith('chapman-'):
        def rhs(t,y):
            a,b,z=y;r1=.001*b;r2=a*b;r3=.1*z;r4=.05*a*z
            return [2*r1-r2+r3-r4,-r1-r2+r3+2*r4,r2-r3-r4]
        return rhs
    if name.startswith('gilbert-'):
        def rhs(t,y):
            x,yy,z=y;p=1/1.01
            return [-p*(yy+.1*x*z),p*(x-.1*yy*z),.1*p*(x*x+yy*yy)]
        return rhs
    if name.startswith('lorentz-'):
        def rhs(t,y):
            x,yy,z,v,w,u=y;q=-1.602e-19/9.109e-31
            return [v,w,u,q*(100+.001*w),-q*.001*v,0]
        return rhs
    if name.startswith('kerr-'):
        def rhs(t,y):
            x,z=y;shift=2-x*x-z*z
            return [-x+shift*z+1.4,-z-shift*x]
        return rhs
    if name.startswith('rate-state-'):
        def rhs(t,y):
            u,age=y;v=math.exp(u);dage=1-v*age
            return [(.02*(1-v)-.015/age*dage)/.01,dage]
        return rhs
    if name.startswith('adiabatic-'):
        def rhs(t,y):
            x,v,p,h=y;volume=.01+.01*x
            return [v,.01*(p-100000)-1000*x-10*v,-1.4*p*.01*v/volume,10*v*v]
        return rhs
    if name.startswith('akzo-'):
        def rhs(t,y):
            a,c,b,z,p=y;bound=115.83*a*z
            r1=18.7*a**4*math.sqrt(c);r2=.58*b*z;r3=.58/34.4*a*p;r4=.09*a*z*z;r5=.42*bound*bound*math.sqrt(c)
            return [-2*r1+r2-r3-r4,-.5*r1-r4-.5*r5+3.3*(.9/737-c),r1-r2+r3,-r2+r3-2*r4,r2-r3+r5]
        return rhs
    if name.startswith('cahn-'):
        def rhs(t,y):
            y=np.asarray(y);mu=y**3-y-.1*(np.roll(y,1)-2*y+np.roll(y,-1))
            return np.roll(mu,1)-2*mu+np.roll(mu,-1)
        return rhs
    if name.startswith('semiconductor-'):
        def rhs(t,y):
            n,s,l=y;stim=.05*(n-10)*s
            return [1500-n-stim,stim-50*s+.0001*n,.9999*n+50*s]
        return rhs
    raise AssertionError(name)

@lru_cache(None)
def independently_solved(name):
    m=model(name);r=run(name)
    # BDF is an independent method for the eliminated stiff benchmark;
    # explicit high-order DOP853 references the other ten systems.
    method='BDF' if name.startswith('akzo-') else 'DOP853'
    solution=solve_ivp(reference(name),(m.time_settings.start,m.time_settings.end),[s.initial_value for s in m.stocks],t_eval=r.time,method=method,rtol=2e-12 if name.startswith('akzo-') else 2e-11,atol=1e-18 if name.startswith('lorentz-') else 1e-15 if name.startswith('akzo-') else 1e-14)
    assert solution.success
    return solution.y

@pytest.mark.parametrize('name',SLUGS)
def test_complete_default_reference_and_units(name):
    m=model(name);r=run(name);actual=matrix(r,m);expected=independently_solved(name)
    assert analyze_units(m)['status']=='consistent'
    assert inspect_inputs(m,numerical_check=False)['valid']
    assert np.isfinite(actual).all() and any(np.ptp(row)>1e-8 for row in actual)
    for a,e in zip(actual,expected):
        np.testing.assert_allclose(a,e,rtol=4e-6,atol=2e-8*max(float(np.max(abs(e))),1e-12))
    signed=next(e['signed_states'] for e in MANIFEST if e['id']==m.id)
    for s in m.stocks:
        if s.name not in signed:assert min(r.values[s.name])>=-1e-10
    assert m.source.startswith('https://') and m.reference
    assert len(r.time)<=10001
    if r.integration_diagnostics:assert r.integration_diagnostics['work_units']<1_000_000


def test_bubble_total_energy_with_resolved_viscous_loss():
    name=slug('rayleigh-');r=run(name);y=matrix(r,model(name));rad,v,loss=y
    kinetic=2*math.pi*1000*rad**3*v*v
    gas=4*math.pi*100144*.001**4.2/(4.2-3)*rad**(3-4.2)
    potential=4*math.pi*(100000*rad**3/3+.072*rad**2)
    total=kinetic+gas+potential+loss
    assert total==pytest.approx(np.full(len(total),total[0]),rel=3e-9,abs=1e-13)
    assert np.all(np.diff(loss)>=0) and min(rad)>.0008 and max(abs(v))<5
    # Independent force equilibrium at the specified ambient radius.
    assert reference(name)(0,[.001,0,0])==pytest.approx([0,0,0],abs=1e-10)
    assert loss[-1]>0


def test_lane_emden_analytic_n0_n1_and_published_n3_surface():
    name=slug('lane-');base=model(name)
    for n,end in [(0,2),(1,3)]:
        m=base.model_copy(deep=True);m.time_settings.end=end
        next(v for v in m.variables if v.name=='Polytropic_Index').equation=str(n)
        x0=.01;m.stocks[0].initial_value=1-x0*x0/6+n*x0**4/120-n*(8*n-5)*x0**6/15120
        m.stocks[1].initial_value=-x0/3+n*x0**3/30-n*(8*n-5)*x0**5/2520
        r=simulate(m);x=np.array(r.time)
        expected=1-x*x/6 if n==0 else np.sin(x)/x
        assert r.values['Theta']==pytest.approx(expected,abs=2e-8)
    m=base.model_copy(deep=True);m.time_settings.end=6.895;r=simulate(m)
    theta=r.values['Theta'][-1];slope=r.values['Radial_Slope'][-1]
    assert 6.895-theta/slope==pytest.approx(6.89685,abs=4e-6)
    assert -6.895**2*slope==pytest.approx(2.01824,abs=5e-6)
    assert m.time_settings.units=='1'  # radius coordinate, explicitly not time


def test_chapman_atom_budget_and_independently_derived_stationary_state():
    name=slug('chapman-');r=run(name);y=matrix(r,model(name))
    assert y[0]+2*y[1]+3*y[2]==pytest.approx(2,abs=4e-13)
    a=(.001+math.sqrt(.001**2+4*.001*.1/.05))/2
    ratio=(a-.001)/.1;b=(2-a)/(2+3*ratio);z=ratio*b;steady=[a,b,z]
    assert reference(name)(0,steady)==pytest.approx([0,0,0],abs=1e-15)
    assert y[:,-1]==pytest.approx(steady,rel=.005)


def test_spin_exact_precession_relaxation_norm_and_field_energy():
    name=slug('gilbert-');r=run(name);y=matrix(r,model(name));t=np.array(r.time);phase=t/1.01
    q=np.arctanh(.8)+.1*t/1.01;transverse=1/np.cosh(q)
    expected=np.array([transverse*np.cos(phase),transverse*np.sin(phase),np.tanh(q)])
    np.testing.assert_allclose(y,expected,rtol=2e-6,atol=2e-8)
    assert np.sum(y*y,axis=0)==pytest.approx(1,abs=2e-8)
    assert np.all(np.diff(-y[2])<=1e-12)


def test_lorentz_exact_crossed_field_orbit_and_electrical_work():
    name=slug('lorentz-');m=model(name);r=run(name);t=np.array(r.time);y=matrix(r,m)
    omega=(-1.602e-19/9.109e-31)*.001;vd=-100/.001
    vx=100000*np.cos(omega*t)+(0-vd)*np.sin(omega*t)
    vy=vd+(0-vd)*np.cos(omega*t)-100000*np.sin(omega*t)
    x=100000*np.sin(omega*t)/omega+(0-vd)*(1-np.cos(omega*t))/omega
    yy=vd*t+(0-vd)*np.sin(omega*t)/omega+100000*(np.cos(omega*t)-1)/omega
    expected=np.array([x,yy,20000*t,vx,vy,np.full(len(t),20000)])
    for a,b in zip(y,expected):np.testing.assert_allclose(a,b,rtol=2e-6,atol=2e-8*max(np.max(abs(b)),1e-12))
    energy=.5*9.109e-31*(y[3]**2+y[4]**2+y[5]**2)-(-1.602e-19)*100*y[0]
    assert energy==pytest.approx(np.full(len(t),energy[0]),rel=2e-7,abs=1e-30)
    # Guiding-centre displacement is perpendicular to E, independent of charge.
    assert np.mean(vy)==pytest.approx(vd,rel=.15)


def test_kerr_three_stationary_intensities_and_two_stable_basins():
    name=slug('kerr-');roots=np.sort(np.roots([1,-4,5,-1.4**2]));assert all(np.isreal(roots))
    reached=[]
    for intensity in [roots[0],roots[-1]]:
        x=intensity/1.4;z=-(2-intensity)*intensity/1.4
        assert reference(name)(0,[x,z])==pytest.approx([0,0],abs=1e-13)
        m=model(name).model_copy(deep=True);m.stocks[0].initial_value=float(x+.01);m.stocks[1].initial_value=float(z)
        r=simulate(m);final=r.values['Intensity'][-1];assert final==pytest.approx(intensity,rel=1e-6);reached.append(final)
    assert reached[1]-reached[0]>.8
    # Determinant changes sign on the middle branch; trace is always -2.
    determinants=1+(2-roots)*(2-3*roots)
    assert determinants[0]>0 and determinants[1]<0 and determinants[2]>0


def test_rate_state_friction_loading_identity_and_stiffness_boundary():
    name=slug('rate-state-');r=run(name)
    assert math.exp(r.values['Log_Slip_Speed'][-1])==pytest.approx(1,abs=1e-8)
    assert r.values['Contact_Age'][-1]==pytest.approx(1,abs=1e-8)
    for u,age in [(-.3,.5),(.2,2),(0,1)]:
        du,da=reference(name)(0,[u,age])
        assert .01*du+.015*da/age==pytest.approx(.02*(1-math.exp(u)),abs=2e-16)
    def eig(stiffness):return np.linalg.eigvals([[(.015-stiffness)/.01,.015/.01],[-1,-1]])
    assert max(eig(.02).real)<0 and max(eig(.003).real)>0
    assert max(eig(.005).real)==pytest.approx(0,abs=1e-15)


def test_gas_piston_adiabat_and_closed_energy_including_external_damper():
    name=slug('adiabatic-');r=run(name);x,v,p,h=matrix(r,model(name));volume=.01+.01*x
    assert min(volume)>0 and min(p)>0
    invariant=p*volume**1.4
    assert invariant==pytest.approx(np.full(len(p),invariant[0]),rel=3e-9)
    energy=.5*v*v+.5*1000*x*x+p*volume/.4+100000*.01*x+h
    assert energy==pytest.approx(np.full(len(p),energy[0]),rel=2e-10,abs=1e-7)
    assert np.all(np.diff(h)>=0) and h[-1]>.4


def test_akzo_algebraic_residual_domain_and_published_endpoint():
    name=slug('akzo-');r=run(name);y=matrix(r,model(name));bound=np.array(r.values['Bound_Complex'])
    assert bound==pytest.approx(115.83*y[0]*y[3],rel=2e-14)
    assert min(y[1])>0
    expected=np.array([.1150794920661702,.001203831471567715,.1611562887407974,.0003656156421249283,.01708010885264404])
    np.testing.assert_allclose(y[:,-1],expected,rtol=5e-8,atol=1e-11)
    assert bound[-1]==pytest.approx(.004873531310307455,rel=5e-8)


def cahn_energy(y):
    y=np.asarray(y)
    return np.sum((y*y-1)**2/4+.05*(np.roll(y,-1,axis=0)-y)**2,axis=0)

def test_cahn_conserved_mass_discrete_energy_and_spinodal_mode():
    name=slug('cahn-');m=model(name);r=run(name);y=matrix(r,m)
    assert np.sum(y,axis=0)==pytest.approx(np.zeros(len(r.time)),abs=3e-13)
    energy=cahn_energy(y)
    assert np.all(np.diff(energy)<=2e-12) and energy[-1]<energy[0]-.1
    assert r.values['Free_Energy']==pytest.approx(energy,abs=2e-14)
    rng=np.random.default_rng(21)
    for _ in range(100):
        state=rng.uniform(-.9,.9,8);mu=state**3-state-.1*(np.roll(state,1)-2*state+np.roll(state,-1))
        deriv=reference(name)(0,state)
        assert np.sum(deriv)==pytest.approx(0,abs=3e-15)
        assert mu@deriv==pytest.approx(-np.sum((np.roll(mu,-1)-mu)**2),abs=5e-14)
    mode=np.cos(2*math.pi*np.arange(8)/8);amplitude=2/8*(mode@y)
    laplace=4*math.sin(math.pi/8)**2;growth=laplace*(1-.1*laplace)
    assert amplitude[10]==pytest.approx(amplitude[0]*math.exp(growth*.1),rel=3e-5)
    assert max(abs(y[:,-1]))>.2


def test_laser_quanta_budget_threshold_and_relaxation():
    name=slug('semiconductor-');m=model(name);r=run(name);n,s,l=matrix(r,m)
    assert n+s+l==pytest.approx(.000001+1500*np.array(r.time),abs=2e-7)
    threshold=10+1/(.05*.02)
    def photon(n):return .02*(1500-.9999*n)
    stationary=brentq(lambda n:(.05*(n-10)-50)*photon(n)+.0001*n,0,threshold)
    assert reference(name)(0,[stationary,photon(stationary),0])[:2]==pytest.approx([0,0],abs=1e-9)
    assert n[-1]==pytest.approx(stationary,rel=.003)
    assert s[-1]==pytest.approx(photon(stationary),rel=.03)
    assert max(s)>2*photon(stationary) and min(n)>=0 and min(s)>0

@pytest.mark.parametrize('prefix',['rayleigh-','lane-','chapman-','gilbert-','lorentz-','kerr-','rate-state-','adiabatic-','cahn-'])
def test_coarse_verification_grid_halving_reduces_reference_error(prefix):
    name=slug(prefix);m=model(name).model_copy(deep=True);m.time_settings.dt*=4
    coarse=simulate(m)
    solution=solve_ivp(reference(name),(m.time_settings.start,m.time_settings.end),[s.initial_value for s in m.stocks],t_eval=coarse.time,method='DOP853',rtol=2e-12,atol=1e-18 if prefix=='lorentz-' else 1e-14)
    assert solution.success;ref=solution.y
    fine=m.model_copy(deep=True);fine.time_settings.dt/=2;fr=simulate(fine)
    indices={round(t,14):i for i,t in enumerate(fr.time)}
    refined=matrix(fr,fine)[:,[indices[round(t,14)] for t in coarse.time]]
    scale=np.maximum(np.max(abs(ref),axis=1),1e-12)[:,None]
    c=np.max(abs(matrix(coarse,m)-ref)/scale);f=np.max(abs(refined-ref)/scale)
    assert f<c*.3


def test_source_metadata_and_no_exact_active_or_staged_duplicate():
    repo=ROOT.parents[1];ids=set();titles=set();equations=set()
    from tests.library_admission import baseline_models
    for d in baseline_models(repo,{model(name).id for name in SLUGS}):
        ids.add(d.get('id'));titles.add(d.get('name','').lower());equations.add(tuple(sorted(f.get('equation','').replace(' ','') for f in d.get('flows',[]))))
    for folder in [repo/'operations']:
        for path in folder.rglob('*.json'):
            if ROOT in path.parents:continue
            try:d=json.loads(path.read_text())
            except (ValueError,UnicodeDecodeError):continue
            if not isinstance(d,dict) or not isinstance(d.get('stocks'),list):continue
            ids.add(d.get('id'));titles.add(d.get('name','').lower());equations.add(tuple(sorted(f.get('equation','').replace(' ','') for f in d.get('flows',[]))))
    assert len(SLUGS)==11 and len(set(SLUGS))==11
    for name in SLUGS:
        m=model(name);assert m.id not in ids and m.name.lower() not in titles
        assert tuple(sorted(f.equation.replace(' ','') for f in m.flows)) not in equations
    assert all(e['parameter_provenance'] and e['rights'] and e['scope'] for e in MANIFEST)


def test_expanded_stock_derivative_duplicate_screen():
    from app.core.equations import preprocess_equation,canonical_name,decode_identifier
    def fingerprint(raw):
        stocks=raw.get('stocks',[]);aliases={canonical_name(s['name']):'STATE_'+str(i) for i,s in enumerate(stocks)}
        variables={canonical_name(v['name']):v.get('equation','0') for v in raw.get('variables',[])}
        class Normalize(ast.NodeTransformer):
            def __init__(self):self.expanding=set()
            def visit_Name(self,node):
                key=canonical_name(decode_identifier(node.id))
                if key in aliases:return ast.Name(id=aliases[key],ctx=ast.Load())
                if key in variables:
                    if key in self.expanding or len(self.expanding)>20:raise ValueError('Recursive variable')
                    self.expanding.add(key);expanded=self.visit(ast.parse(preprocess_equation(variables[key]),mode='eval').body);self.expanding.remove(key);return expanded
                return ast.Name(id=key,ctx=ast.Load())
            def visit_Constant(self,node):return ast.Constant(value=float(node.value)) if type(node.value) in (int,float) else node
        output=[]
        try:
            for s in stocks:
                terms=[]
                for f in raw.get('flows',[]):
                    if f.get('to_stock') in (s.get('id'),s['name']):terms.append('+('+f.get('equation','0')+')')
                    if f.get('from_stock') in (s.get('id'),s['name']):terms.append('-('+f.get('equation','0')+')')
                output.append(ast.dump(Normalize().visit(ast.parse(preprocess_equation(''.join(terms) or '0'),mode='eval')),include_attributes=False))
        except (ValueError,TypeError,KeyError,SyntaxError,RecursionError):return None
        return tuple(output)
    repo=ROOT.parents[1];existing=set()
    from tests.library_admission import baseline_models
    for d in baseline_models(repo,{model(name).id for name in SLUGS}):existing.add(fingerprint(d))
    for folder in [repo/'operations']:
        for path in folder.rglob('*.json'):
            if ROOT in path.parents:continue
            try:d=json.loads(path.read_text())
            except (ValueError,UnicodeDecodeError):continue
            if isinstance(d,dict) and isinstance(d.get('stocks'),list):existing.add(fingerprint(d))
    seen=set()
    for name in SLUGS:
        fp=fingerprint(json.loads((ROOT/(name+'.json')).read_text()));assert fp and fp not in existing and fp not in seen;seen.add(fp)


@pytest.mark.parametrize('prefix',['akzo-','semiconductor-'])
def test_adaptive_tolerance_tightening_against_independent_solver(prefix):
    name=slug(prefix);m=model(name).model_copy(deep=True);m.time_settings.rtol/=10;m.time_settings.atol/=10
    ref=independently_solved(name);scale=np.maximum(np.max(abs(ref),axis=1),1e-12)[:,None]
    coarse=np.max(abs(matrix(run(name),model(name))-ref)/scale)
    fine=np.max(abs(matrix(simulate(m),m)-ref)/scale)
    assert fine<coarse*.5
