"""Source and numerical evidence for admitted and deferred mechanistic examples."""
from tests.library_admission import baseline_models
import hashlib,json,math
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from app.core.model import Model
from app.core.simulator import simulate
from app.core.validation import inspect_inputs
from app.core.units import analyze_units
ROOT=Path(__file__).parents[1]
CANDIDATES=ROOT/'operations/library-candidates'
MANIFEST=json.loads((CANDIDATES/'MANIFEST.json').read_text())['candidates']

def reference_rhs(key):
    if key=='thomas-cyclic-sine':return lambda t,u:[math.sin(u[1])-.208186*u[0],math.sin(u[2])-.208186*u[1],math.sin(u[0])-.208186*u[2]]
    if key=='dadras-quadratic-flow':return lambda t,u:[u[1]-3*u[0]+2.7*u[1]*u[2],1.7*u[1]-u[0]*u[2]+u[2],2*u[0]*u[1]-9*u[2]]
    if key=='chen-three-state':return lambda t,u:[35*(u[1]-u[0]),-7*u[0]-u[0]*u[2]+28*u[1],u[0]*u[1]-3*u[2]]
    if key=='rossler-three-state':return lambda t,u:[-u[1]-u[2],u[0]+.2*u[1],.2+u[2]*(u[0]-5.7)]
    if key=='hindmarsh-rose-source':return lambda t,u:[u[1]-u[0]**3+3*u[0]**2-u[2]+5,1-5*u[0]**2-u[1],.01*(4*(u[0]+1.6)-u[2])]
    if key=='nonlinear-sequential-chemistry':return lambda t,u:[-u[0],u[0]-u[1]**2,u[1]**2]
    if key=='euler-rigid-body':return lambda t,u:[-2*u[1]*u[2],1.25*u[0]*u[2],-.5*u[0]*u[1]]
    if key=='robertson-autocatalytic':
        def rhs(t,u):
            a=.04*u[0];b=3e7*u[1]*u[1];c=1e4*u[1]*u[2]
            return [-a+c,a-b-c,b]
        return rhs
    if key=='hires-photomorphogenesis':return lambda t,u:[-1.71*u[0]+.43*u[1]+8.32*u[2]+.0007,1.71*u[0]-8.75*u[1],-10.03*u[2]+.43*u[3]+.035*u[4],8.32*u[1]+1.71*u[2]-1.12*u[3],-1.745*u[4]+.43*u[5]+.43*u[6],-280*u[5]*u[7]+.69*u[3]+1.71*u[4]-.43*u[5]+.69*u[6],280*u[5]*u[7]-1.81*u[6],-280*u[5]*u[7]+1.81*u[6]]
    if key=='pleiades-seven-body':
        def rhs(t,u):
            position=np.array(u[:14]).reshape(2,7);delta=position[:,None,:]-position[:,:,None]
            squared=np.sum(delta**2,axis=0);np.fill_diagonal(squared,1)
            force=delta/ squared[None,:,:]**1.5
            for i in range(7):force[:,i,i]=0
            acceleration=np.sum(force*np.arange(1,8)[None,None,:],axis=2)
            return np.concatenate((u[14:],acceleration.ravel()))
        return rhs
    raise AssertionError(key)

@pytest.mark.parametrize('entry',MANIFEST,ids=lambda e:e['file'])
def test_complete_default_against_independent_ode_and_admission(entry):
    raw=json.loads((CANDIDATES/entry['file']).read_text());model=Model(**raw)
    result=simulate(model);actual=np.array([result.values[s.name] for s in model.stocks])
    assert np.isfinite(actual).all()
    method='BDF' if model.time_settings.integration_method=='radau' else 'DOP853'
    ref=solve_ivp(reference_rhs(Path(entry['file']).stem),(0,model.time_settings.end),[s.initial_value for s in model.stocks],t_eval=result.time,method=method,rtol=2e-11,atol=1e-13)
    assert ref.success
    # Our Radau defaults are1e-6 relative/1e-9 absolute, independent reference tighter.
    np.testing.assert_allclose(actual,ref.y,rtol=3e-4,atol=2e-5)
    assert any(np.ptp(row)>1e-7 for row in actual)
    report=inspect_inputs(model,numerical_check=False)
    assert report['valid'],report['issues']
    units=analyze_units(model)
    assert not units['errors'],units


def test_source_hashes_licenses_and_no_active_duplicate_ids():
    active=baseline_models(ROOT, {entry['id'] for entry in MANIFEST})
    active_ids={m['id'] for m in active}
    def fingerprint(model):
        return tuple(sorted(s.get('equation','').replace(' ','').lower() for s in model.get('flows',[])))
    active_fingerprints={fingerprint(m) for m in active}
    fingerprints=[]
    for entry in MANIFEST:
        assert entry['license']=='MIT' and entry['id'] not in active_ids
        source=CANDIDATES/'sources'/entry['source_url'].split('/')[-1]
        assert hashlib.sha256(source.read_bytes()).hexdigest()==entry['source_file_sha256']
        fp=fingerprint(json.loads((CANDIDATES/entry['file']).read_text()))
        assert fp not in active_fingerprints and fp not in fingerprints
        fingerprints.append(fp)
    assert 'Permission is hereby granted' in (CANDIDATES/'sources/LICENSE.md').read_text()


def test_conserved_masses_and_rigid_body_invariants():
    for key in ['nonlinear-sequential-chemistry','robertson-autocatalytic']:
        m=Model(**json.loads((CANDIDATES/(key+'.json')).read_text()));r=simulate(m)
        np.testing.assert_allclose(np.sum([r.values[s.name] for s in m.stocks],axis=0),1,atol=1e-8)
    m=Model(**json.loads((CANDIDATES/'hires-photomorphogenesis.json').read_text()));r=simulate(m)
    np.testing.assert_allclose(np.array(r.values['U7'])+r.values['U8'],.0057,atol=1e-10)
    m=Model(**json.loads((CANDIDATES/'euler-rigid-body.json').read_text()));r=simulate(m)
    x,y,z=[np.array(r.values[n]) for n in ['X','Y','Z']]
    np.testing.assert_allclose(1.25*x*x+2*y*y,1.25,atol=1e-7)
    np.testing.assert_allclose(.5*x*x-2*z*z,.5-2*.9**2,atol=1e-7)

@pytest.mark.parametrize('key',['nonlinear-sequential-chemistry','euler-rigid-body','chen-three-state','hindmarsh-rose-source'])
def test_step_halving_reduces_full_series_error(key):
    m=Model(**json.loads((CANDIDATES/(key+'.json')).read_text()))
    if key=='hindmarsh-rose-source':m.time_settings=m.time_settings.model_copy(update={'dt':.008})
    coarse=simulate(m)
    m.time_settings=m.time_settings.model_copy(update={'dt':m.time_settings.dt/2});fine=simulate(m)
    ref=solve_ivp(reference_rhs(key),(0,m.time_settings.end),[s.initial_value for s in m.stocks],t_eval=coarse.time,method='DOP853',rtol=2e-12,atol=1e-14)
    a=np.array([coarse.values[s.name] for s in m.stocks]);b=np.array([fine.values[s.name][::2] for s in m.stocks])
    assert np.max(abs(b-ref.y)) < np.max(abs(a-ref.y))/8


def test_nonlinear_chemistry_bessel_closed_form():
    from scipy.special import iv,kv
    m=Model(**json.loads((CANDIDATES/'nonlinear-sequential-chemistry.json').read_text()));r=simulate(m)
    t=np.array(r.time);q=np.exp(-t/2);ratio=kv(1,2)/iv(1,2)
    a=np.exp(-t);b=q*(kv(1,2*q)-ratio*iv(1,2*q))/(kv(0,2*q)+ratio*iv(0,2*q))
    np.testing.assert_allclose(r.values['A'],a,rtol=1e-7,atol=1e-9)
    np.testing.assert_allclose(r.values['B'],b,rtol=1e-7,atol=1e-8)
    np.testing.assert_allclose(r.values['C'],1-a-b,rtol=1e-7,atol=1e-8)


def test_pleiades_linear_momentum_and_center_of_mass():
    m=Model(**json.loads((CANDIDATES/'pleiades-seven-body.json').read_text()));r=simulate(m)
    masses=np.arange(1,8)
    for coordinate,velocity in [('X','VX'),('Y','VY')]:
        positions=np.array([r.values[f'{coordinate}{i}'] for i in range(1,8)])
        velocities=np.array([r.values[f'{velocity}{i}'] for i in range(1,8)])
        momentum=masses@velocities
        np.testing.assert_allclose(momentum,momentum[0],atol=1e-8)
        barycenter=masses@positions
        np.testing.assert_allclose(barycenter,barycenter[0]+momentum[0]*np.array(r.time),atol=1e-8)


def test_canonical_stock_derivative_fingerprints_do_not_duplicate_active_models():
    """Conservative alpha-normalization; not a proof of algebraic inequivalence."""
    import ast
    from app.core.equations import canonical_name,decode_identifier,preprocess_equation
    def fingerprint(raw):
        stocks=raw.get('stocks',[])
        aliases={canonical_name(s['name']):f'S{i}' for i,s in enumerate(stocks)}
        constants={}
        for v in raw.get('variables',[]):
            try:constants[canonical_name(v['name'])]=float(v.get('equation',''))
            except (TypeError,ValueError):pass
        class Rename(ast.NodeTransformer):
            def visit_Name(self,node):
                name=canonical_name(decode_identifier(node.id))
                if name in aliases:return ast.Name(id=aliases[name],ctx=ast.Load())
                if name in constants:return ast.Constant(value=constants[name])
                return ast.Name(id=name,ctx=ast.Load())
        derivatives=[]
        for stock in stocks:
            refs={stock['name'],stock.get('id')};terms=[]
            for flow in raw.get('flows',[]):
                if flow.get('to_stock') in refs:terms.append('+('+flow.get('equation','0')+')')
                if flow.get('from_stock') in refs:terms.append('-('+flow.get('equation','0')+')')
            try:derivatives.append(ast.dump(Rename().visit(ast.parse(preprocess_equation(''.join(terms) or '0'),mode='eval')),include_attributes=False))
            except (ValueError,SyntaxError,RecursionError):return None
        return tuple(derivatives)
    active={fingerprint(raw) for raw in baseline_models(ROOT, {entry['id'] for entry in MANIFEST})}
    seen=set()
    for entry in MANIFEST:
        fp=fingerprint(json.loads((CANDIDATES/entry['file']).read_text()))
        assert fp and fp not in active and fp not in seen
        seen.add(fp)
