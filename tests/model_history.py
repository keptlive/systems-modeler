"""Verify current bytes before recovering a hash-bound historical model version.

Historical preservation claims stay tested against their original release. New
repair tests separately exercise current equations and intentional changes.
"""
import hashlib
import json

def model_path(root, relative):
    """Read a current model, or its explicitly retired, hash-bound test fixture."""
    path = root / relative
    if path.exists():
        return path
    manifest = json.loads((root / 'operations/library-curation.json').read_text())
    record = next(row for row in manifest['retired'] if row['file'] == str(relative))
    archived = root / record['archive']
    assert hashlib.sha256(archived.read_bytes()).hexdigest() == record['sha256'], str(relative)
    return archived


def find_model_path(root, stem):
    paths = list((root / 'models').rglob(stem + '.json'))
    if paths:
        assert len(paths) == 1
        return paths[0]
    manifest = json.loads((root / 'operations/library-curation.json').read_text())
    rows = [r for r in manifest['retired'] if r['id'] == stem]
    assert len(rows) == 1, stem
    return model_path(root, rows[0]['file'])

def v18_bytes(root,relative):
    raw=model_path(root,relative).read_bytes()
    chain=json.loads((root/'operations/model-revision-chain-v19.json').read_text())
    row=next((r for r in chain['models'] if r['file']==str(relative)),None)
    if row is None:return raw
    assert hashlib.sha256(raw).hexdigest()==row['after_sha256'],str(relative)
    previous=row['before_text'].encode()
    assert hashlib.sha256(previous).hexdigest()==row['before_sha256'],str(relative)
    return previous


def v17_bytes(root,relative):
    raw=v18_bytes(root,relative)
    chain=json.loads((root/'operations/model-revision-chain-v18.json').read_text())
    row=next((r for r in chain['models'] if r['file']==str(relative)),None)
    if row is None:return raw
    assert hashlib.sha256(raw).hexdigest()==row['after_sha256'],str(relative)
    previous=row['before_text'].encode()
    assert hashlib.sha256(previous).hexdigest()==row['before_sha256'],str(relative)
    return previous


def pre_hardening_v19_bytes(root, relative):
    """Recover source-repair bytes through the separately reviewed solver revision."""
    raw=model_path(root,relative).read_bytes()
    chain=json.loads((root/'operations/corpus-hardening-repairs-v19-b.json').read_text())
    row=next((r for r in chain['models'] if r['file']==str(relative)),None)
    if row is None:return raw
    assert hashlib.sha256(raw).hexdigest()==row['after_sha256'],str(relative)
    previous=row['before_text'].encode()
    assert hashlib.sha256(previous).hexdigest()==row['before_sha256'],str(relative)
    return previous
