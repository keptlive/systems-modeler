"""Read-only catalog/source inspection and isolated candidate evidence outputs."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,urllib.request
from app.core.model import Model
from app.core.simulator import simulate
from app.core.units import analyze_units
D=Path(__file__).parent;ROOT=D.parents[1]
def h(data):return hashlib.sha256(data).hexdigest()
def write(name,value):(D/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
models=[p for p in sorted(D.glob('*.json')) if p.name.startswith(('finite-source-','pi-'))]
spec=importlib.util.spec_from_file_location('screen',(ROOT/'operations/library-candidates-third-engineering/duplicate_screen.py'));screen=importlib.util.module_from_spec(spec);spec.loader.exec_module(screen)
paths=[ROOT/n for n in subprocess.check_output(['git','ls-files','models'],cwd=ROOT,text=True).splitlines() if n.endswith('.json')];assert len(paths)==996
inventory={str(p.relative_to(ROOT)):h(p.read_bytes()) for p in paths}
indexes={str(p.relative_to(ROOT)):h(p.read_bytes()) for pattern in ('library-admissions*.json','library-quality*.json') for p in sorted((ROOT/'operations').glob(pattern))}
others={str(p.relative_to(ROOT)):json.loads(p.read_text()) for p in paths}
for p in sorted((ROOT/'operations').glob('library-candidates*/*.json')):
 if p.parent==D:continue
 value=json.loads(p.read_text())
 if isinstance(value,dict) and value.get('stocks') and value.get('flows'):others[str(p.relative_to(ROOT))]=value
exact={};abstract={};skipped=[]
for name,raw in others.items():
 try:
  exact.setdefault(screen.fingerprint(raw),[]).append(name);abstract.setdefault(screen.fingerprint(raw,True),[]).append(name)
 except (ValueError,SyntaxError,RecursionError,TypeError):skipped.append(name)
rows=[]
for p in models:
 raw=json.loads(p.read_text());rows.append(dict(file=p.name,expanded_matches=exact.get(screen.fingerprint(raw),[]),constant_abstracted_matches=abstract.get(screen.fingerprint(raw,True),[])))
 assert not rows[-1]['expanded_matches'] and not rows[-1]['constant_abstracted_matches'],rows[-1]
closest=['models/economics/erlang-loss-call-center-eco.json','models/economics/mm1-queue-dynamics-eco.json','models/classic/wiener-cybernetic-feedback-cla.json','models/energy/power-grid-frequency-control-ene.json','models/engineering/candidate-applied-nonlinear-pendulum-feedback.json']
write('DEDUPE-BASELINE.json',dict(baseline_count=996,inventory_sha256=h(json.dumps(inventory,sort_keys=True).encode()),all_tracked_hashes=inventory,inspected_indexes=indexes,compared=len(others),expanded=len(others)-len(skipped),unexpanded=skipped,helper_sha256=h((ROOT/'operations/library-candidates-third-engineering/duplicate_screen.py').read_bytes()),candidate_results=rows,closest={n:dict(name=others[n]['name'],stocks=[s['name'] for s in others[n]['stocks']],flow_equations=[f['equation'] for f in others[n]['flows']]) for n in closest},limits='Stock order preserved; no permutation/isomorphism/transcendental-identity proof. Unsupported/cyclic forms listed; source/mechanism comparison remains required.'))
rows=[]
for p in models:
 m=Model.model_validate_json(p.read_text());r=simulate(m);assert analyze_units(m)['status']=='consistent'
 rows.append(dict(file=p.name,id=m.id,sha256=h(p.read_bytes()),points=len(r.time),output_sha256=h(json.dumps(r.values,sort_keys=True,separators=(',',':')).encode()),stock_ranges={s.name:[min(r.values[s.name]),max(r.values[s.name])] for s in m.stocks},units_status='consistent',assumptions='Original illustrative defaults; no empirical validation.'))
write('NUMERICAL-EVIDENCE.json',dict(scope='Local complete default RK4 runs plus independent test_candidates.py analytical/invariant/limit checks',models=rows,engine_sha256={str(p.relative_to(ROOT)):h(p.read_bytes()) for p in sorted((ROOT/'app/core').glob('*.py'))}))

value=json.loads((D/'DEDUPE-BASELINE.json').read_text())
value['manual_unexpanded_assessment']={'models/energy/duck-curve-solar-grid-ene.json':'Three solar/dispatch/storage stocks with time-dependent solar ramp and selector charging; neither four-state finite-source generator nor two-state saturated PI tracking loop.','models/physics/heat-transfer-and-diffusion-model-phy.json':'Four air/wall/floor/energy stocks. Thermal air/wall/floor exchange and cumulative energy are not normalized down-machine probabilities; no finite-source birth/single-server repair transitions or PI command saturation/tracking correction.'}
write('DEDUPE-BASELINE.json',value)

# Record transient-reference residuals without changing model/engine numerics.
import numpy as np
from scipy.integrate import solve_ivp
m=Model.model_validate_json((D/'pi-back-calculation-sixth-control.json').read_text())
def rhs(t,state):
 y,i=state;e=.8-y;v=3*e+i;u=min(1,max(0,v))
 return [(u-y)/2,e+2*(u-v)]
errors=[]
for step in (.02,.01,.005):
 m.time_settings.dt=step;r=simulate(m);ref=solve_ivp(rhs,(0,20),[0,0],method='DOP853',rtol=2e-12,atol=2e-13,t_eval=r.time,max_step=.01)
 assert ref.success
 errors.append(dict(dt=step,max_abs=float(np.max(np.abs(np.array([r.values['Output'],r.values['Integral_Output']])-ref.y)))))
value=json.loads((D/'NUMERICAL-EVIDENCE.json').read_text());value['pi_switch_step_refinement']=errors
value['author_validation']={'command':'PYTHONPATH=. .venv/bin/python -m pytest -q operations/library-candidates-sixth-control/test_candidates.py','passed':43,'seconds':11.56,'reference_scope':'12 full-series varied repair matrix exponentials; exact stationary/binomial/Erlang limits; exact unsaturated/saturated PI curves and13 full-series PI DOP853 checks plus step refinement. Solver defaults retained.'}
write('NUMERICAL-EVIDENCE.json',value)
