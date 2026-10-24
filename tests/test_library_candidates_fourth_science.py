"""Collect the exact reviewed candidate regressions and verify adopted source."""
import hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RESEARCH=ROOT/'operations/library-candidates-fourth-science'
globals().update({k:v for k,v in runpy.run_path(str(RESEARCH/'test_candidates.py')).items() if k.startswith('test_')})

def test_fourth_admission_exact_sources_and_993_unchanged():
 manifest=json.loads((ROOT/'operations/library-admissions-fourth-20261024.json').read_text())
 assert manifest['baseline_count']==993 and manifest['admitted_count']==3 and manifest['active_count']==996
 assert len(manifest['all_993_before_hashes'])==993
 for name,h in manifest['all_993_before_hashes'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
 for row in manifest['models']:
  assert (ROOT/row['file']).read_bytes()==(ROOT/row['source']).read_bytes()
  assert hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest()==row['sha256']
  assert row['sha256'] in (ROOT/row['review']).read_text()
 assert hashlib.sha256((RESEARCH/'MANIFEST.json').read_bytes()).hexdigest()==manifest['review_manifest_sha256']
