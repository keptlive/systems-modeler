"""Read-only catalog/source inspection and isolated candidate evidence outputs."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,urllib.request
from app.core.model import Model
from app.core.simulator import simulate
from app.core.units import analyze_units
D=Path(__file__).parent;ROOT=D.parents[1]
def h(data):return hashlib.sha256(data).hexdigest()
def write(name,value):(D/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
models=[p for p in sorted(D.glob('*.json')) if p.name.startswith(('holt-','three-stage-'))]
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
closest=['models/economics/rosenzweig-macarthur-predator-prey-eco.json','models/ecology/predator-prey-stable.json','models/environment/competitive-langmuir-closed-sorption-environment.json','models/engineering/candidate-second-applied-binary-distillation-thirty-two.json']
write('DEDUPE-BASELINE.json',dict(baseline_count=996,inventory_sha256=h(json.dumps(inventory,sort_keys=True).encode()),all_tracked_hashes=inventory,inspected_indexes=indexes,compared=len(others),expanded=len(others)-len(skipped),unexpanded=skipped,helper_sha256=h((ROOT/'operations/library-candidates-third-engineering/duplicate_screen.py').read_bytes()),candidate_results=rows,closest={n:dict(name=others[n]['name'],stocks=[s['name'] for s in others[n]['stocks']],flow_equations=[f['equation'] for f in others[n]['flows']]) for n in closest},limits='Stock order preserved; no permutation/isomorphism/transcendental-identity proof. Unsupported/cyclic forms listed; source/mechanism comparison remains required.'))
rows=[]
for p in models:
 m=Model.model_validate_json(p.read_text());r=simulate(m);assert analyze_units(m)['status']=='consistent'
 rows.append(dict(file=p.name,id=m.id,sha256=h(p.read_bytes()),points=len(r.time),output_sha256=h(json.dumps(r.values,sort_keys=True,separators=(',',':')).encode()),stock_ranges={s.name:[min(r.values[s.name]),max(r.values[s.name])] for s in m.stocks},units_status='consistent',assumptions='Original illustrative defaults; no empirical validation.'))
write('NUMERICAL-EVIDENCE.json',dict(scope='Local complete default RK4 runs plus independent test_candidates.py analytical/invariant/limit checks',models=rows,engine_sha256={str(p.relative_to(ROOT)):h(p.read_bytes()) for p in sorted((ROOT/'app/core').glob('*.py'))}))

value=json.loads((D/'DEDUPE-BASELINE.json').read_text())
value['manual_unexpanded_assessment']={'models/energy/duck-curve-solar-grid-ene.json':'Three solar/dispatch/storage stocks with time-dependent solar ramp and selector charging; not independent prey with shared enemy.','models/physics/heat-transfer-and-diffusion-model-phy.json':'Four air/wall/floor/energy stocks; different state count and thermal mechanism from both candidates.'}
write('DEDUPE-BASELINE.json',value)
