from tests.library_admission import baseline_models
"""Independent mathematical admission checks for applied candidates, not active models."""
import json,hashlib,math
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.linalg import expm
from app.core.model import Model
from app.core.simulator import simulate
from app.core.validation import inspect_inputs
from app.core.units import analyze_units
ROOT=Path(__file__).parents[1];DIR=ROOT/'operations/library-candidates-applied'
ENTRIES=json.loads((DIR/'MANIFEST.json').read_text())['candidates']

def rhs(key,data):
    if key=='tcp-red-router':
        def f(t,u):
            return np.r_[10/u[-1]-.002*(1+np.array(u[:-1])**2/2),100*np.sum(u[:-1])/u[-1]-10]
        return f
    if key=='ship-turning-path':
        def f(t,u):
            x,y,h,v,r=u
            return [math.cos(h)+v*math.sin(h),-math.sin(h)+v*math.cos(h),r,-.6*v-.3*r-2*v*abs(v),-5*v-2*r]
        return f
    if key=='nonlinear-cruise-pi':
        def f(t,u):
            v,z=u;err=20-v;throttle=np.clip(.5*err+.099*z,0,1)
            torque=max(190*(1-.4*(12*v/420-1)**2),0)
            slope=4*math.pi/180*np.clip(t-5,0,1)
            return [(12*torque*throttle-1600*9.8*math.sin(slope)-1600*9.8*.01*(1 if v>=0 else -1)-.5*1.3*.32*2.4*abs(v)*v)/1600,err-.002*z]
        return f
    if key=='airfuel-cross-limit':
        def f(t,u):
            a,ad,f,fd=u;r=np.interp(t,data['command_times'],data['command_values'])
            return [ad,-8*ad-4*a+4*max(r,f),fd,-3*fd-4*f+4*min(r,a)]
        return f
    if key=='adaptive-noise-cancel':
        def f(t,u):
            z,w,a,b=u;n=math.sin(.7*t)+.5*math.sin(1.3*t);err=z-w
            return [-.75*z+.9*n,a*w+b*n,.01*w*err,.01*n*err]
        return f
    if key=='nonlinear-pendulum-feedback':
        def f(t,u):
            theta,w=u
            return [w,math.sin(theta)+(-4*math.sin(theta)-w*math.cos(theta))*math.cos(theta)]
        return f
    raise KeyError(key)


def reference(entry,model,time):
    key=Path(entry['file']).stem;data=entry['reference_data'];initial=np.array([s.initial_value for s in model.stocks])
    if key=='sensor-consensus-five-node':
        a=np.eye(5)-.1*np.array(data['laplacian'])
        return np.column_stack([np.linalg.matrix_power(a,int(t))@initial for t in time])
    if key=='active-opamp-bandpass':
        t=np.array(time);return np.array([1-np.exp(-100*t),-100/98*(np.exp(-2*t)-np.exp(-100*t))])
    if key in ('whipple-bicycle-stability','afm-piezo-modes'):
        if key=='whipple-bicycle-stability':
            mass=np.array(data['M']);stiffness=np.array(data['K0'])+49*np.array(data['K2']);damping=7*np.array(data['C'])
            a=np.block([[np.zeros((2,2)),np.eye(2)],[-np.linalg.solve(mass,stiffness),-np.linalg.solve(mass,damping)]])
            return np.column_stack([expm(a*t)@initial for t in time])
        a=np.array(data['A']);b=np.array(data['B']);eq=np.linalg.solve(a,-b)
        vals,vecs=np.linalg.eig(a);coeff=np.linalg.solve(vecs,initial-eq)
        result=eq[:,None]+np.real(vecs@(coeff[:,None]*np.exp(vals[:,None]*np.array(time))))
        for index in np.linspace(0,len(time)-1,9).astype(int):
            np.testing.assert_allclose(result[:,index],eq+expm(a*time[index])@(initial-eq),rtol=1e-8,atol=1e-6)
        return result
    # Air-fuel source interpolation changes slope at .3-grid knots; constrain
    # the independent solver rather than stepping over an inactive interval.
    ref=solve_ivp(rhs(key,data),(0,model.time_settings.end),initial,t_eval=time,method='DOP853',rtol=2e-11,atol=1e-12,max_step=.03 if key=='airfuel-cross-limit' else np.inf)
    assert ref.success
    return ref.y


@pytest.mark.parametrize('entry',ENTRIES,ids=lambda e:e['file'])
def test_default_full_series_matches_independent_reference_and_admission(entry):
    model=Model(**json.loads((DIR/entry['file']).read_text()));run=simulate(model)
    actual=np.array([run.values[s.name] for s in model.stocks]);expected=reference(entry,model,run.time)
    assert np.isfinite(actual).all()
    scale=np.maximum(1,np.max(abs(expected),axis=1))
    assert np.max(np.max(abs(actual-expected),axis=1)/scale)<2e-5
    assert any(np.ptp(row)>1e-7 for row in actual)
    report=inspect_inputs(model,numerical_check=False)
    assert report['valid'],report['issues']
    # Missing units remain unknown; they are never converted into a false pass.
    assert not analyze_units(model)['errors']


def test_source_and_candidate_hashes_licenses_and_no_exact_catalog_duplicate():
    active=baseline_models(ROOT, {entry['id'] for entry in ENTRIES})
    ids={m['id'] for m in active};names={m['name'].lower() for m in active}
    fingerprints={tuple(sorted(f.get('equation','').replace(' ','').lower() for f in m.get('flows',[]))) for m in active}
    seen=set()
    for entry in ENTRIES:
        raw=json.loads((DIR/entry['file']).read_text())
        assert raw['id'] not in ids and raw['name'].lower() not in names
        assert hashlib.sha256((DIR/entry['file']).read_bytes()).hexdigest()==entry['candidate_sha256']
        fp=tuple(sorted(f['equation'].replace(' ','').lower() for f in raw['flows']))
        assert fp not in fingerprints and fp not in seen;seen.add(fp)
        for source in entry['sources']:
            assert hashlib.sha256((DIR/'sources'/source['file']).read_bytes()).hexdigest()==source['sha256']
    assert 'BSD 3-Clause' in (DIR/'sources/LICENSE').read_text()


def getrun(key):
    return simulate(Model(**json.loads((DIR/(key+'.json')).read_text())))


def test_consensus_mean_conservation_variance_contraction_and_exact_iterations():
    run=getrun('sensor-consensus-five-node');a=np.array([run.values[f'Node{i}'] for i in range(1,6)])
    np.testing.assert_allclose(np.mean(a,axis=0),25,atol=1e-12)
    assert np.all(np.diff(np.var(a,axis=0))<=1e-12)
    assert np.ptp(a[:,-1])<np.ptp(a[:,0])/3
    assert run.time==list(range(41))


def test_control_behavior_domains_and_lyapunov_loss():
    run=getrun('tcp-red-router');assert min(run.values['Queue'])>0
    assert np.ptp([run.values[f'Window{i}'][-1] for i in range(1,7)])<np.ptp([run.values[f'Window{i}'][0] for i in range(1,7)])/50
    run=getrun('ship-turning-path');assert abs(run.values['PosY'][-1])>1 and abs(run.values['Heading'][-1])>1
    run=getrun('whipple-bicycle-stability');assert abs(run.values['Roll'][-1])<.001
    run=getrun('nonlinear-cruise-pi');speed=np.array(run.values['Speed']);assert min(speed)<speed[0]-.1 and abs(speed[-1]-20)<.1
    run=getrun('airfuel-cross-limit');assert np.min(np.array(run.values['Air'])-run.values['Fuel'])>-1e-7
    assert abs(run.values['Air'][-1]-.5)<.002 and abs(run.values['Fuel'][-1]-.5)<.002
    run=getrun('adaptive-noise-cancel');err=np.array(run.values['Headphone'])-run.values['Filter']
    assert np.mean(err[-1000:]**2)<np.mean(err[:1000]**2)/3
    run=getrun('active-opamp-bandpass');assert min(run.values['Output'])<-.8 and abs(run.values['Output'][-1])<.003
    run=getrun('nonlinear-pendulum-feedback');theta=np.array(run.values['Angle']);omega=np.array(run.values['AngularRate'])
    energy=.5*omega**2+2*np.sin(theta)**2+np.cos(theta)-1
    assert max(np.diff(energy))<1e-8
    assert abs(theta[-1])<.001 and abs(omega[-1])<.001


@pytest.mark.parametrize('key',['active-opamp-bandpass','afm-piezo-modes','nonlinear-pendulum-feedback'])
def test_step_refinement_improves_complete_trajectory(key):
    entry=next(e for e in ENTRIES if e['file']==key+'.json')
    model=Model(**json.loads((DIR/entry['file']).read_text()))
    if key=='nonlinear-pendulum-feedback':model.time_settings=model.time_settings.model_copy(update={'dt':.02})
    coarse=simulate(model)
    expected=reference(entry,model,coarse.time)
    model.time_settings=model.time_settings.model_copy(update={'dt':model.time_settings.dt/2});fine=simulate(model)
    a=np.array([coarse.values[s.name] for s in model.stocks]);b=np.array([fine.values[s.name][::2] for s in model.stocks])
    scale=np.maximum(1,np.max(abs(expected),axis=1))[:,None]
    assert np.max(abs(b-expected)/scale)<np.max(abs(a-expected)/scale)/7


def test_physical_output_and_declared_vs_unknown_dimensional_evidence():
    entry=next(e for e in ENTRIES if e['file']=='afm-piezo-modes.json')
    run=getrun('afm-piezo-modes');states=np.array([run.values[n] for n in ['Mode1','Rate1','Mode2','Rate2']])
    np.testing.assert_allclose(run.values['PiezoOutput'],np.array(entry['reference_data']['C'])@states,rtol=1e-12,atol=1e-12)
    complete={'sensor-consensus-five-node','nonlinear-cruise-pi','active-opamp-bandpass','nonlinear-pendulum-feedback'}
    for entry in ENTRIES:
        key=Path(entry['file']).stem
        report=analyze_units(Model(**json.loads((DIR/entry['file']).read_text())))
        assert report['status']==('consistent' if key in complete else 'incomplete')


def test_canonical_derivative_fingerprints_are_distinct_from_active_catalog():
    import ast
    from app.core.equations import canonical_name,decode_identifier,preprocess_equation
    def fingerprint(raw):
        stocks=raw.get('stocks',[]);symbols={canonical_name(s['name']):f'S{i}' for i,s in enumerate(stocks)};constants={}
        for v in raw.get('variables',[]):
            try:constants[canonical_name(v['name'])]=float(v.get('equation',''))
            except (TypeError,ValueError):pass
        class Normalize(ast.NodeTransformer):
            def visit_Name(self,node):
                name=canonical_name(decode_identifier(node.id))
                if name in symbols:return ast.Name(id=symbols[name],ctx=ast.Load())
                if name in constants:return ast.Constant(value=constants[name])
                return ast.Name(id=name,ctx=ast.Load())
        equations=[]
        for stock in stocks:
            ids={stock['name'],stock.get('id')};terms=[]
            for flow in raw.get('flows',[]):
                if flow.get('to_stock') in ids:terms.append('+('+flow.get('equation','0')+')')
                if flow.get('from_stock') in ids:terms.append('-('+flow.get('equation','0')+')')
            try:equations.append(ast.dump(Normalize().visit(ast.parse(preprocess_equation(''.join(terms) or '0'),mode='eval')),include_attributes=False))
            except (ValueError,SyntaxError,RecursionError):return None
        return tuple(equations)
    active={fingerprint(raw) for raw in baseline_models(ROOT, {entry['id'] for entry in ENTRIES})};seen=set()
    for entry in ENTRIES:
        candidate=fingerprint(json.loads((DIR/entry['file']).read_text()))
        assert candidate and candidate not in active and candidate not in seen
        seen.add(candidate)
