"""Exact approved metadata replacement, numerical parity and immutable history."""
import hashlib,json,shutil
from pathlib import Path
import pytest
from app.core.model import Model
from app.core.simulator import simulate
from tests.model_history import before_scope_metadata_bytes
ROOT=Path(__file__).resolve().parents[1]
M=json.loads((ROOT/"operations/library-metadata-scope-20261024.json").read_text())
def sha(data):return hashlib.sha256(data).hexdigest()

@pytest.mark.parametrize("row",M["entries"],ids=lambda r:r["id"])
def test_exact_approved_metadata_and_full_trajectory(row):
    before=(ROOT/row["archive"]).read_bytes();after=(ROOT/row["file"]).read_bytes()
    assert sha(before)==row["before_sha256"] and sha(after)==row["after_sha256"]
    assert after==(ROOT/row["source"]).read_bytes()
    a,b=json.loads(before),json.loads(after)
    assert {k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}=={"name","description","source","reference"}
    assert a["id"]==b["id"]==row["id"]
    x,y=simulate(Model(**a)),simulate(Model(**b))
    assert x.time==y.time and x.values==y.values and len(x.time)==row["points"]
    assert sha(json.dumps(dict(time=x.time,values=x.values),sort_keys=True).encode())==row["output_sha256"]
    assert before_scope_metadata_bytes(ROOT,row["file"])==before

def test_exact_1000_count_and_only_two_source_hash_changes():
    raw=(ROOT/M["baseline_public_receipt"]).read_bytes()
    assert sha(raw)==M["baseline_public_receipt_sha256"]
    old=json.loads(raw);assert old["counts"]=={"passed":1000}
    paths=list((ROOT/"models").rglob("*.json"))
    current={json.loads(p.read_text())["id"]:sha(p.read_bytes()) for p in paths}
    expected={r["id"]:r["sha256"] for r in old["models"]}
    assert len(paths)==len(current)==1000 and set(expected)==set(current)
    assert {key for key in current if current[key]!=expected[key]}=={r["id"] for r in M["entries"]}
    assert sha((ROOT/"operations/library-admissions-20261024.json").read_bytes())==M["admission_ledger_sha256"]
    assert len(M["entries"])==2 and {r["file"] for r in M["entries"]}=={"models/transportation/public-transit-ridership-service-tra.json","models/technology/shannon-communication-channel-tec.json"}
    assert M["active_count"]==1000 and M["replaced_count"]==2 and M["retired_count"]==M["admitted_count"]==0

def test_history_refuses_current_or_archive_tampering(tmp_path):
    for name in ["operations/library-metadata-scope-20261024.json",*[r[k] for r in M["entries"] for k in ["file","archive","source"]]]:
        out=tmp_path/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,out)
    row=M["entries"][0];path=tmp_path/row["file"];data=path.read_bytes()
    path.write_bytes(data+b" ")
    with pytest.raises(AssertionError):before_scope_metadata_bytes(tmp_path,row["file"])
    path.write_bytes(data);archive=tmp_path/row["archive"];archive.write_bytes(archive.read_bytes()+b" ")
    with pytest.raises(AssertionError):before_scope_metadata_bytes(tmp_path,row["file"])

def test_transit_metadata_repair_preserves_followup_and_v17_chain():
    from tests.model_history import before_quality_followup_bytes, v17_bytes
    name="models/transportation/public-transit-ridership-service-tra.json"
    old=json.loads((ROOT/"operations/library-quality-followup-20261024.json").read_text())
    row=next(r for r in old["replaced"] if r["file"]==name)
    assert before_quality_followup_bytes(ROOT,name)==(ROOT/row["archive"]).read_bytes()
    assert sha(before_quality_followup_bytes(ROOT,name))==row["before_sha256"]
    assert v17_bytes(ROOT,name)
