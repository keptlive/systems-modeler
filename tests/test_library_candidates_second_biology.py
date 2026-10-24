"""Independent references and physical/biological invariants for review-only candidates."""
import ast,hashlib,json,math
from functools import lru_cache
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.linalg import expm
from scipy.optimize import brentq
from app.core.model import Model
from app.core.simulator import simulate
from app.core.units import analyze_units
from tests.library_admission import baseline_models
ROOT=Path(__file__).resolve().parents[1]/'operations/library-candidates-second-biology'
MANIFEST=json.loads((ROOT/'manifest.json').read_text())
SLUGS=[Path(e['file']).stem for e in MANIFEST]
@lru_cache(None)
def model(slug):return Model.model_validate_json((ROOT/(slug+'.json')).read_text())
@lru_cache(None)
def run(slug):return simulate(model(slug))
def slug(prefix):return next(s for s in SLUGS if s.startswith(prefix))
def matrix(result,m):return np.array([result.values[s.name] for s in m.stocks])

def reference(name):
    if name.startswith('tyson-'):
        def rhs(t,y):
            c,cp,pm,m,cy,yp=y;ct=c+cp+pm+m;binding=200/ct*cp*cy;act=(.018+180*(m/ct)**2)*pm
            return [m+100*cp-100*c,100*c-100*cp-binding,binding-act,act-m,.015*ct-binding,m-.6*yp]
        return rhs
    if name.startswith('li-rinzel-'):
        def rhs(t,y):
            c,h=y;opening=(.6/.8)**3*(c/(c+.4))**3*h**3
            return [(40*opening+.02)*(2-1.185*c)-.6*c*c/(.18**2+c*c),.4-h*(c+.4)]
        return rhs
    if name.startswith('vilar-'):
        def rhs(t,y):
            da,dab,dr,drb,ma,a,mr,r,c=y
            ba=da*a;bb=dr*a;sequester=2*a*r
            return [50*dab-ba,ba-50*dab,100*drb-bb,bb-100*drb,500*dab+50*da-10*ma,50*ma+50*dab+100*drb-ba-bb-sequester-a,50*drb+.01*dr-.5*mr,5*mr-sequester+c-.2*r,sequester-c]
        return rhs
    if name.startswith('schlogl-'):return lambda t,y:[3*y[0]**2-.6*y[0]**3+.25-2.95*y[0]]
    if name.startswith('becker-'):
        def rhs(t,y):
            j=[y[0]*y[i]-.1*y[i+1] for i in range(4)]
            return [-2*j[0]-sum(j[1:]),j[0]-j[1],j[1]-j[2],j[2]-j[3],j[3]]
        return rhs
    if name.startswith('competitive-'):
        def rhs(t,y):
            s,e,i,c,p,ci=y;a=2*s*e-.5*c;b=5*i*e-.1*ci;v=.4*c
            return [-a,-a+v-b,-b,a-v,v,b]
        return rhs
    if name.startswith('kirschner-'):
        def rhs(t,y):
            e,tum,i=y
            return [.02*tum-.03*e+.1245*e*i/(20+i),.18*(1-.001*tum)*tum-e*tum/(10+tum),.5*e*tum/(10+tum)-10*i]
        return rhs
    if name.startswith('bacterial-'):return lambda t,y:persister_matrix()@y
    if name.startswith('frank-'):
        def rhs(t,y):
            a,r,l,d=y;cross=10*r*l
            return [-a*(r+l),a*r-cross,a*l-cross,cross]
        return rhs
    if name.startswith('chemotaxis-'):
        def rhs(t,y):
            activity=1/(1+math.exp(6*(2*(1-y[0])+math.log(10))))
            return [.01-.03*activity]
        return rhs
    raise AssertionError(name)
def persister_matrix():return np.array([[-4-.0000012,.1],[.0000012,-.5]])
@lru_cache(None)
def independently_solved(name):
    m=model(name);r=run(name)
    # LSODA is an independent stiffness-aware algorithm; avoids millions of
    # explicit reference steps in the promoter-binding and cdc2 benchmarks.
    method='LSODA' if name.startswith(('vilar-','tyson-')) else 'DOP853'
    ref=solve_ivp(reference(name),(0,m.time_settings.end),[s.initial_value for s in m.stocks],method=method,t_eval=r.time,rtol=2e-11,atol=1e-27 if name.startswith('kirschner-') else 1e-14)
    assert ref.success
    return ref.y

@pytest.mark.parametrize('name',SLUGS)
def test_default_full_series_against_independent_equations_and_units(name):
    m=model(name);r=run(name);actual=matrix(r,m);expected=independently_solved(name)
    assert analyze_units(m)['status']=='consistent'
    assert np.isfinite(actual).all()
    for a,e in zip(actual,expected):
        np.testing.assert_allclose(a,e,rtol=5e-6,atol=2e-8*max(np.max(abs(e)),1e-8))
        assert np.ptp(a)>1e-10
        assert min(a)>-1e-9
    assert m.source.startswith('https://') and m.reference
    assert 'not fitted' in m.description
    assert len(r.time)<=10001
    if r.integration_diagnostics:assert r.integration_diagnostics['work_units']<1_000_000


def test_tyson_cdc2_conservation_and_activation_feedback():
    name=slug('tyson-');m=model(name);y=matrix(run(name),m)
    assert np.sum(y[:4],axis=0)==pytest.approx(.004,abs=2e-13)
    assert np.max(y[3])<.004+1e-12
    # Positive MPF stimulates conversion of the *same* preMPF pool; cdc2 is
    # repartitioned, not synthesized by the nonlinear activation reaction.
    for q in [.1,.2,.3]:
        state=[.001,.001,.001,.001,.002,.003];state[3]=q*.004
        assert sum(reference(name)(0,state)[:4])==pytest.approx(0,abs=1e-15)


def test_calcium_closed_store_and_inactivation_domain():
    name=slug('li-rinzel-');r=run(name);c=np.array(r.values['Cytosolic_Calcium']);h=np.array(r.values['Available_Receptors'])
    assert min(c)>=0 and max(c)<=2/1.185
    assert min(h)>=0 and max(h)<=1
    er=(2-c)/.185
    assert c+.185*er==pytest.approx(2,abs=1e-14)
    assert reference(name)(0,[0,0])[0]>.0
    assert reference(name)(0,[2/1.185,.8])[0]<0
    assert reference(name)(0,[.3,0])[1]>0
    assert reference(name)(0,[.3,1])[1]<0


def test_vilar_promoter_copies_and_repeated_deterministic_cycles():
    name=slug('vilar-');r=run(name);y=matrix(r,model(name))
    assert y[0]+y[1]==pytest.approx(1,abs=3e-11)
    assert y[2]+y[3]==pytest.approx(1,abs=3e-11)
    assert max(y[1])<=1+1e-10 and max(y[3])<=1+1e-10
    from scipy.signal import find_peaks
    peaks,_=find_peaks(y[7],prominence=100)
    assert len(peaks)>=2
    assert all(15<interval<35 for interval in np.diff(np.array(r.time)[peaks]))


def test_schlogl_three_roots_basin_selection_and_no_stochastic_switching():
    name=slug('schlogl-');roots=np.sort(np.roots([-.6,3,-2.95,.25]))
    assert all(np.isreal(roots)) and min(roots)>0
    derivative=lambda x:6*x-1.8*x*x-2.95
    assert derivative(roots[0])<0 and derivative(roots[1])>0 and derivative(roots[2])<0
    assert run(name).values['Autocatalyst'][-1]==pytest.approx(roots[0],rel=1e-6)
    upper=model(name).model_copy(deep=True);upper.stocks[0].initial_value=float(roots[1]+.1)
    assert simulate(upper).values['Autocatalyst'][-1]==pytest.approx(roots[2],rel=1e-6)


def test_becker_doring_monomer_budget_and_detailed_balance():
    name=slug('becker-');y=matrix(run(name),model(name));weights=np.arange(1,6)
    assert weights@y==pytest.approx(np.ones(y.shape[1]),abs=3e-13)
    monomer=brentq(lambda z:sum(n*z**n/.1**(n-1) for n in range(1,6))-1,0,1)
    target=np.array([monomer**n/.1**(n-1) for n in range(1,6)])
    assert reference(name)(0,target)==pytest.approx(np.zeros(5),abs=1e-14)
    np.testing.assert_allclose(y[:,-1],target,rtol=.02,atol=1e-4)


def test_competitive_inhibition_three_moieties_and_control():
    name=slug('competitive-');y=matrix(run(name),model(name))
    assert y[0]+y[3]+y[4]==pytest.approx(2,abs=3e-13)
    assert y[1]+y[3]+y[5]==pytest.approx(.1,abs=3e-14)
    assert y[2]+y[5]==pytest.approx(.4,abs=3e-14)
    uninhibited=model(name).model_copy(deep=True);uninhibited.stocks[2].initial_value=0
    control=simulate(uninhibited)
    assert run(name).values['Product'][1000]<control.values['Product'][1000]*.6
    assert np.all(np.diff(y[4])>=-1e-13)


def test_kirschner_tumor_free_invariant_and_tumor_upper_bound():
    name=slug('kirschner-');r=run(name)
    assert max(r.values['Tumor'])<=1000
    assert max(r.values['IL2'])>0
    empty=model(name).model_copy(deep=True);empty.stocks[1].initial_value=0
    absent=simulate(empty)
    assert absent.values['Tumor']==pytest.approx(np.zeros(len(absent.time)),abs=1e-14)
    assert absent.values['IL2']==pytest.approx(np.zeros(len(absent.time)),abs=1e-14)
    assert absent.values['Effectors']==pytest.approx(np.exp(-.03*np.array(absent.time)),rel=2e-7,abs=1e-10)


def test_persister_every_point_matches_matrix_exponential_and_slow_tail():
    name=slug('bacterial-');m=model(name);r=run(name);initial=np.array([.9999994,.0000006])
    y=matrix(r,m)
    expected=np.array([expm(persister_matrix()*t)@initial for t in r.time]).T
    np.testing.assert_allclose(y,expected,rtol=3e-8,atol=1e-15)
    total=y.sum(axis=0)
    assert np.all(np.diff(total)<0)
    assert total[-1]>math.exp(-4*8)*10000
    assert y[1,-1]/total[-1]>.9
    assert -math.log(total[-1]/total[-501])/(r.time[-1]-r.time[-501])<.6


def test_frank_mass_stoichiometry_handedness_and_symmetric_control():
    name=slug('frank-');m=model(name);r=run(name);y=matrix(r,m)
    assert y[0]+y[1]+y[2]+2*y[3]==pytest.approx(1.02001,abs=4e-13)
    ee=(y[1]-y[2])/(y[1]+y[2])
    assert np.all(np.diff(ee)>=-1e-12) and ee[-1]>ee[0]*20
    symmetric=m.model_copy(deep=True);symmetric.stocks[1].initial_value=.01
    same=simulate(symmetric)
    assert same.values['Right_Enantiomer']==pytest.approx(same.values['Left_Enantiomer'],abs=1e-13)


def test_chemotaxis_activity_recovers_same_setpoint_across_ligands():
    name=slug('chemotaxis-');base=model(name)
    for ligand in [1,10,100]:
        modified=base.model_copy(deep=True)
        next(v for v in modified.variables if v.name=='ligand').equation=str(ligand)
        r=simulate(modified)
        assert r.values['Receptor_Activity'][-1]==pytest.approx(1/3,abs=1e-5)
        expected=1+(math.log((1+ligand)/(1+ligand/100))-math.log(2)/6)/2
        assert r.values['Methylation'][-1]==pytest.approx(expected,abs=1e-5)
        assert 0<min(r.values['Receptor_Activity'])<=max(r.values['Receptor_Activity'])<1

@pytest.mark.parametrize('prefix',['schlogl-','competitive-','bacterial-','chemotaxis-'])
def test_independent_refinement_decreases_error(prefix):
    name=slug(prefix);base=model(name);m=base.model_copy(deep=True)
    factor=1 if prefix=='competitive-' else 8
    m.time_settings.dt*=factor;r=simulate(m);ref=independently_solved(name)[:,::factor]
    refined=m.model_copy(deep=True);refined.time_settings.dt/=2
    finer=matrix(simulate(refined),refined)[:,::2]
    scale=np.maximum(np.max(abs(ref),axis=1),1e-10)[:,None]
    coarse=np.max(abs(matrix(r,m)-ref)/scale);fine=np.max(abs(finer-ref)/scale)
    assert fine<coarse*.3


def test_distinct_identity_and_semantic_inventory_against_active_and_staged_models():
    repo=ROOT.parents[1];ids=set();names=set();equations=set()
    for d in baseline_models(repo,{model(name).id for name in SLUGS}):
        ids.add(d.get('id'));names.add(d.get('name'))
        equations.add(tuple(sorted(f.get('equation','').replace(' ','') for f in d.get('flows',[]))))
    for tree in [repo/'operations']:
        for p in tree.rglob('*.json'):
            if ROOT in p.parents:continue
            try:d=json.loads(p.read_text())
            except (ValueError,UnicodeDecodeError):continue
            if not isinstance(d,dict) or not isinstance(d.get('stocks'),list):continue
            ids.add(d.get('id'));names.add(d.get('name'))
            equations.add(tuple(sorted(f.get('equation','').replace(' ','') for f in d.get('flows',[]))))
    assert len(SLUGS)==10 and len(set(SLUGS))==10
    for name in SLUGS:
        m=model(name)
        assert m.id not in ids and m.name not in names
        assert tuple(sorted(f.equation.replace(' ','') for f in m.flows)) not in equations
    assert all(e['parameter_provenance'] and e['license'] for e in MANIFEST)

def test_conservative_alpha_normalized_derivative_screen():
    from app.core.equations import preprocess_equation,canonical_name,decode_identifier
    def fingerprint(raw):
        stocks=raw.get('stocks',[])
        aliases={canonical_name(s['name']):'STATE_'+str(i) for i,s in enumerate(stocks)}
        variables={canonical_name(v['name']):v.get('equation','0') for v in raw.get('variables',[])}
        class Normalize(ast.NodeTransformer):
            def __init__(self):self.expanding=set()
            def visit_Name(self,node):
                key=canonical_name(decode_identifier(node.id))
                if key in aliases:return ast.Name(id=aliases[key],ctx=ast.Load())
                if key in variables:
                    if key in self.expanding or len(self.expanding)>20:raise ValueError('Recursive variable')
                    self.expanding.add(key)
                    expanded=self.visit(ast.parse(preprocess_equation(variables[key]),mode='eval').body)
                    self.expanding.remove(key)
                    return expanded
                return ast.Name(id=key,ctx=ast.Load())
            def visit_Constant(self,node):
                return ast.Constant(value=float(node.value)) if type(node.value) in (int,float) else node
        output=[]
        try:
            for stock in stocks:
                terms=[]
                for flow in raw.get('flows',[]):
                    if flow.get('to_stock') in (stock.get('id'),stock['name']):terms.append('+('+flow.get('equation','0')+')')
                    if flow.get('from_stock') in (stock.get('id'),stock['name']):terms.append('-('+flow.get('equation','0')+')')
                tree=Normalize().visit(ast.parse(preprocess_equation(''.join(terms) or '0'),mode='eval'))
                output.append(ast.dump(tree,include_attributes=False))
        except (ValueError,TypeError,KeyError,SyntaxError,RecursionError):return None
        return tuple(output)
    repo=ROOT.parents[1];existing=set()
    for raw in baseline_models(repo,{model(name).id for name in SLUGS}):
        existing.add(fingerprint(raw))
    for folder in [repo/'operations']:
        for path in folder.rglob('*.json'):
            if ROOT in path.parents:continue
            try:raw=json.loads(path.read_text())
            except (ValueError,UnicodeDecodeError):continue
            if isinstance(raw,dict) and isinstance(raw.get('stocks'),list):existing.add(fingerprint(raw))
    seen=set()
    for name in SLUGS:
        value=fingerprint(json.loads((ROOT/(name+'.json')).read_text()))
        assert value and value not in existing and value not in seen
        seen.add(value)
