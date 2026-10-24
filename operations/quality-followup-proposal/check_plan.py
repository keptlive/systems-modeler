from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
    plan=json.loads((Path(__file__).with_name('PLAN.json')).read_text())
    rows=plan['actions']
    assert len(rows)==29 and len({r['file'] for r in rows})==29 and len({r['id'] for r in rows})==29
    assert sum(r['action']=='replace' for r in rows)==27
    assert sum(r['action']=='retire' for r in rows)==2
    for i,r in enumerate(rows):
        before=ROOT/r['proposed_archive']
        assert digest(before)==r['before_sha256']
        assert digest(ROOT/r['file'])==r['before_sha256'], r['file']
        assert json.loads(before.read_text())['id']==r['id']
        if r['action']=='replace':
            after=ROOT/r['source']
            assert digest(after)==r['after_sha256']
            old,new=json.loads(before.read_text()),json.loads(after.read_text())
            assert new['id']==r['id']
            if i<26:
                assert {k for k in old.keys()|new.keys() if old.get(k)!=new.get(k)}=={'description'}
                sentence=' Reference: NSIDC Arctic Sea Ice News. Source: https://nsidc.org/arcticseaicenews/'
                assert old['description'].replace(sentence,'')==new['description']
    deps=plan['dependencies']
    assert digest(ROOT/'operations/provenance-cleanup/MANIFEST.json')==deps['provenance_manifest_sha256']
    assert digest(ROOT/'operations/may-consolidation-proposal/PLAN.json')==deps['may_plan_sha256']
    assert digest(ROOT/deps['migration_document'])==deps['migration_document_sha256']
    return {'actions':29,'replace':27,'retire':2,'active_writes':0}
if __name__=='__main__': print(json.dumps(check()))
