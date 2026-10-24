"""Exact local adoption, archived originals and cumulative catalog accounting."""
import hashlib,json
from pathlib import Path
from tests.library_admission import baseline_models
ROOT=Path(__file__).resolve().parents[1]
def test_exact_adopted_transaction_and_historical_accounting():
    m=json.loads((ROOT/'operations/library-quality-followup-20261024.json').read_text())
    assert len(m['retired'])==2 and len(m['replaced'])==27
    assert m['active_count']==993
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
    # Preserve the historical transaction's77/993 accounting against its exact
    # pre-fourth-admission ledger, not today's intentionally larger inventory.
    original=(ROOT/'tests/fixtures/fourth-admissions-20261024/ledger-before.json').read_bytes()
    assert hashlib.sha256(original).hexdigest()=='9b28aa91078e2f151a4be915c62672ba80640f7a7c6cb9000f9d5c0751f77010'
    historical=json.loads(original)
    assert historical['baseline_count']==923 and historical['admitted_count']==77
    assert historical['retired_count']==7 and historical['active_count']==993
    fourth=json.loads((ROOT/'operations/library-admissions-fourth-20261024.json').read_text())
    before=fourth['all_993_before_hashes']
    assert len(before)==993 and fourth['baseline_count']==historical['active_count']
    for name,h in before.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
    assert len(baseline_models(ROOT))==916


def test_current_fourth_admission_extends_exact_historical_ledger():
    original=(ROOT/'tests/fixtures/fourth-admissions-20261024/ledger-before.json').read_bytes()
    assert hashlib.sha256(original).hexdigest()=='9b28aa91078e2f151a4be915c62672ba80640f7a7c6cb9000f9d5c0751f77010'
    historical=json.loads(original)
    frozen=(ROOT/'tests/fixtures/fifth-sixth-admissions-20261024/ledger-before.json').read_bytes()
    assert hashlib.sha256(frozen).hexdigest()=='9cbb8c583e3aa369828616a3481f88e444ce47a01876d7ea7eb5828905224812'
    adm=json.loads(frozen)
    fourth=json.loads((ROOT/'operations/library-admissions-fourth-20261024.json').read_text())
    assert len(fourth['models'])==fourth['admitted_count']==3
    assert adm['models']==historical['models']+fourth['models']
    assert adm['admitted_count']==80 and adm['active_count']==996
    assert adm['admitted_count']-fourth['admitted_count']==historical['admitted_count']==77
    assert adm['active_count']-fourth['admitted_count']==historical['active_count']==993
    assert adm['baseline_count']==historical['baseline_count']==923
    assert adm['retired_count']==historical['retired_count']==7
    assert adm['baseline_count']+adm['admitted_count']-adm['retired_count']==adm['active_count']
    for row in fourth['models']:
        assert (ROOT/row['file']).read_bytes()==(ROOT/row['source']).read_bytes()
        assert hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest()==row['sha256']
        assert row['sha256'] in (ROOT/row['review']).read_text()
    assert set(fourth['all_993_before_hashes']).isdisjoint({row['file'] for row in fourth['models']})
    latest=json.loads((ROOT/'operations/library-admissions-fifth-sixth-20261024.json').read_text())
    current={str(p.relative_to(ROOT)) for p in (ROOT/'models').rglob('*.json')}
    assert current==set(latest['all_996_before_hashes'])|{r['file'] for r in latest['models']}
    current-= {r['file'] for r in latest['models']}
    assert current==set(fourth['all_993_before_hashes'])|{row['file'] for row in fourth['models']}
    assert len(current)==996


def test_exact_26_description_only_changes():
    m=json.loads((ROOT/'operations/library-quality-followup-20261024.json').read_text())
    for r in m['replaced'][:26]:
        old=json.loads((ROOT/r['archive']).read_text())
        new=json.loads((ROOT/r['file']).read_text())
        assert {k for k in old.keys()|new.keys() if old.get(k)!=new.get(k)}=={'description'}
        assert new['description']==old['description'].replace(' Reference: NSIDC Arctic Sea Ice News. Source: https://nsidc.org/arcticseaicenews/','')
