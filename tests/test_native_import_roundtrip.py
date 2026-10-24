from fastapi.testclient import TestClient
from app.main import app
from app.storage import models as storage
from app.core.model import Model, LookupTable, TimeSettings, Variable
from app.core.xmile_generator import generate_xmile
from app.core.xmile_parser import parse_xmile
from tests.test_mdl_parser import TEACUP


def test_mdl_import_retains_original_and_caveats_through_save_edit_reload(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'MODELS_DIR', str(tmp_path))
    client = TestClient(app)
    response = client.post('/api/models/import/mdl', files={'file':('teacup.mdl', TEACUP.encode(), 'text/plain')})
    assert response.status_code == 200, response.text
    model = response.json()
    assert model['source_document']['text'] == TEACUP
    assert any(d['code']=='net_derivative_flow' for d in model['source_document']['diagnostics'])
    updated = client.put('/api/models/'+model['id'], json={'name':'Edited cooling example'})
    assert updated.status_code == 200
    reloaded = client.get('/api/models/'+model['id']).json()
    assert reloaded['source_document'] == model['source_document']
    assert reloaded['name'] == 'Edited cooling example'
    xml_roundtrip = parse_xmile(generate_xmile(Model(**reloaded)))
    assert xml_roundtrip.source_document.text == TEACUP
    assert client.post('/api/simulate', json={'model':reloaded}).status_code == 200


def test_mdl_unsupported_import_does_not_create_saved_definition(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'MODELS_DIR', str(tmp_path))
    response = TestClient(app).post('/api/models/import/mdl', files={'file':('bad.mdl', b'X[A]=2 ~ things ~ |')})
    assert response.status_code == 422
    assert list(tmp_path.iterdir()) == []


def test_xmile_unit_metadata_roundtrips_without_scale_conversion():
    model = Model(name='unit metadata', time_settings=TimeSettings(units='year'),
                  variables=[Variable(name='Input',equation='0.5',units='year')],
                  tables=[LookupTable(name='Response',points=[(0,0),(1,2)],input_units='year',output_units='person')])
    imported = parse_xmile(generate_xmile(model))
    assert imported.time_settings.units == 'year'
    assert imported.tables[0].input_units == 'year'
    assert imported.tables[0].output_units == 'person'
    assert imported.tables[0].points == model.tables[0].points
