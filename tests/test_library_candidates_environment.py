from tests.library_admission import baseline_models
"""Source-law candidates checked against independent equations and process budgets."""
import json,math
from functools import lru_cache
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp,simpson
from scipy.linalg import expm
from scipy.optimize import brentq
from app.core.model import Model
from app.core.simulator import simulate
from app.core.units import analyze_units
ROOT=Path(__file__).resolve().parents[1]/'operations/library-candidates-environment'
MANIFEST=json.loads((ROOT/'manifest.json').read_text())
SLUGS=[Path(e['file']).stem for e in MANIFEST]
@lru_cache(None)
def model(slug):return Model.model_validate_json((ROOT/(slug+'.json')).read_text())
@lru_cache(None)
def run(slug):return simulate(model(slug))

def reference(slug):
    if slug.startswith('green-ampt-'):return lambda t,y:[.005*(1+.03/y[0])]
    if slug.startswith('streeter-'):return lambda t,y:[-.2*y[0],.2*y[0]-.5*y[1]]
    if slug.startswith('rietkerk-'):
        def rhs(t,y):
            p,w,o=y;uptake=.05*w/(w+5)*p;infil=.2*o*(p+1)/(p+5)
            return [10*uptake-.25*p,infil-uptake-.2*w,1.5-infil]
        return rhs
    if slug.startswith('competitive-'):
        def rhs(t,y):
            a,b,qa,qb=y;vacancy=1-qa-qb
            ra=2*a*vacancy-.1*qa;rb=.5*b*vacancy-.05*qb
            return [-ra,-rb,ra,rb]
        return rhs
    if slug.startswith('shrinking-'):
        return lambda t,y:[-(.005-y[1])/2500,4*math.pi*y[0]**2*(.005-y[1])/.001]
    if slug.startswith('paired-'):
        return lambda t,y:[.005,4000*math.exp(-y[0]/.6)-math.log(2)/1387*y[1],27000*math.exp(-y[0]/.6)-math.log(2)/705*y[2]]
    if slug.startswith('uranium-'):
        a,b,c=[math.log(2)/h for h in [4468000000,245620,75584]]
        return lambda t,y:[-a*y[0],a*y[0]-b*y[1],b*y[1]-c*y[2],c*y[2]]
    if slug.startswith('ekman-'):
        a,b=ekman_matrix()
        return lambda t,y:a@np.array(y)+b
    if slug.startswith('glen-'):return lambda t,y:[.3-(.3/150**5)*y[0]**5]
    if slug.startswith('dupuit-'):
        def rhs(t,y):
            h1,h2,total=y;q12=(h1*h1-h2*h2)/2000;qout=h2*h2/2000
            return [(.01-q12)/200,(q12-qout)/200,qout]
        return rhs
    raise AssertionError(slug)

def ekman_matrix():
    a=np.zeros((6,6));b=np.zeros(6);b[0]=.02
    for layer in range(3):
        i=2*layer;a[i,i+1]=.36;a[i+1,i]=-.36
        for component in range(2):
            row=i+component
            for neighbor in [layer-1,layer+1]:
                if 0<=neighbor<3:
                    a[row,2*neighbor+component]+=.1;a[row,row]-=.1
            if layer==2:a[row,row]-=.1
    return a,b

@pytest.mark.parametrize('slug',SLUGS)
def test_complete_default_independent_reference_units_and_metadata(slug):
    m=model(slug);r=run(slug)
    assert analyze_units(m)['status']=='consistent'
    assert m.source.startswith('https://') and m.reference
    assert 'illustrative' in m.description.lower() or 'our' in m.description.lower()
    assert len(m.flows)==len(m.stocks)>0
    ref=solve_ivp(reference(slug),(0,m.time_settings.end),[s.initial_value for s in m.stocks],method='DOP853',t_eval=r.time,rtol=2e-11,atol=1e-14)
    assert ref.success
    actual=np.array([r.values[s.name] for s in m.stocks])
    assert np.isfinite(actual).all()
    for row,expected in zip(actual,ref.y):
        assert np.ptp(row)>1e-8
        np.testing.assert_allclose(row,expected,rtol=3e-6,atol=1e-8*max(np.max(abs(expected)),1e-6))
    signed=next(e['signed_states'] for e in MANIFEST if e['file']==slug+'.json')
    for stock in m.stocks:
        if stock.name not in signed:assert min(r.values[stock.name])>=-1e-10


def test_green_ampt_integrated_implicit_solution_and_monotone_capacity():
    slug='green-ampt-ponded-infiltration-environment';r=run(slug)
    for t,f in zip(r.time,r.values['Cumulative_Infiltration']):
        expected=.001 if t==0 else brentq(lambda x:x-.001-.03*math.log((x+.03)/.031)-.005*t,.001,1,xtol=1e-14)
        assert f==pytest.approx(expected,rel=2e-8,abs=1e-11)
    f=np.array(r.values['Cumulative_Infiltration']);capacity=.005*(1+.03/f)
    assert np.all(np.diff(f)>0) and np.all(np.diff(capacity)<0)
    assert capacity[-1]>.005


def test_streeter_phelps_closed_form_oxygen_sag_and_natural_rate_convention():
    r=run('streeter-phelps-river-sag-environment');t=np.array(r.time)
    l=20*np.exp(-.2*t);d=(.2*20/(.5-.2))*(np.exp(-.2*t)-np.exp(-.5*t))+np.exp(-.5*t)
    assert r.values['Oxygen_Demand']==pytest.approx(l,rel=2e-10)
    assert r.values['Oxygen_Deficit']==pytest.approx(d,rel=2e-9)
    assert r.values['Dissolved_Oxygen']==pytest.approx(9-d,rel=1e-9)
    critical=math.log((.5/.2)*(1-1*(.5-.2)/(.2*20)))/(.5-.2)
    assert abs(r.time[int(np.argmax(d))]-critical)<.011
    assert min(r.values['Dissolved_Oxygen'])>0


def test_rietkerk_homogeneous_equilibrium_and_water_use_budget():
    slug='rietkerk-homogeneous-water-vegetation-environment';r=run(slug)
    target=[20,5,1.5/(.2*21/25)]
    assert reference(slug)(0,target)==pytest.approx([0,0,0],abs=1e-14)
    assert [r.values[s.name][-1] for s in model(slug).stocks]==pytest.approx(target,abs=2e-5)
    p=np.array(r.values['Vegetation']);w=np.array(r.values['Soil_Water']);o=np.array(r.values['Surface_Water'])
    # Mathematical converted-water budget: death is a loss, not unmodeled recycling.
    loss=simpson(.2*w+.025*p,x=r.time)
    assert w[-1]+o[-1]+p[-1]/10 == pytest.approx(4+2+.5+1.5*500-loss,abs=.0001)


def test_competitive_sorption_two_totals_shared_site_bound_and_equilibrium():
    r=run('competitive-langmuir-closed-sorption-environment').values
    a,b,qa,qb=[np.array(r[n]) for n in ['Dissolved_A','Dissolved_B','Sorbed_A','Sorbed_B']]
    assert a+qa==pytest.approx(np.full(len(a),2),abs=2e-13)
    assert b+qb==pytest.approx(np.full(len(a),1),abs=2e-13)
    assert np.max(qa+qb)<=1
    # Equilibrium is solved from total inventories and shared vacancy, independently.
    vacancy=brentq(lambda v:2*(20*v)/(1+20*v)+(10*v)/(1+10*v)+v-1,0,1)
    expected_a=2*20*vacancy/(1+20*vacancy);expected_b=10*vacancy/(1+10*vacancy)
    assert [qa[-1],qb[-1]]==pytest.approx([expected_a,expected_b],abs=2e-4)


def test_mineral_geometry_mass_conservation_and_partial_saturation():
    r=run('shrinking-mineral-dissolution-environment').values
    radius=np.array(r['Particle_Radius']);c=np.array(r['Dissolved_Concentration'])
    total=.001*c+4*math.pi*2500*radius**3/3
    assert total==pytest.approx(np.full(len(c),4*math.pi*2500*.001**3/3),rel=2e-10,abs=1e-14)
    equilibrium=(.001**3-3*.001*.005/(4*math.pi*2500))**(1/3)
    assert radius[-1]>0 and radius[-1]==pytest.approx(equilibrium,rel=3e-5)
    assert c[-1]<.005 and np.all(np.diff(radius)<0)


def test_cosmogenic_burial_exact_exponential_production_and_peak_order():
    r=run('paired-cosmogenic-burial-environment');t=np.array(r.time);beta=.005/.6
    for name,p,halflife in [('Beryllium_10',4000,1387),('Aluminium_26',27000,705)]:
        decay=math.log(2)/halflife
        expected=p*(np.exp(-beta*t)-np.exp(-decay*t))/(decay-beta)
        assert r.values[name]==pytest.approx(expected,rel=2e-9,abs=1e-6)
    assert np.argmax(r.values['Aluminium_26'])<np.argmax(r.values['Beryllium_10'])
    assert r.values['Depth']==pytest.approx(.005*t,abs=1e-12)


def test_uranium_series_exact_matrix_and_lineage_not_mass_conservation():
    r=run('uranium-series-lineage-disequilibrium-environment')
    a,b,c=[math.log(2)/h for h in [4468000000,245620,75584]]
    matrix=np.array([[-a,0,0,0],[a,-b,0,0],[0,b,-c,0],[0,0,c,0]])
    for index in range(0,len(r.time),10):
        expected=expm(matrix*r.time[index])@np.array([1,0,0,0])
        actual=[r.values[s.name][index] for s in model('uranium-series-lineage-disequilibrium-environment').stocks]
        assert actual==pytest.approx(expected,rel=2e-10,abs=2e-14)
    total=np.sum([r.values[s.name] for s in model('uranium-series-lineage-disequilibrium-environment').stocks],axis=0)
    assert total==pytest.approx(np.ones(len(total)),abs=3e-15)
    activity_ratio=b*r.values['Uranium_234'][-1]/(a*r.values['Uranium_238'][-1])
    assert .93<activity_ratio<1


def test_ekman_matrix_solution_column_momentum_and_shear_dissipation():
    slug='ekman-three-layer-momentum-environment';r=run(slug);a,b=ekman_matrix()
    augmented=np.zeros((7,7));augmented[:6,:6]=a;augmented[:6,6]=b
    assert max(np.linalg.eigvals(a).real)<0
    for index in range(0,len(r.time),20):
        expected=(expm(augmented*r.time[index])@np.array([0,0,0,0,0,0,1]))[:6]
        actual=np.array([r.values[s.name][index] for s in model(slug).stocks])
        assert actual==pytest.approx(expected,abs=1e-9)
    y=np.array([.03,-.04,.01,.02,-.02,.01]);dy=a@y+b
    assert dy[::2].sum()==pytest.approx(.36*y[1::2].sum()+.02-.1*y[4])
    assert dy[1::2].sum()==pytest.approx(-.36*y[::2].sum()-.1*y[5])
    diss=.1*((y[0]-y[2])**2+(y[2]-y[4])**2+(y[1]-y[3])**2+(y[3]-y[5])**2)+.1*(y[4]**2+y[5]**2)
    assert y@dy==pytest.approx(.02*y[0]-diss)


def test_glen_outlet_fifth_power_equilibrium_and_invariant_interval():
    r=run('glen-fixed-slope-ice-outlet-environment').values['Ice_Thickness']
    assert reference('glen-fixed-slope-ice-outlet-environment')(0,[150])==pytest.approx([0],abs=1e-15)
    assert all(80<=h<=150+1e-10 for h in r)
    assert np.all(np.diff(r)>0)
    assert r[-1]==pytest.approx(150,abs=.0001)


def test_dupuit_storage_discharge_balance_and_quasi_steady_equilibrium():
    slug='dupuit-two-cell-aquifer-environment';r=run(slug)
    h1=np.array(r.values['Upgradient_Head']);h2=np.array(r.values['Downstream_Head']);discharge=np.array(r.values['River_Discharge'])
    assert 200*(h1+h2)+discharge==pytest.approx(4000+.01*np.array(r.time),abs=2e-9)
    assert np.all(h1>h2) and np.all(h2>0)
    equilibrium=[math.sqrt(40),math.sqrt(20),0]
    assert reference(slug)(0,equilibrium)[:2]==pytest.approx([0,0],abs=1e-16)

@pytest.mark.parametrize('slug',['streeter-phelps-river-sag-environment','competitive-langmuir-closed-sorption-environment','ekman-three-layer-momentum-environment','glen-fixed-slope-ice-outlet-environment'])
def test_fixed_step_refinement(slug):
    m=model(slug);coarse=run(slug);fine=simulate(m,m.time_settings.model_copy(update={'dt':m.time_settings.dt/2}))
    ref=solve_ivp(reference(slug),(0,m.time_settings.end),[s.initial_value for s in m.stocks],method='DOP853',t_eval=coarse.time,rtol=2e-12,atol=1e-14)
    a=np.array([coarse.values[s.name] for s in m.stocks]);b=np.array([fine.values[s.name][::2] for s in m.stocks])
    scale=1+abs(ref.y)
    assert np.max(abs(b-ref.y)/scale)<=.2*np.max(abs(a-ref.y)/scale)+1e-10


def test_review_only_source_inventory_and_no_exact_active_ids_names():
    active=baseline_models(ROOT.parents[1], {model(slug).id for slug in SLUGS})
    assert len(SLUGS)==10
    for slug in SLUGS:
        m=model(slug)
        assert m.id not in {a.get('id') for a in active}
        assert m.name not in {a.get('name') for a in active}
    assert all(e['rights'] and e['parameter_provenance'] for e in MANIFEST)


def test_conservative_stock_derivative_fingerprints_not_active_duplicates():
    import ast
    from app.core.equations import preprocess_equation,canonical_name,decode_identifier
    def fingerprint(raw):
        stocks=raw.get('stocks',[])
        aliases={canonical_name(s['name']):'S'+str(i) for i,s in enumerate(stocks)}
        constants={}
        for v in raw.get('variables',[]):
            try:constants[canonical_name(v['name'])]=float(v.get('equation',''))
            except (TypeError,ValueError):pass
        class Normalize(ast.NodeTransformer):
            def visit_Name(self,node):
                key=canonical_name(decode_identifier(node.id))
                if key in aliases:return ast.Name(id=aliases[key],ctx=ast.Load())
                if key in constants:return ast.Constant(value=constants[key])
                return ast.Name(id=key,ctx=ast.Load())
            def visit_Constant(self,node):
                return ast.Constant(value=float(node.value)) if type(node.value) in (int,float) else node
        output=[]
        for s in stocks:
            terms=[]
            for f in raw.get('flows',[]):
                if f.get('to_stock') in (s.get('id'),s['name']):terms.append('+('+f.get('equation','0')+')')
                if f.get('from_stock') in (s.get('id'),s['name']):terms.append('-('+f.get('equation','0')+')')
            try:output.append(ast.dump(Normalize().visit(ast.parse(preprocess_equation(''.join(terms) or '0'),mode='eval')),include_attributes=False))
            except (ValueError,SyntaxError,RecursionError):return None
        return tuple(output)
    active={fingerprint(raw) for raw in baseline_models(ROOT.parents[1], {model(slug).id for slug in SLUGS})}
    seen=set()
    for slug in SLUGS:
        value=fingerprint(json.loads((ROOT/(slug+'.json')).read_text()))
        assert value and value not in active and value not in seen
        seen.add(value)
