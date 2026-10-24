from tests.model_history import before_scope_metadata_bytes
"""Frozen mathematical regressions plus exact admission/history fences."""
import hashlib,importlib.util,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for batch in ('fifth-systems','sixth-control'):
 namespace=runpy.run_path(str(ROOT/'operations'/('library-candidates-'+batch)/'test_candidates.py'))
 for name,value in namespace.items():
  if name.startswith('test_') and name!='test_no_expanded_or_parameter_abstracted_duplicate':globals()['test_'+batch.replace('-','_')+'_'+name[5:]]=value

def test_exact_adoption_and_immutable_996_and_80_ledger_rows():
 a=json.loads((ROOT/'operations/library-admissions-fifth-sixth-20261024.json').read_text())
 frozen=(ROOT/'tests/fixtures/fifth-sixth-admissions-20261024/ledger-before.json').read_bytes()
 assert hashlib.sha256(frozen).hexdigest()==a['ledger_before_sha256']=='9cbb8c583e3aa369828616a3481f88e444ce47a01876d7ea7eb5828905224812'
 old=json.loads(frozen);now=json.loads((ROOT/'operations/library-admissions-20261024.json').read_text())
 assert old['admitted_count']==len(old['models'])==80 and old['active_count']==996
 assert now=={**old,'models':old['models']+a['models'],'admitted_count':84,'active_count':1000}
 assert (a['baseline_count'],a['admitted_count'],a['active_count'])==(996,4,1000)
 assert len(a['all_996_before_hashes'])==996
 for name,h in a['all_996_before_hashes'].items():assert hashlib.sha256(before_scope_metadata_bytes(ROOT,name)).hexdigest()==h
 for name,h in a['review_manifests_sha256'].items():assert hashlib.sha256(before_scope_metadata_bytes(ROOT,name)).hexdigest()==h
 assert set(a['all_996_before_hashes']).isdisjoint(r['file'] for r in a['models'])
 for r in a['models']:
  assert (ROOT/r['file']).read_bytes()==(ROOT/r['source']).read_bytes()
  assert hashlib.sha256((ROOT/r['file']).read_bytes()).hexdigest()==r['sha256']
  assert r['sha256'] in (ROOT/r['review']).read_text()
 current={str(p.relative_to(ROOT)) for p in (ROOT/'models').rglob('*.json')}
 assert current==set(a['all_996_before_hashes'])|{r['file'] for r in a['models']}
 assert len(current)==1000

def test_sixth_dedupe_preserves_exact_historical_selection_and_cross_batch_distinction():
 # Same expanded/constant-abstracted screen as frozen author test; bind its
 # historical996 catalog instead of accidentally comparing new active copies.
 folder=ROOT/'operations/library-candidates-sixth-control'
 frozen=json.loads((folder/'DEDUPE-BASELINE.json').read_text())
 a=json.loads((ROOT/'operations/library-admissions-fifth-sixth-20261024.json').read_text())
 assert frozen['all_tracked_hashes']==a['all_996_before_hashes']
 spec=importlib.util.spec_from_file_location('screen',ROOT/'operations/library-candidates-third-engineering/duplicate_screen.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
 paths=[ROOT/n for n in frozen['all_tracked_hashes']]
 paths += [p for p in (ROOT/'operations').glob('library-candidates*/*.json') if p.parent!=folder]
 known=[set(),set()]
 for p in paths:
  raw=json.loads(p.read_text())
  if not isinstance(raw,dict) or not raw.get('stocks') or not raw.get('flows'):continue
  for abstract in (False,True):
   try:known[int(abstract)].add(s.fingerprint(raw,abstract))
   except (ValueError,SyntaxError,RecursionError,TypeError):pass
 for prefix in ('finite-source-','pi-'):
  raw=json.loads(next(folder.glob(prefix+'*.json')).read_text())
  for abstract in (False,True):assert s.fingerprint(raw,abstract) not in known[int(abstract)]
