"""Reproducible read-only engine/source screening; writes local candidate receipts."""
import sys,json,hashlib,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
from scipy.integrate import solve_ivp
from app.core.model import Model
from app.core.simulator import simulate
from app.core.units import analyze_units
from app.core.validation import inspect_inputs
from tests.test_library_candidates_third_engineering import ENTRIES,rhs,D
rows=[]
for entry in ENTRIES:
    p=D/entry['file'];m=Model(**json.loads(p.read_text()));start=time.perf_counter();r=simulate(m);duration=time.perf_counter()-start
    actual=np.array([r.values[s.name] for s in m.stocks]);key=p.stem;f=rhs(key)
    if key=='three-tank-nonlinear-hydraulics':
        expected=np.empty_like(actual);expected[:,0]=actual[:,0]
        for i in range(len(r.time)-1):expected[:,i+1]=expected[:,i]+f(r.time[i],expected[:,i])
    else:
        ref=solve_ivp(f,(0,r.time[-1]),actual[:,0],t_eval=r.time,method='DOP853',rtol=2e-11,atol=1e-12,max_step=.02 if key=='quarter-car-road-suspension' else np.inf);assert ref.success;expected=ref.y
    unit=analyze_units(m);report=inspect_inputs(m,numerical_check=False)
    rows.append(dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),samples=len(r.time),end=r.time[-1],solver=m.time_settings.integration_method,wall_seconds=duration,max_scaled_reference_error=float(np.max(abs(actual-expected)/np.maximum(1,np.max(abs(expected),axis=1))[:,None])),final=actual[:,-1].tolist(),stock_ranges=[[float(min(x)),float(max(x))] for x in actual],units=unit,inspection=report))
sources=[]
for p in sorted((D/'sources').glob('*')):sources.append(dict(file=str(p.relative_to(D)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
# Semantic duplicate screening is deliberately limited; themes still need a human.
active=[]
for p in sorted((ROOT/'models').rglob('*.json')):
    try:active.append(json.loads(p.read_text()))
    except (ValueError,UnicodeError):pass
keywords=['adaptive','levitat','pitch','kite','tire','battery','compressor','hyster','crystal','generator','grid','polymer','chemical']
related=[dict(id=x.get('id'),name=x.get('name')) for x in active if any(k in (x.get('name','')+' '+x.get('description','')).lower() for k in keywords)]
(D/'EVIDENCE.json').write_text(json.dumps(dict(candidates=rows,retained_sources=sources,active_models_screened=len(active),related_theme_models=related,limitations='Numerical conformance is not empirical validation; scalar equation fingerprints are not proof of semantic novelty.'),indent=2)+'\n')
print(json.dumps([(r['file'],r['max_scaled_reference_error'],r['units'].get('status')) for r in rows]))

from duplicate_screen import screen
(D/'DUPLICATE-SCREEN.json').write_text(json.dumps(screen(ROOT,D),indent=2)+'\n')
