"""Proof that isolated citation proposals cannot alter executable model content."""
import hashlib
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).parents[1]
D=ROOT/'operations/provenance-cleanup'
MANIFEST=json.loads((D/'MANIFEST.json').read_text())
ENTRIES=MANIFEST['entries']
REMOVED=' Reference: NSIDC Arctic Sea Ice News. Source: https://nsidc.org/arcticseaicenews/'
@pytest.mark.parametrize('entry',ENTRIES,ids=lambda e:e['path'])
def test_exact_snapshots_and_only_declared_metadata_delta(entry):
    before=(ROOT/entry['before_path']).read_bytes()
    assert hashlib.sha256(before).hexdigest()==entry['before_sha256']
    original=json.loads(before)
    assert original['id']==entry['id']
    assert original.get('source')==entry['source_preserved']
    assert original.get('reference')==entry['reference_preserved']
    if entry['decision']!='remove_unrelated_description_reference':
        assert entry['changed_fields']==[] and 'after_path' not in entry
        assert REMOVED in original['description']
        return
    after=(ROOT/entry['after_path']).read_bytes()
    assert hashlib.sha256(after).hexdigest()==entry['after_sha256']
    revised=json.loads(after)
    assert entry['changed_fields']==['description']
    assert before.count(REMOVED.encode())==1
    assert after==before.replace(REMOVED.encode(),b'')
    assert revised['description']==original['description'].replace(REMOVED,'')
    # Whole non-description object equality covers equations, initials, units,
    # element IDs/order/roles, topology/layout, source/reference and settings.
    assert {k:v for k,v in revised.items() if k!='description'}=={k:v for k,v in original.items() if k!='description'}
    for field in ['stocks','flows','variables','tables','connectors','time_settings','source','reference','name','created_at','updated_at']:
        assert revised.get(field)==original.get(field)
    for raw in [original,revised]:
        payload={k:v for k,v in raw.items() if k not in {'description','source','reference','name','created_at','updated_at'}}
        assert hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()==entry['executable_payload_sha256']

def test_inventory_scope_and_legitimate_references_preserved():
    assert len(ENTRIES)==28 and len({e['path'] for e in ENTRIES})==28
    proposed=[e for e in ENTRIES if 'after_path' in e]
    assert len(proposed)==26==MANIFEST['proposed_removals']
    preserved={e['path']:e['decision'] for e in ENTRIES if 'after_path' not in e}
    assert preserved=={'models/climate/climate-arctic-amplification-cli.json':'preserve','models/climate/glacial-interglacial-cycle-cli.json':'defer'}
    assert len(list((D/'after/models').rglob('*.json')))==26
    assert len(list((D/'before/models').rglob('*.json')))==28
    assert all('not certified' in e['rationale'] for e in proposed)

def test_existing_provenance_warnings_are_not_removed():
    row=next(e for e in ENTRIES if 'goldstone-tilly' in e['path'])
    before=json.loads((ROOT/row['before_path']).read_text())['description']
    after=json.loads((ROOT/row['after_path']).read_text())['description']
    warning=before.split('\n\nIdentifier reconciliation',1)[1]
    assert after.endswith('\n\nIdentifier reconciliation'+warning)
    assert 'remain unverified' in after

def test_all_output_paths_are_confined_and_bibliographic_limits_explicit():
    for row in ENTRIES:
        for key in ['before_path','after_path']:
            if key not in row:continue
            path=(ROOT/row[key]).resolve()
            assert path.is_relative_to(D.resolve())
        assert row['source_check']['scope']
    assert 'not admissions' in MANIFEST['scope']
    assert 'unverified' in MANIFEST['scope']
