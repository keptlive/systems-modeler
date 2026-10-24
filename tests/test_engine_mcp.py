"""Read-only MCP registration and native engine execution contract."""
import asyncio
import json
import pytest
from mcp.server.fastmcp.exceptions import ToolError
from app import mcp_server as server
from app.core.model import Model
from app.core.simulator import simulate

def model():
    return {"name":"native MCP","stocks":[{"id":"x","name":"X","initial_value":10,"units":"person"}],
        "flows":[{"name":"Growth","equation":"X * rate","to_stock":"x","units":"person/year"}],
        "variables":[{"name":"rate","equation":"0.1","units":"1/year"}],
        "time_settings":{"start":0,"end":1,"dt":0.25,"units":"year"}}

def forbid(*args,**kwargs):
    raise AssertionError("Read-only native tools must not simulate or save")

@pytest.fixture(autouse=True)
def no_hidden_simulation_or_writes(monkeypatch):
    monkeypatch.setattr(server,"simulate",forbid)
    monkeypatch.setattr(server.storage,"create_model",forbid)
    monkeypatch.setattr(server.storage,"update_model",forbid)

def test_compile_and_units_preserve_source_and_select_saved_models(monkeypatch):
    raw=model()
    assert server.compile_model_structure(model_json=json.dumps(raw))["model"]["stocks"][0]["name"]=="X"
    monkeypatch.setattr(server.storage,"get_model",lambda ident:Model.model_validate(raw) if ident=="existing" else None)
    checked=server.check_model_units(model_id="existing")
    assert not checked["errors"]
    for args in ({},{"model_id":"existing","model_json":raw},{"model_id":"missing"}):
        with pytest.raises(ToolError):server.compile_model_structure(**args)

def test_native_array_compilation_and_error_diagnostics():
    raw=model()
    raw["dimensions"]=[{"name":"Region","elements":["North","South"]}]
    raw["stocks"][0].update(dimensions=["Region"])
    raw["flows"][0].update(dimensions=["Region"],to_stock="X[Region]")
    compiled=server.compile_model_structure(model_json=raw)
    assert len(compiled["model"]["stocks"])==2
    raw["stocks"][0]["dimensions"]=["Missing"]
    with pytest.raises(ToolError) as exc:server.compile_model_structure(model_json=raw)
    error=json.loads(str(exc.value))["failure"]
    assert error["code"]=="invalid_shape"
    assert error["diagnostics"][0]["severity"]=="error"

def test_feedback_requires_explicit_trajectory_and_never_runs_simulation():
    raw=model()
    result=simulate(Model.model_validate(raw))
    feedback=server.analyze_model_feedback(result_json=result.model_dump(mode="json"),model_json=raw,sample_count=2)
    assert len(feedback["samples"])==2
    assert feedback["samples"][0]["jacobian"][0][0]==pytest.approx(.1,rel=1e-5)
    from app.core.diagnostics import model_hash
    result.integration_diagnostics={"normalized_model_sha256":model_hash(Model.model_validate(raw))}
    raw["flows"][0]["equation"]="X * rate * 2"
    with pytest.raises(ToolError):
        server.analyze_model_feedback(result_json=result.model_dump(mode="json"),model_json=raw)

def test_import_mdl_returns_draft_with_exact_source_and_warnings():
    source="Stock=INTEG(-Stock/10,100) ~ kg ~ | FINAL TIME=1 ~ year ~ | TIME STEP=.25 ~ year ~ |"
    result=server.import_mdl_model(source)
    assert result["model"]["source_document"]["text"]==source
    assert result["model"]["source_document"]["diagnostics"]==result["diagnostics"]
    assert any(d["code"]=="net_derivative_flow" for d in result["diagnostics"])
    with pytest.raises(ToolError) as exc:server.import_mdl_model("Stock[D]=1 ~~|")
    assert json.loads(str(exc.value))["failure"]["diagnostics"][0]["severity"]=="error"

@pytest.mark.parametrize("value",["[1]","{",'{ "name": NaN }',{"name":"x"*2_097_153}])
def test_json_forms_have_explicit_byte_and_finiteness_bounds(value):
    with pytest.raises(ToolError):server.compile_model_structure(model_json=value)

def test_feedback_rejects_nonfinite_and_oversized_json():
    with pytest.raises(ToolError):server.analyze_model_feedback(result_json='{"time":[NaN],"values":{}}',model_json=model())
    with pytest.raises(ToolError):server.analyze_model_feedback(result_json=" "*8_388_609,model_json=model())

def test_real_fastmcp_registration_annotations_and_dispatch():
    async def exercise():
        listed=await server.mcp.list_tools()
        names={t.name:t for t in listed}
        required={"compile_model_structure","check_model_units","analyze_model_feedback","import_mdl_model"}
        assert required <= names.keys()
        assert {"simulate_model","list_models","open_workspace","export_model_xmile"} <= names.keys()
        for name in required:
            assert names[name].annotations.readOnlyHint
            assert not names[name].annotations.destructiveHint
        result=await server.mcp.call_tool("compile_model_structure",{"model_json":model()})
        assert result
        with pytest.raises(ToolError):
            await server.mcp.call_tool("analyze_model_feedback",{"model_json":model()})
    asyncio.run(exercise())



def test_real_stdio_mcp_client_new_tools():
    import sys
    from pathlib import Path
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    def payload(response):
        assert not response.isError, response.content
        return response.structuredContent or json.loads(response.content[0].text)
    async def exercise():
        params=StdioServerParameters(command=sys.executable,args=["-m","app.mcp_server"],cwd=str(Path(__file__).resolve().parents[1]))
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                tools=await session.list_tools()
                assert {"compile_model_structure","check_model_units","analyze_model_feedback","import_mdl_model"} <= {t.name for t in tools.tools}
                compiled=payload(await session.call_tool("compile_model_structure",{"model_json":json.dumps(model())}))
                assert compiled["model"]["stocks"][0]["name"]=="X"
                assert not payload(await session.call_tool("check_model_units",{"model_json":model()}))["errors"]
                result=simulate(Model.model_validate(model())).model_dump(mode="json")
                feedback=payload(await session.call_tool("analyze_model_feedback",{"model_json":model(),"result_json":result,"sample_count":1}))
                assert len(feedback["samples"])==1
                imported=payload(await session.call_tool("import_mdl_model",{"mdl_text":"x=2 ~~|"}))
                assert imported["model"]["source_document"]["text"]=="x=2 ~~|"
                invalid=await session.call_tool("import_mdl_model",{"mdl_text":"x=DELAY1(1,2) ~~|"})
                assert invalid.isError
    asyncio.run(exercise())
