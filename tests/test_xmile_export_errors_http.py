"""Real export routes: expected admission is typed; unrelated errors stay errors."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.model import Model
from app.storage import models as storage


def fixture(discrete=True):
    return Model(id='export-fixture',name='Export fixture',stocks=[{'id':'x','name':'X','initial_value':.1}],flows=[{'id':'f','name':'Change','equation':'3.7*X*(1-X)-X','to_stock':'x'}],time_settings={'end':3,'dt':1,'discrete_period':1 if discrete else None})

@pytest.mark.parametrize('method',['get','post'])
def test_actual_discrete_exports_and_saved_reimport_preserve_contract(monkeypatch,tmp_path,method):
    from pathlib import Path
    from app.core.simulator import simulate
    monkeypatch.setattr(storage,'MODELS_DIR',str(tmp_path/'models'))
    m=storage.create_model(fixture());before=m.model_dump(mode='json')
    source=Path(storage.find_model_path(m.id));original_bytes=source.read_bytes()
    client=TestClient(app,raise_server_exceptions=False)
    response=client.get(f'/api/models/{m.id}/export/xmile') if method=='get' else client.post('/api/models/export/xmile',json=before)
    assert response.status_code==200
    assert response.headers['content-type'].startswith('application/xml')
    assert source.read_bytes()==original_bytes and len(list(source.parent.glob('*.json')))==1
    imported=client.post('/api/models/import/xmile',files={'file':('replay.xmile',response.text,'application/xml')})
    assert imported.status_code==200,imported.text
    restored=Model.model_validate(imported.json())
    assert restored.time_settings.model_dump()==m.time_settings.model_dump()
    fetched=client.get('/api/models/'+restored.id);assert fetched.status_code==200
    assert fetched.json()['time_settings']==before['time_settings']
    replay=client.post('/api/simulate',json={'model_id':restored.id});assert replay.status_code==200
    expected=simulate(m)
    assert replay.json()['time']==expected.time and replay.json()['values']==expected.values
    assert source.read_bytes()==original_bytes and len(list(source.parent.glob('*.json')))==2
    assert m.model_dump(mode='json')==before

@pytest.mark.parametrize('method',['get','post'])
def test_successful_xml_exports_and_missing_get_404_preserved(monkeypatch,method):
    m=fixture(False);monkeypatch.setattr(storage,'get_model',lambda key:m if key==m.id else None);client=TestClient(app)
    response=client.get(f'/api/models/{m.id}/export/xmile') if method=='get' else client.post('/api/models/export/xmile',json=m.model_dump(mode='json'))
    assert response.status_code==200
    assert response.headers['content-type'].startswith('application/xml')
    assert '<xmile' in response.text
    assert 'attachment;' in response.headers['content-disposition']
    assert client.get('/api/models/absent/export/xmile').status_code==404

@pytest.mark.parametrize('method',['get','post'])
def test_export_valueerror_detail_is_bounded_plain_text(monkeypatch,method):
    from app.core import xmile_generator
    m=fixture(False);monkeypatch.setattr(storage,'get_model',lambda key:m)
    message='<script>untrusted</script>\x00\n'+'a'*5000
    def reject(model):raise ValueError(message)
    monkeypatch.setattr(xmile_generator,'generate_xmile',reject);client=TestClient(app,raise_server_exceptions=False)
    response=client.get(f'/api/models/{m.id}/export/xmile') if method=='get' else client.post('/api/models/export/xmile',json=m.model_dump(mode='json'))
    assert response.status_code==422
    text=response.json()['detail'];assert len(text)==500
    assert text.startswith('<script>untrusted</script> ')
    assert all(ord(c)>=32 and ord(c)!=127 for c in text)
    assert response.headers['content-type'].startswith('application/json')

@pytest.mark.parametrize('error',[RuntimeError('unexpected generator bug'),TypeError('unexpected type bug')])
def test_unexpected_generator_exceptions_are_not_masked_as_admission(monkeypatch,error):
    from app.core import xmile_generator
    def fail(model):raise error
    monkeypatch.setattr(xmile_generator,'generate_xmile',fail);client=TestClient(app,raise_server_exceptions=False)
    response=client.post('/api/models/export/xmile',json=fixture(False).model_dump(mode='json'))
    assert response.status_code==500 and response.text=='Internal Server Error'

def test_empty_expected_error_has_actionable_fallback_and_model_validation_unchanged(monkeypatch):
    from app.core import xmile_generator
    def reject(model):raise ValueError('\x00\n')
    monkeypatch.setattr(xmile_generator,'generate_xmile',reject);client=TestClient(app)
    response=client.post('/api/models/export/xmile',json=fixture(False).model_dump(mode='json'))
    assert response.status_code==422 and 'use JSON' in response.json()['detail']
    malformed=fixture(False).model_dump(mode='json');malformed['time_settings']['dt']=-1
    response=client.post('/api/models/export/xmile',json=malformed)
    assert response.status_code==422 and isinstance(response.json()['detail'],list)
