"""Exact local adoption, archived originals and cumulative catalog accounting."""
import hashlib,json
from pathlib import Path
from tests.library_admission import baseline_models
ROOT=Path(__file__).resolve().parents[1]
def test_exact_adopted_transaction_and_historical_accounting():
    m=json.loads((ROOT/'operations/library-quality-followup-20261024.json').read_text())
    assert len(m['retired'])==2 and len(m['replaced'])==27
    rows=m['retired']+m['replaced']
    assert len({r['file'] for r in rows})==29
    for r in rows:
        assert hashlib.sha256((ROOT/r['archive']).read_bytes()).hexdigest()==r['before_sha256']
        if 'review_manifest' in r:
            proof=(ROOT/r['review_manifest']).read_bytes()
            assert hashlib.sha256(proof).hexdigest()==r['review_manifest_sha256']
            assert r['review_manifest_sha256'] in (ROOT/r['review']).read_text()
            entry=next(e for e in json.loads(proof)['entries'] if e['path']==r['file'])
            assert entry['before_sha256']==r['before_sha256'] and entry['after_sha256']==r['after_sha256']
        else: assert r['before_sha256'] in (ROOT/r['review']).read_text()
    for r in m['retired']:assert not (ROOT/r['file']).exists()
    for r in m['replaced']:
        assert (ROOT/r['file']).read_bytes()==(ROOT/r['source']).read_bytes()
        assert hashlib.sha256((ROOT/r['file']).read_bytes()).hexdigest()==r['after_sha256']
    adm=json.loads((ROOT/'operations/library-admissions-20261024.json').read_text())
    assert adm['baseline_count']==923 and adm['admitted_count']==77
    assert adm['retired_count']==7 and adm['active_count']==993
    assert len(baseline_models(ROOT))==916
    assert len(list((ROOT/'models').rglob('*.json')))==993

def test_exact_26_description_only_changes():
    m=json.loads((ROOT/'operations/library-quality-followup-20261024.json').read_text())
    for r in m['replaced'][:26]:
        old=json.loads((ROOT/r['archive']).read_text())
        new=json.loads((ROOT/r['file']).read_text())
        assert {k for k in old.keys()|new.keys() if old.get(k)!=new.get(k)}=={'description'}
        assert new['description']==old['description'].replace(' Reference: NSIDC Arctic Sea Ice News. Source: https://nsidc.org/arcticseaicenews/','')
