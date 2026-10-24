"""Catalog admission and retired counterexamples have separate contracts."""
import hashlib
import json
from pathlib import Path
import pytest
from app.core.model import Model
from app.core.simulator import simulate
from app.core.failure_diagnostics import failure_payload
from app.core.validation import inspect_inputs

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / 'operations/library-curation.json').read_text())


@pytest.mark.parametrize('row', MANIFEST['retired'], ids=lambda r:r['id'])
def test_retired_evidence_is_preserved_outside_the_served_library(row):
    assert not (ROOT / row['file']).exists()
    archived = ROOT / row['archive']
    assert archived.is_relative_to(ROOT / 'tests/fixtures/retired-library')
    assert hashlib.sha256(archived.read_bytes()).hexdigest() == row['sha256']


@pytest.mark.parametrize('row', [r for r in MANIFEST['retired'] if r['classification']=='invalid_definition'], ids=lambda r:r['id'])
def test_invalid_definitions_still_produce_the_recorded_causal_failure(row):
    model = Model.model_validate_json((ROOT / row['archive']).read_bytes())
    with pytest.raises(Exception) as caught:
        simulate(model, model.time_settings.model_copy(update={'random_seed':42}))
    payload = failure_payload(caught.value)
    assert payload['code'] == row['failure_code']
    assert sorted({r['code'] for r in payload.get('root_errors',[])}) == row['root_error_codes']


def test_active_library_has_no_unreviewed_inert_structure():
    paths = list((ROOT / 'models').rglob('*.json'))
    admission_path = ROOT / 'operations/library-admissions-20261024.json'
    added = json.loads(admission_path.read_text())['admitted_count'] if admission_path.exists() else 0
    assert len(paths) == MANIFEST['active_count'] + added
    calculators = set(MANIFEST['static_calculators'])
    for path in paths:
        model = Model.model_validate_json(path.read_bytes())
        issues = inspect_inputs(model, numerical_check=False)['issues']
        codes = {i['code'] for i in issues}
        assert 'empty_model' not in codes, path
        assert 'zero_flow_definitions' not in codes, path
        if 'no_dynamic_stocks' in codes:
            assert model.id in calculators, path
            assert 'static' in model.description.lower(), path


def test_zero_flow_warning_does_not_reject_an_intentional_baseline():
    m = Model(stocks=[{'id':'x','name':'X','initial_value':10}],
              flows=[{'name':'Input','to_stock':'x','equation':'0'}])
    result = inspect_inputs(m, numerical_check=False)
    assert result['valid']
    assert 'zero_flow_definitions' in {i['code'] for i in result['issues']}
    m.flows[0].equation = 'X * 0.1'
    assert 'zero_flow_definitions' not in {i['code'] for i in inspect_inputs(m,False)['issues']}
