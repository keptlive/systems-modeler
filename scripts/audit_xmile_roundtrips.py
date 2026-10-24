"""Audit full tracked-model XMILE round trips; preserve trajectories, settings and roles."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.model import Model
from app.core.simulator import simulate
from app.core.xmile_generator import generate_xmile
from app.core.xmile_parser import parse_xmile

ROOT=Path(__file__).resolve().parents[1]

def hashes():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'app/core').glob('*.py'))}

def tracked_model_hashes(root):
    """Capture the tracked JSON inventory and exact bytes, including staged files."""
    names=subprocess.check_output(['git','ls-files','-z','--','models'],cwd=root).decode().split('\0')
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest()
            for name in sorted(names) if name.endswith('.json')}

def assert_model_manifest(root, expected):
    assert tracked_model_hashes(root)==expected, 'Tracked model inventory or bytes changed during audit'

def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    output=args.output
    before=hashes(); models_before=tracked_model_hashes(ROOT); rows=[]; started=time.monotonic()
    for name in models_before:
        raw=(ROOT/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==models_before[name], 'Model bytes changed before simulation'
        m=Model.model_validate_json(raw); row={'file':name,'id':m.id}
        if m.time_settings.random_seed is None: m.time_settings.random_seed=42
        try:
            snapshot=m.model_dump(mode='json'); a=simulate(m)
            xml=generate_xmile(m); imported=parse_xmile(xml)
            assert m.model_dump(mode='json')==snapshot, 'Export mutated source model'
            row['source_sha256']=models_before[name]
            row['xml_sha256']=hashlib.sha256(xml.encode()).hexdigest()
            b=simulate(imported)
            row['status']='passed' if a.time==b.time and a.values==b.values and a.report_values==b.report_values and m.time_settings.model_dump()==imported.time_settings.model_dump() and {v.name:v.role for v in m.variables}=={v.name:v.role for v in imported.variables} else 'changed'
            if row['status']=='changed':
                row['differing_outputs']=[k for k,v in a.values.items() if b.values.get(k)!=v]
                row['time_equal']=a.time==b.time
        except Exception as e: row.update(status='rejected',error=str(e))
        rows.append(row)
    assert hashes()==before, 'Source changed during audit'
    assert_model_manifest(ROOT, models_before)
    from collections import Counter
    result={'engine_sha256':before,'model_sha256':models_before,'scope':'All tracked public complete seeded defaults through scalar XMILE','counts':dict(Counter(r['status'] for r in rows)),'seconds':time.monotonic()-started,'models':rows}
    output.write_text(json.dumps(result,indent=2)+'\n'); print(result['counts'])

    if not rows or any(r['status'] != 'passed' for r in rows):
        raise SystemExit(1)


if __name__=='__main__':
    main()
