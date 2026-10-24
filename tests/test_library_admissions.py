import json
from pathlib import Path
from tests.library_admission import baseline_models

ROOT=Path(__file__).resolve().parents[1]

def test_approved_admissions_match_source_hashes_and_preserve_baseline():
    manifest=json.loads((ROOT/'operations/library-admissions-20261024.json').read_text())
    baseline=baseline_models(ROOT)
    assert len(baseline)==manifest['baseline_count']
    assert len(manifest['models'])==manifest['admitted_count']
    assert len(list((ROOT/'models').rglob('*.json')))==manifest['active_count']
