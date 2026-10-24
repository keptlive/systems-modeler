"""Apply an explicit, hash-bound retirement/repair list; never sync a directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan(app, manifest):
    app = app.resolve()
    actions = manifest['actions']
    if not 1 <= len(actions) <= 200:
        raise ValueError('Expected 1–200 explicitly reviewed model actions')
    seen, rows = set(), []
    for entry in actions:
        relative = Path(entry['file'])
        if (relative.is_absolute() or '..' in relative.parts or len(relative.parts)<2
                or relative.parts[0]!='models' or relative.suffix!='.json'):
            raise ValueError('Only individual model JSON paths are allowed')
        if str(relative) in seen:
            raise ValueError('Duplicate model action')
        seen.add(str(relative))
        target = app / relative
        if target.is_symlink() or not target.resolve().is_relative_to(app / 'models'):
            raise ValueError('Model path escapes the model directory')
        raw = target.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry['before_sha256']:
            raise ValueError('Model changed since review: '+str(relative))
        if json.loads(raw)['id'] != entry['id']:
            raise ValueError('Model identity changed')
        payload = None
        if entry['action']=='replace':
            payload = entry['content'].encode()
            if hashlib.sha256(payload).hexdigest()!=entry['after_sha256']:
                raise ValueError('Replacement hash mismatch')
            if json.loads(payload)['id']!=entry['id']:
                raise ValueError('Replacement changes model identity')
        elif entry['action']!='retire':
            raise ValueError('Unknown action')
        rows.append((relative,target,payload,target.stat()))
    return rows


def data_hashes(app):
    paths=list((app/'models').rglob('*.json'))
    if (app/'models.db').exists():paths.append(app/'models.db')
    return {str(p.relative_to(app)):digest(p) for p in sorted(paths)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--backup',type=Path,required=True)
    parser.add_argument('--service',required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();app=args.app.resolve()
    manifest=json.loads(args.manifest.read_text());rows=plan(app,manifest)
    if not args.apply:
        print(json.dumps({'dry_run':True,'actions':len(rows)}));return
    subprocess.run(['systemctl','stop',args.service],check=True)
    applied=[]
    try:
        rows=plan(app,manifest)  # Recheck after stopping the writer.
        before=data_hashes(app)
        args.backup.mkdir(parents=True,exist_ok=False,mode=0o700)
        (args.backup/'data-before.json').write_text(json.dumps(before,indent=2))
        (args.backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
        # Save every original before changing any model.
        for relative,target,payload,stat in rows:
            saved=args.backup/relative;saved.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(target,saved)
        expected=dict(before)
        for relative,target,payload,stat in rows:
            if payload is None:
                target.unlink();expected.pop(str(relative))
            else:
                temporary=target.with_name('.'+target.name+'.curation')
                with temporary.open('xb') as stream:
                    stream.write(payload);stream.flush();os.fsync(stream.fileno())
                os.chmod(temporary,stat.st_mode & 0o777)
                os.chown(temporary,stat.st_uid,stat.st_gid)
                os.replace(temporary,target)
                expected[str(relative)]=hashlib.sha256(payload).hexdigest()
            applied.append((relative,target,payload,stat))
        if data_hashes(app)!=expected:
            raise RuntimeError('Unexpected model/database change during curation')
        receipt={'actions':len(rows),'retired':sum(p is None for _,_,p,_ in rows),
                 'replaced':sum(p is not None for _,_,p,_ in rows),
                 'all_other_data_unchanged':True,'data_after':expected}
        (args.backup/'receipt.json').write_text(json.dumps(receipt,indent=2))
        print(json.dumps({k:v for k,v in receipt.items() if k!='data_after'}))
    except Exception:
        # Restore only this transaction's successfully applied, unchanged targets.
        for relative,target,payload,stat in reversed(applied):
            expected_hash=hashlib.sha256(payload).hexdigest() if payload else None
            if (target.exists() and digest(target)!=expected_hash) or (not target.exists() and payload is not None):
                raise RuntimeError('Refusing rollback over an unexpected edit: '+str(relative))
            shutil.copy2(args.backup/relative,target)
            os.chown(target,stat.st_uid,stat.st_gid)
        raise
    finally:
        subprocess.run(['systemctl','start',args.service],check=True)


if __name__=='__main__':main()
