"""HTTP failures keep legacy detail text and add actionable causal evidence."""
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_http_root_cause_is_distinct_from_blocked_values():
    response=client.post('/api/simulate',json={'model':{
        'stocks':[{'id':'stock','name':'Balance','initial_value':0}],
        'variables':[{'id':'dependent','name':'Result','equation':'"Bad ratio" + 1'},
                     {'id':'bad','name':'Bad ratio','equation':'1 / Balance'}],
        'time_settings':{'end':1,'dt':.25}}})
    assert response.status_code==422
    body=response.json();assert isinstance(body['detail'],str)
    failure=body['failure'];assert failure['time']==0
    assert failure['root_errors'][0]['element']=='Bad ratio'
    assert failure['root_errors'][0]['equation']=='1 / Balance'
    assert failure['root_errors'][0]['code']=='division_by_zero'
    assert failure['blocked_errors'][0]['element']=='Result'
    assert failure['blocked_errors'][0]['root_cause']['element']=='Bad ratio'
    assert failure['stock_values']=={'Balance':0}
    assert '__xmile_id_' not in body['detail']

def test_http_work_or_retention_limit_is_capacity_not_invalid_equation():
    response=client.post('/api/simulate',json={'model':{
        'variables':[{'name':'Constant','equation':'2'}],
        'time_settings':{'end':100001,'dt':1}}})
    assert response.status_code==422
    body=response.json();assert isinstance(body['detail'],str)
    assert body['failure']['category']=='capacity'
    assert body['failure']['code']=='capacity_exceeded'
