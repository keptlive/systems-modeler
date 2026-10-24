"""Current public audit inventory must describe exactly the served source catalog."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_public_validation_index_binds_every_tracked_model_and_engine():
    public=json.loads((ROOT/'static/library-validation.json').read_text())
    assert set(public)=={'scope','library_scope','engine_sha256','scientific_validation','counts','models'}
    assert public['scope']=='full default runs'
    assert public['counts']=={'passed':996}
    paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','models'],cwd=ROOT,text=True).splitlines() if p.endswith('.json')]
    expected={json.loads(p.read_text())['id']:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    rows=public['models']
    assert len(rows)==len(expected)==996
    assert {r['id']:r['sha256'] for r in rows}==expected
    assert all(set(r)=={'id','sha256','status'} and r['status']=='passed' for r in rows)
    assert set(public['engine_sha256'])=={str(p.relative_to(ROOT)) for p in (ROOT/'app/core').glob('*.py')}
    for name,h in public['engine_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
    text=(ROOT/'static/library-validation.json').read_text()
    assert '/tmp/' not in text and '/home/' not in text and 'private_path' not in text
def test_library_count_metadata_preserves_interface():
    text=(ROOT/'sites/library/index.html').read_text()
    assert text.count('996 curated')==8
    assert '995 curated' not in text
    editor=(ROOT/'static/index.html').read_text()
    assert editor.count('996 curated public models')==6
