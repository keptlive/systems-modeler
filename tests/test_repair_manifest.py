"""Targeted model repair must refuse changed inputs and ambiguous destinations."""
import hashlib
import json
import pytest
from scripts.apply_model_repairs import plan


def test_repair_plan_fences_all_inputs_and_identity(tmp_path):
    folder = tmp_path / "models"
    folder.mkdir()
    original = '{"id":"source","stocks":[]}'
    replacement = '{"id":"source","stocks":[{"name":"X","initial_value":1}]}'
    target = folder / "source.json"
    target.write_text(original)
    row = {"file":"models/source.json","content":replacement,
           "before_sha256":hashlib.sha256(original.encode()).hexdigest(),
           "after_sha256":hashlib.sha256(replacement.encode()).hexdigest()}
    assert len(plan(tmp_path, {"repairs":[row]})) == 1
    assert target.read_text() == original
    with pytest.raises(ValueError, match="Duplicate"):
        plan(tmp_path, {"repairs":[row,row]})
    target.write_text('{"id":"source","name":"Newer user edit"}')
    with pytest.raises(ValueError, match="changed since"):
        plan(tmp_path, {"repairs":[row]})
    target.write_text(original)
    for path in ["models/../models/source.json","/models/source.json","models/source.txt"]:
        with pytest.raises(ValueError):
            plan(tmp_path, {"repairs":[dict(row,file=path)]})
    replacement = json.dumps({"id":"different"})
    with pytest.raises(ValueError, match="identity"):
        plan(tmp_path, {"repairs":[dict(row,content=replacement,after_sha256=hashlib.sha256(replacement.encode()).hexdigest())]})
