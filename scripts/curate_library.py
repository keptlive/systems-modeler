"""Apply an explicit, hash-bound retirement/repair/admission list; never sync a directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat as file_type
import subprocess
import uuid


def _regular_reader(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    stream=os.fdopen(fd,'rb')
    if not file_type.S_ISREG(os.fstat(stream.fileno()).st_mode):
        stream.close()
        raise ValueError('Model/database paths must be regular files')
    return stream


def _regular_bytes(path):
    with _regular_reader(path) as stream:
        return stream.read()


def digest(path):
    value=hashlib.sha256()
    with _regular_reader(path) as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            value.update(chunk)
    return value.hexdigest()


def _relative(value):
    if not isinstance(value,str) or '\\' in value or ':' in value or '\x00' in value:
        raise ValueError('Only individual model JSON paths are allowed')
    relative=Path(value)
    if (relative.is_absolute() or '..' in relative.parts or len(relative.parts)<2
            or relative.parts[0]!='models' or relative.suffix!='.json'):
        raise ValueError('Only individual model JSON paths are allowed')
    return relative


def _target(app,relative,create=False):
    target=app/relative
    if target.is_symlink() or not target.resolve().is_relative_to(app/'models'):
        raise ValueError('Model path escapes the model directory')
    if create:
        for ancestor in [app/'models',*target.parents]:
            if ancestor==app:break
            if ancestor.is_symlink():
                raise ValueError('Create paths may not follow symbolic links')
    return target


def _identity(raw):
    def reject_constant(value):
        raise ValueError('Nonfinite JSON constant is unsupported')
    try:
        if isinstance(raw,bytes):raw=raw.decode('utf-8')
        value=json.loads(raw,parse_constant=reject_constant)
    except (ValueError,UnicodeDecodeError) as exc:
        raise ValueError('Model content must be valid JSON') from exc
    if not isinstance(value,dict) or not isinstance(value.get('id'),str) or not value['id']:
        raise ValueError('Model content requires a nonempty string identity')
    return value['id']


def model_files(app):
    """Fail closed on unreadable subtrees and symbolic links."""
    root=app/'models'
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Model directory must be an existing real directory')
    def fail(error):raise error
    for directory,children,files in os.walk(root,followlinks=False,onerror=fail):
        for name in children:
            if (Path(directory)/name).is_symlink():
                raise ValueError('Cannot establish model identities through symbolic links')
        for name in files:
            path=Path(directory)/name
            if path.suffix.lower()!='.json':continue
            if path.is_symlink():
                raise ValueError('Cannot establish model identities through symbolic links')
            yield path


def model_identities(app):
    identities={}
    for path in model_files(app):
        ident=_identity(_regular_bytes(path))
        identities.setdefault(ident,[]).append(path)
    return identities


def plan(app, manifest):
    app = app.resolve()
    actions = manifest['actions']
    if not 1 <= len(actions) <= 200:
        raise ValueError('Expected 1–200 explicitly reviewed model actions')
    seen, rows, created_ids = set(), [], set()
    identities=model_identities(app) if any(e.get('action')=='create' for e in actions) else {}
    for entry in actions:
        relative = _relative(entry['file'])
        if str(relative) in seen:
            raise ValueError('Duplicate model action')
        seen.add(str(relative))
        create=entry['action']=='create'
        target=_target(app,relative,create)
        if create:
            if target.exists():
                raise ValueError('Create destination already exists: '+str(relative))
            ident=entry['id']
            if not isinstance(ident,str) or not ident:
                raise ValueError('Create requires a nonempty model identity')
            if ident in identities or ident in created_ids:
                raise ValueError('Create model identity already exists: '+ident)
            created_ids.add(ident)
            if not isinstance(entry.get('content'),str):
                raise ValueError('Create content must be JSON text')
            payload=entry['content'].encode('utf-8')
            if hashlib.sha256(payload).hexdigest()!=entry['after_sha256']:
                raise ValueError('Create hash mismatch')
            if _identity(payload)!=ident:
                raise ValueError('Create content changes model identity')
            rows.append((relative,target,payload,None))
            continue
        raw = _regular_bytes(target)
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
    paths=list(model_files(app))
    if (app/'models.db').exists():paths.append(app/'models.db')
    return {str(p.relative_to(app)):digest(p) for p in sorted(paths)}


def _create_parent(app,relative):
    """Open/create the reviewed parent without following any directory symlink."""
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
    fd=os.open(app,flags)
    try:
        for part in relative.parts[:-1]:
            try:next_fd=os.open(part,flags,dir_fd=fd)
            except FileNotFoundError:
                owner=os.fstat(fd)
                os.mkdir(part,mode=0o755,dir_fd=fd)
                next_fd=os.open(part,flags,dir_fd=fd)
                os.fchown(next_fd,owner.st_uid,owner.st_gid)
                os.fchmod(next_fd,0o755)
            os.close(fd);fd=next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def create_model(app,row,on_created):
    """Publish complete bytes atomically; link refuses any existing destination."""
    relative,target,payload,_=row
    _target(app,relative,True)
    if _identity(payload) in model_identities(app):
        raise ValueError('Create model identity already exists before admission')
    directory=_create_parent(app,relative)
    temporary='.'+relative.name+'.curation-'+uuid.uuid4().hex
    made_temp=False
    try:
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644,dir_fd=directory)
        made_temp=True
        with os.fdopen(fd,'wb') as stream:
            os.fchmod(stream.fileno(),0o644)
            stream.write(payload);stream.flush();os.fsync(stream.fileno())
            owner=os.fstat(directory)
            os.fchown(stream.fileno(),owner.st_uid,owner.st_gid)
            os.fsync(stream.fileno())
        os.link(temporary,relative.name,src_dir_fd=directory,dst_dir_fd=directory,follow_symlinks=False)
        on_created()  # Track before cleanup/fsync, so any later failure rolls back.
        os.unlink(temporary,dir_fd=directory);made_temp=False
        os.fsync(directory)
    finally:
        try:
            if made_temp:
                os.unlink(temporary,dir_fd=directory)
        finally:
            os.close(directory)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--backup',type=Path,required=True)
    parser.add_argument('--service',required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();app=args.app.resolve()
    backup=args.backup.resolve()
    if backup==app/'models.db' or backup==app/'models' or backup.is_relative_to(app/'models'):
        raise ValueError('Backup must be outside model data paths')
    manifest=json.loads(args.manifest.read_text());rows=plan(app,manifest)
    if not args.apply:
        print(json.dumps({'dry_run':True,'actions':len(rows),'created_files':[str(r) for r,_,_,st in rows if st is None]}));return
    subprocess.run(['systemctl','stop',args.service],check=True)
    applied=[];backup_owned=False
    try:
        rows=plan(app,manifest)  # Recheck after stopping the writer.
        before=data_hashes(app)
        args.backup.mkdir(parents=True,exist_ok=False,mode=0o700)
        backup_owned=True
        (args.backup/'data-before.json').write_text(json.dumps(before,indent=2))
        (args.backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
        creates=[{'file':str(r),'id':_identity(p),'after_sha256':hashlib.sha256(p).hexdigest()}
                 for r,_,p,st in rows if st is None]
        (args.backup/'created-files.json').write_text(json.dumps(creates,indent=2))
        # Save every original before changing any existing model; creates have none.
        for relative,target,payload,stat in rows:
            if stat is None:continue
            saved=args.backup/relative;saved.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(target,saved)
        expected=dict(before)
        for row in rows:
            relative,target,payload,stat=row
            if stat is None:
                create_model(app,row,lambda row=row:applied.append(row))
                expected[str(relative)]=hashlib.sha256(payload).hexdigest()
                continue
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
            applied.append(row)
        if data_hashes(app)!=expected:
            raise RuntimeError('Unexpected model/database change during curation')
        if creates:
            final_ids=model_identities(app)
            for created in creates:
                if final_ids.get(created['id'])!=[app/created['file']]:
                    raise RuntimeError('Create model identity changed during curation')
        receipt={'actions':len(rows),'retired':sum(p is None for _,_,p,_ in rows),
                 'replaced':sum(p is not None and st is not None for _,_,p,st in rows),
                 'created':len(creates),'created_files':creates,
                 'all_other_data_unchanged':True,'data_after':expected}
        (args.backup/'receipt.json').write_text(json.dumps(receipt,indent=2))
        print(json.dumps({k:v for k,v in receipt.items() if k!='data_after'}))
    except Exception:
        refused=[];restored=[]
        # Restore/remove only this transaction's unchanged targets; preserve edits.
        for relative,target,payload,stat in reversed(applied):
            try:
                _target(app,relative,stat is None)
                expected_hash=hashlib.sha256(payload).hexdigest() if payload else None
                if stat is None:
                    if target.exists():
                        if digest(target)!=expected_hash:
                            raise RuntimeError('Unexpected edit')
                        target.unlink()
                else:
                    if (target.exists() and digest(target)!=expected_hash) or (not target.exists() and payload is not None):
                        raise RuntimeError('Unexpected edit')
                    shutil.copy2(args.backup/relative,target)
                    os.chown(target,stat.st_uid,stat.st_gid)
                restored.append(str(relative))
            except (OSError,ValueError,RuntimeError):
                refused.append(str(relative))
        if backup_owned:
            (args.backup/'rollback-receipt.json').write_text(json.dumps({'restored_or_removed':restored,'refused_unexpected_edits':refused},indent=2))
        if refused:
            raise RuntimeError('Refusing rollback over an unexpected edit: '+', '.join(refused))
        raise
    finally:
        subprocess.run(['systemctl','start',args.service],check=True)


if __name__=='__main__':main()
