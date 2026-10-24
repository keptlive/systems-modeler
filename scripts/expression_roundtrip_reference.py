"""Compare full scalar export round trips with an explicitly selected Simlin build.

Run from the repository root with --reference-python pointing to an isolated
pysimlin environment. Differences are observations, never silently accepted as
our expected semantics. Reference error rows retain unsupported cases.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.model import Model
from app.core.simulator import simulate
from app.core.xmile_parser import parse_xmile
from app.core.xmile_generator import generate_xmile

REFERENCE = r'''
import hashlib,json,sys
from pathlib import Path
import simlin
base=Path(sys.argv[1]); rows=[]
for path in sorted(base.glob('*.xmile')):
    row={'case':path.stem}
    try:
        frame=simlin.load(path).run(analyze_loops=False).results
        row.update(time=list(map(float,frame.index)),output=list(map(float,frame['output'])))
    except Exception as exc:
        row['error']={'type':type(exc).__name__,'message':str(exc)[:1000]}
    rows.append(row)
native={str(p.name):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(simlin.__file__).parent.rglob('*.so')}
Path(sys.argv[2]).write_text(json.dumps({'native_sha256':native,'cases':rows},allow_nan=False))
'''


def cases():
    expressions = {
        'power':'POW(TIME - 2, 2)', 'remainder_positive':'MODULO(TIME - 2, 3)',
        'remainder_negative':'MODULO(TIME - 2, -3)',
        'near_zero_division':'XIDZ(3, .000000001, 7)',
        'threshold_division':'XIDZ(3, .000001, 7)',
        'zero_division':'ZIDZ(3, 0)', 'exact_zero_division':'SAFEDIV(3, .000000001, 7)',
        'negative_start_ramp':'RAMP(1, -10)', 'inverse_alias':'ARCSIN(.5)',
        'nested_lookup':'2 * LOOKUP(Curve, TIME)',
    }
    for name, expression in expressions.items():
        model = Model(name=name, variables=[{'name':'Output','equation':expression}],
            tables=[{'name':'Curve','points':[(0,10),(4,20)]}] if name=='nested_lookup' else [],
            time_settings={'start':0,'end':4,'dt':.25,'integration_method':'rk4'})
        yield name, model


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-python',required=True)
    parser.add_argument('--reference-source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    engine={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'app/core').glob('*.py'))}
    head=subprocess.check_output(['git','-C',str(args.reference_source),'rev-parse','HEAD'],text=True).strip()
    dirty=subprocess.check_output(['git','-C',str(args.reference_source),'status','--porcelain'],text=True).strip()
    if dirty:
        raise SystemExit('Reference checkout must be clean')
    result={'scope':'Complete 17-sample scalar RK4 series; exact local round trips; observed reference comparisons, not universal parity.',
        'reference_source_commit':head,'engine_sha256':engine,'cases':[]}
    with tempfile.TemporaryDirectory(prefix='expression-roundtrip-') as folder:
        folder=Path(folder)
        for name, model in cases():
            before=simulate(model)
            raw=generate_xmile(model)
            after=simulate(parse_xmile(raw))
            if before.time != after.time or before.values != after.values:
                raise AssertionError('Roundtrip changed '+name)
            (folder/(name+'.xmile')).write_text(raw)
            result['cases'].append({'case':name,'local_roundtrip_equal':True,
                'xml_sha256':hashlib.sha256(raw.encode()).hexdigest(),
                'time':before.time,'output':before.values['Output']})
        runner=folder/'reference.py'; runner.write_text(REFERENCE)
        output=folder/'reference.json'
        subprocess.run([args.reference_python,str(runner),str(folder),str(output)],check=True)
        reference=json.loads(output.read_text())
        result['reference_native_sha256']=reference['native_sha256']
        by_name={r['case']:r for r in reference['cases']}
        for row in result['cases']:
            ref=by_name[row['case']]; row['reference']=ref
            if 'error' in ref:
                row['comparison']='reference_rejected'
            else:
                row['comparison']='agree' if row['time']==ref['time'] and all(abs(a-b)<=1e-12*max(1,abs(a),abs(b)) for a,b in zip(row['output'],ref['output'])) and len(row['output'])==len(ref['output']) else 'difference'
    if engine != {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'app/core').glob('*.py'))}:
        raise AssertionError('Engine changed during comparison')
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({kind:sum(r['comparison']==kind for r in result['cases']) for kind in ('agree','difference','reference_rejected')}))

if __name__=='__main__':
    main()
