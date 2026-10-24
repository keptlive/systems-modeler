"""Real HTTP/MCP calls and cross-process sensitivity admission/lifecycle."""
import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from mcp.server.fastmcp.exceptions import ToolError
from app.main import app
from app import sensitivity_transport as service
from app import mcp_server as server

ROOT=Path(__file__).resolve().parents[1]


def model():
    return dict(id="transport-fixture",name="Transport analytic",stocks=[dict(id="x",name="X",initial_value=3)],
                flows=[dict(id="f",name="F",equation="p*X",to_stock="x")],
                variables=[dict(id="p",name="p",equation=".4")],
                time_settings=dict(start=0,end=2,dt=.02,integration_method="rk4"))


def request():
    return dict(model=model(),parameters=[dict(id="p",step=.002)],output_stock_id="x")


@pytest.fixture(autouse=True)
def isolated_quota(tmp_path,monkeypatch):
    monkeypatch.setenv("SYSTEMS_MODELER_SENSITIVITY_QUOTA_DIR",str(tmp_path/"quota"))
    def forbid(*args,**kwargs):raise AssertionError("Sensitivity may not save or call AI")
    monkeypatch.setattr(service.storage,"create_model",forbid)
    monkeypatch.setattr(service.storage,"update_model",forbid)


def test_real_http_and_mcp_match_read_only_contract():
    raw=request();original=json.dumps(raw,sort_keys=True)
    result=TestClient(app).post("/api/sensitivity/local",json=raw)
    assert result.status_code==200
    report=result.json()
    assert report["status"]=="complete"
    assert report["rows"][0]["derivative"]==pytest.approx(6*__import__("math").exp(.8),rel=1e-6)
    async def call():
        return await server.analyze_model_sensitivity(
            parameters=raw["parameters"],output_stock_id="x",model_json=json.dumps(raw["model"]))
    other=asyncio.run(call())
    assert other["rows"]==report["rows"]
    assert other["provenance"]["normalized_model_sha256"]==report["provenance"]["normalized_model_sha256"]
    assert json.dumps(raw,sort_keys=True)==original


@pytest.mark.parametrize("change,code",[
    ({"model_id":"also"},"invalid_request"),
    ({"parameters":[dict(id="p",step=True)]},"invalid_request"),
    ({"parameters":[dict(id="p",step=0)]},"invalid_request"),
    ({"output_stock_id":"X"},"invalid_selector"),
    ({"max_work_units":1},"capacity"),
])
def test_http_typed_failures(change,code):
    raw={**request(),**change}
    response=TestClient(app).post("/api/sensitivity/local",json=raw)
    assert response.status_code==422
    assert response.json()["failure"]["code"]==code


def test_scalar_unsupported_and_model_resolution(monkeypatch):
    raw=request();raw["model"]["flows"][0]["equation"]="ABS(X)"
    assert TestClient(app).post("/api/sensitivity/local",json=raw).json()["failure"]["code"]=="unsupported_model"
    from app.core.model import Model
    monkeypatch.setattr(service.storage,"get_model",lambda key:Model(**model()) if key=="saved" else None)
    raw=request();raw.pop("model");raw["model_id"]="saved";raw["time_settings"]={"dt":.01}
    report=TestClient(app).post("/api/sensitivity/local",json=raw).json()
    assert report["status"]=="complete" and report["settings"]["dt"]==.01
    raw["model_id"]="missing"
    assert TestClient(app).post("/api/sensitivity/local",json=raw).status_code==404


def test_http_byte_and_nonfinite_bounds():
    client=TestClient(app)
    assert client.post("/api/sensitivity/local",content=b"x",headers={"content-length":"2097153"}).status_code==413
    assert client.post("/api/sensitivity/local",content=b"x"*2097153).status_code==413
    assert client.post("/api/sensitivity/local",content='{"model":NaN}').status_code==422
    assert client.post("/api/sensitivity/local",content=b"\xff").status_code==422


def child_lock():
    code="from app.sensitivity_transport import deployment_quota; import time;\nwith deployment_quota():\n print('ready',flush=True); time.sleep(30)"
    p=subprocess.Popen([sys.executable,"-c",code],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=os.environ.copy())
    assert p.stdout.readline().strip()=="ready"
    return p


def test_cross_process_slot_shared_by_real_http_and_mcp_then_crash_releases():
    p=child_lock()
    try:
        response=TestClient(app).post("/api/sensitivity/local",json=request())
        assert response.status_code==429
        assert response.json()["failure"]["code"]=="sensitivity_busy"
        async def busy():
            with pytest.raises(ToolError) as exc:
                await server.analyze_model_sensitivity(parameters=request()["parameters"],output_stock_id="x",model_json=model())
            assert json.loads(str(exc.value))["failure"]["code"]=="sensitivity_busy"
        asyncio.run(busy())
    finally:
        p.terminate();p.wait(timeout=3)
    with service.deployment_quota():pass
    assert TestClient(app).post("/api/sensitivity/local",json=request()).json()["status"]=="complete"


@pytest.mark.parametrize("kind",["directory_symlink","file_symlink","hardlink","directory_mode","file_mode"])
def test_insecure_quota_is_fail_closed(kind,tmp_path):
    quota=Path(os.environ["SYSTEMS_MODELER_SENSITIVITY_QUOTA_DIR"])
    if kind=="directory_symlink":
        target=tmp_path/"target";target.mkdir(mode=0o700);quota.symlink_to(target,target_is_directory=True)
    else:
        quota.mkdir(mode=0o700)
        lock=quota/"slot.lock"
        if kind=="file_symlink":
            target=tmp_path/"target";target.write_text("unchanged");lock.symlink_to(target)
        elif kind=="hardlink":
            target=tmp_path/"target";target.write_text("unchanged");target.chmod(0o600);os.link(target,lock)
        elif kind=="directory_mode":quota.chmod(0o755)
        elif kind=="file_mode":lock.write_text("");lock.chmod(0o644)
    response=TestClient(app).post("/api/sensitivity/local",json=request())
    assert response.status_code==503
    assert response.json()["failure"]["code"]=="quota_unavailable"


def test_cancelled_transport_holds_quota_until_thread_cleanup(monkeypatch):
    started=threading.Event();cleaned=threading.Event()
    def controlled(*args,cancel_event=None,**kwargs):
        started.set()
        assert cancel_event.wait(2)
        time.sleep(.05)
        cleaned.set()
        return {"status":"cancelled"}
    monkeypatch.setattr(service,"analyze_local_sensitivity",controlled)
    async def exercise():
        from app.core.model import Model
        task=asyncio.create_task(service.run_sensitivity(Model(**model()),request()["parameters"],"x"))
        while not started.is_set():await asyncio.sleep(.005)
        task.cancel()
        await asyncio.sleep(.01)
        with pytest.raises(service.SensitivityTransportError) as exc:
            with service.deployment_quota():pass
        assert exc.value.code=="sensitivity_busy"
        with pytest.raises(asyncio.CancelledError):await task
        assert cleaned.is_set()
        with service.deployment_quota():pass
    asyncio.run(exercise())


def test_http_disconnect_cancels_real_worker_and_releases_slot():
    from fastapi import FastAPI
    small=FastAPI();small.include_router(service.router,prefix="/api")
    messages=[];first=True;disconnect_at=time.monotonic()+.03
    async def receive():
        nonlocal first
        if first:
            first=False
            return {"type":"http.request","body":json.dumps(request()).encode(),"more_body":False}
        if time.monotonic()>=disconnect_at:
            return {"type":"http.disconnect"}
        await asyncio.sleep(10)
        return {"type":"http.disconnect"}
    async def send(message):messages.append(message)
    async def exercise():
        await small({"type":"http","asgi":{"version":"3.0"},"http_version":"1.1",
                     "method":"POST","scheme":"http","path":"/api/sensitivity/local",
                     "raw_path":b"/api/sensitivity/local","query_string":b"","headers":[],
                     "client":("127.0.0.1",1),"server":("test",80)},receive,send)
    asyncio.run(exercise())
    bodies=b"".join(m.get("body",b"") for m in messages if m["type"]=="http.response.body")
    assert json.loads(bodies)["status"]=="cancelled"
    with service.deployment_quota():pass


def test_mcp_registration_and_existing_routes_remain():
    async def exercise():
        tools={t.name:t for t in await server.mcp.list_tools()}
        tool=tools["analyze_model_sensitivity"]
        assert tool.annotations.readOnlyHint and not tool.annotations.destructiveHint
        assert {"simulate_model","analyze_model_feedback","open_workspace"}<=tools.keys()
        result=await server.mcp.call_tool("analyze_model_sensitivity",
                    {"parameters":[{"id":"p","step":.002}],"output_stock_id":"x","model_json":model()})
        assert result
    asyncio.run(exercise())
    routes=set(app.openapi()["paths"])|{getattr(r,"path",None) for r in app.routes}
    assert {"/api/simulate","/api/feedback","/api/analyze","/api/sensitivity/local","/","/guide","/mcp"}<=routes


def test_real_stdio_mcp_client_sensitivity():
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    async def exercise():
        args=StdioServerParameters(command=sys.executable,args=["-m","app.mcp_server"],cwd=str(ROOT),env=os.environ.copy())
        async with stdio_client(args) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                listed=await session.list_tools()
                assert "analyze_model_sensitivity" in {t.name for t in listed.tools}
                response=await session.call_tool("analyze_model_sensitivity",
                    dict(parameters=[dict(id="p",step=.002)],output_stock_id="x",model_json=model()))
                assert not response.isError,response.content
                report=response.structuredContent or json.loads(response.content[0].text)
                assert report["status"]=="complete" and report["provenance"]
                bad=await session.call_tool("analyze_model_sensitivity",
                    dict(parameters=[dict(id="p",step=0)],output_stock_id="x",model_json=model()))
                assert bad.isError
    asyncio.run(exercise())


def test_http_deadline_status_has_provenance_and_releases_shared_slot():
    raw={**request(),"timeout_seconds":.001}
    response=TestClient(app).post("/api/sensitivity/local",json=raw)
    assert response.status_code==200
    report=response.json()
    assert report["status"]=="deadline_exceeded" and report["provenance"]
    assert "rows" not in report
    with service.deployment_quota():pass


def test_http_baseline_failure_is_explicit_and_not_a_zero_derivative():
    raw=request();raw["model"]["flows"][0]["equation"]="1/(p-.4)"
    response=TestClient(app).post("/api/sensitivity/local",json=raw)
    assert response.status_code==200
    report=response.json()
    assert report["status"]=="baseline_failed"
    assert report["rows"]==[] and report["error"] and report["provenance"]


def test_worker_infrastructure_error_is_distinct_and_releases_quota(monkeypatch):
    def fail(*args,**kwargs):raise OSError("injected")
    monkeypatch.setattr(service,"analyze_local_sensitivity",fail)
    response=TestClient(app).post("/api/sensitivity/local",json=request())
    assert response.status_code==503
    assert response.json()["failure"]["code"]=="worker_unavailable"
    with service.deployment_quota():pass


def test_nonfinite_and_oversize_mcp_input_rejected_before_worker(monkeypatch):
    def fail(*args,**kwargs):raise AssertionError("execution must not begin")
    monkeypatch.setattr(service,"analyze_local_sensitivity",fail)
    async def exercise():
        for raw in ['{"name":NaN}',{"description":"x"*2097153}]:
            with pytest.raises(ToolError):
                await server.analyze_model_sensitivity(parameters=[dict(id="p",step=.1)],output_stock_id="x",model_json=raw)
    asyncio.run(exercise())


def test_lock_inode_is_persistent_and_no_follow_parent_path(tmp_path,monkeypatch):
    with service.deployment_quota():pass
    path=Path(os.environ["SYSTEMS_MODELER_SENSITIVITY_QUOTA_DIR"])/"slot.lock"
    inode=path.stat().st_ino
    with service.deployment_quota():pass
    assert path.stat().st_ino==inode
    linked=tmp_path/"linked";linked.symlink_to(path.parent,target_is_directory=True)
    monkeypatch.setenv("SYSTEMS_MODELER_SENSITIVITY_QUOTA_DIR",str(linked/"nested"))
    with pytest.raises(service.SensitivityTransportError) as exc:
        with service.deployment_quota():pass
    assert exc.value.code=="quota_unavailable"


@pytest.mark.parametrize("location",["root","stock","flow","variable","position","settings"])
def test_unknown_raw_semantic_fields_reject_http_and_mcp(location):
    raw=model()
    target={
        "root":raw,"stock":raw["stocks"][0],"flow":raw["flows"][0],
        "variable":raw["variables"][0],"settings":raw["time_settings"],
    }
    if location=="position":
        raw["stocks"][0]["position"]={}
        modified=raw["stocks"][0]["position"]
    else:modified=target[location]
    modified["events"]=[{"when":"X>1","set":"X=0"}]
    response=TestClient(app).post("/api/sensitivity/local",json={**request(),"model":raw})
    assert response.status_code==422
    assert response.json()["failure"]["code"]=="invalid_request"
    assert "Unknown fields" in response.json()["detail"]
    async def exercise():
        with pytest.raises(ToolError) as exc:
            await server.analyze_model_sensitivity(parameters=request()["parameters"],output_stock_id="x",model_json=raw)
        assert json.loads(str(exc.value))["failure"]["code"]=="invalid_request"
        assert "Unknown fields" in str(exc.value)
    asyncio.run(exercise())


def test_declared_arbitrary_source_diagnostics_are_preserved():
    raw=model()
    raw["source_document"]={"format":"vensim_mdl","text":"retained source",
                            "diagnostics":[{"custom":{"events":"metadata only","nested":[1,2,3]}}]}
    resolved=service.resolve_sensitivity_model(model_json=raw)
    assert resolved.source_document.diagnostics==raw["source_document"]["diagnostics"]
    response=TestClient(app).post("/api/sensitivity/local",json={**request(),"model":raw})
    assert response.status_code==200 and response.json()["status"]=="complete"


def test_unknown_source_document_schema_key_rejects_but_not_diagnostic_maps():
    raw=model();raw["source_document"]={"format":"vensim_mdl","text":"source","events":[]}
    response=TestClient(app).post("/api/sensitivity/local",json={**request(),"model":raw})
    assert response.status_code==422 and "source_document" in response.json()["detail"]


def test_unknown_time_settings_patch_is_already_rejected():
    response=TestClient(app).post("/api/sensitivity/local",
                                 json={**request(),"time_settings":{"events":[]}})
    assert response.status_code==422
