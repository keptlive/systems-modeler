import hashlib,json
import pytest
from scripts.curate_library import plan

def fixture(tmp_path):
    p=tmp_path/'models/a.json';p.parent.mkdir();p.write_text('{"id":"a"}')
    action={'file':'models/a.json','id':'a','action':'retire','before_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    return p,action

def test_plan_refuses_changed_data_and_does_not_touch_it(tmp_path):
    p,a=fixture(tmp_path);p.write_text('{"id":"a","user_edit":true}')
    before=p.read_bytes()
    with pytest.raises(ValueError,match='changed since review'):plan(tmp_path,{'actions':[a]})
    assert p.read_bytes()==before

def test_plan_never_accepts_database_or_path_escape(tmp_path):
    p,a=fixture(tmp_path)
    for name in ('models.db','models/../private.json','/tmp/models/a.json'):
        with pytest.raises(ValueError):plan(tmp_path,{'actions':[{**a,'file':name}]})
    assert p.exists()

def test_plan_requires_replacement_identity_and_hash(tmp_path):
    p,a=fixture(tmp_path)
    payload='{"id":"different"}'
    with pytest.raises(ValueError,match='identity'):
        plan(tmp_path,{'actions':[{**a,'action':'replace','content':payload,'after_sha256':hashlib.sha256(payload.encode()).hexdigest()}]})
    assert p.read_text()=='{"id":"a"}'

def test_retirement_plan_is_read_only_and_rejects_duplicates(tmp_path):
    p,a=fixture(tmp_path)
    rows=plan(tmp_path,{'actions':[a]});assert len(rows)==1 and rows[0][2] is None
    with pytest.raises(ValueError,match='Duplicate'):plan(tmp_path,{'actions':[a,a]})
    assert p.exists()
