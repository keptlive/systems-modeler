"""Historical recovery must verify both sides of the follow-up transaction."""
import hashlib
import json
from pathlib import Path

import pytest
from tests.model_history import before_quality_followup_bytes, v17_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_every_followup_archive_recovers_original_bytes():
    manifest = json.loads((ROOT / 'operations/library-quality-followup-20261024.json').read_text())
    for row in manifest['replaced'] + manifest['retired']:
        raw = before_quality_followup_bytes(ROOT, row['file'])
        assert hashlib.sha256(raw).hexdigest() == row['before_sha256']
        assert v17_bytes(ROOT, row['file'])


@pytest.mark.parametrize('corruption', ['current', 'archive', 'retired_reappears'])
def test_recovery_rejects_corrupt_transaction_bytes(tmp_path, corruption):
    current = tmp_path / 'models/example.json'
    archive = tmp_path / 'tests/fixtures/quality-followup-20261024/example.json'
    current.parent.mkdir(parents=True)
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b'original')
    row = dict(file='models/example.json', archive=str(archive.relative_to(tmp_path)),
               before_sha256=hashlib.sha256(b'original').hexdigest(),
               after_sha256=hashlib.sha256(b'current').hexdigest())
    manifest = dict(replaced=[row], retired=[])
    current.write_bytes(b'current')
    if corruption == 'current':
        current.write_bytes(b'corrupt')
    elif corruption == 'archive':
        archive.write_bytes(b'corrupt')
    else:
        manifest = dict(replaced=[], retired=[row])
    (tmp_path / 'operations').mkdir()
    (tmp_path / 'operations/library-quality-followup-20261024.json').write_text(json.dumps(manifest))
    with pytest.raises(AssertionError):
        before_quality_followup_bytes(tmp_path, row['file'])
