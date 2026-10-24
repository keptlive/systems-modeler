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

def before_quality_followup_bytes(root, relative):
    """Verify today's bytes, then recover the reviewed pre-follow-up version."""
    manifest = json.loads((root / 'operations/library-quality-followup-20261024.json').read_text())
    name = str(relative)
    replaced = next((row for row in manifest['replaced'] if row['file'] == name), None)
    retired = next((row for row in manifest['retired'] if row['file'] == name), None)
    row = replaced or retired
    if row is None:
        return before_scope_metadata_bytes(root, relative)
    current = root / relative
    if replaced is not None:
        assert hashlib.sha256(before_scope_metadata_bytes(root, relative)).hexdigest() == row['after_sha256'], name
    else:
        assert not current.exists(), name
    archived = (root / row['archive']).read_bytes()
    assert hashlib.sha256(archived).hexdigest() == row['before_sha256'], name
    return archived


def v18_bytes(root,relative):
    raw=before_quality_followup_bytes(root,relative)
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

def before_scope_metadata_bytes(root, relative):
    """Verify exact current/proposal bytes before recovering approved metadata history."""
    name = str(relative)
    path = root / relative
    manifest = root / "operations/library-metadata-scope-20261024.json"
    if not manifest.exists():
        return model_path(root, relative).read_bytes()
    entries = json.loads(manifest.read_text())["entries"]
    row = next((r for r in entries if r["file"] == name), None)
    if row is None:
        return model_path(root, relative).read_bytes()
    approved = {
        "models/transportation/public-transit-ridership-service-tra.json": (
            "ba7fb744f6c0ee69a2653fce8399dcd125ef8af7b3bea795717c469ccbc8b813",
            "e9817e6ac36f8257472d2d70464e8dbfeb6e2c1671e9a0e26509bcd3fdf97c29"),
        "models/technology/shannon-communication-channel-tec.json": (
            "bf2c9cb984f264d2e082935523d18f83dc594cefd29c3e98a2eb902f135d4618",
            "394ae80f268be47d553847eb517a80f9896331bbcc0946bb508f9d29ba394a07")}
    assert len(entries) == 2 and {r["file"] for r in entries} == set(approved)
    assert (row["before_sha256"], row["after_sha256"]) == approved[name]
    current = path.read_bytes()
    after = (root / row["source"]).read_bytes()
    before = (root / row["archive"]).read_bytes()
    assert current == after and hashlib.sha256(current).hexdigest() == row["after_sha256"], name
    assert hashlib.sha256(before).hexdigest() == row["before_sha256"], name
    a, b = json.loads(before), json.loads(after)
    fields = {"name", "description", "source", "reference"}
    assert set(row["changed_fields"]) == fields
    assert {k for k in a.keys() | b.keys() if a.get(k) != b.get(k)} == fields
    assert a["id"] == b["id"] == row["id"]
    return before
