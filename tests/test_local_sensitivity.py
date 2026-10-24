"""Independent analytic references and admission/resource/lifecycle checks."""
import json
import math
import multiprocessing
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from app.core.equations import EquationError
from app.core.model import Model
from app.core.simulator import simulate
from app.core.local_sensitivity import (
    analyze_local_sensitivity, LocalSensitivityError, _admit, _row, _worker,
)


def growth(method="rk4", initializer=False):
    return Model(id="fixture",name="Local sensitivity fixture",
        stocks=[dict(id="x",name="Population",initial_value=3,
                     equation="scale" if initializer else "",units="people")],
        flows=[dict(id="g",name="Growth",equation="rate*Population",to_stock="x",units="people/time")],
        variables=[dict(id="p",name="rate",equation="0.4",units="1/time"),
                   dict(id="a",name="scale",equation="3",units="people")],
        time_settings=dict(start=5,end=7,dt=.02,integration_method=method))


@pytest.mark.parametrize("method",["euler","rk4"])
@pytest.mark.parametrize("initializer",[False,True])
def test_native_derivative_matches_independent_discrete_and_continuous_references(method,initializer):
    m=growth(method,initializer);original=m.model_dump_json()
    r=analyze_local_sensitivity(m,[dict(id="p",step=.002)],"x")
    assert r["status"]=="complete" and r["completed_runs"]==5
    z=.4*.02;n=100
    if method=="euler":
        R=1+z;dR=1
    else:
        R=1+z+z*z/2+z**3/6+z**4/24
        dR=1+z+z*z/2+z**3/6
    derivative=3*n*R**(n-1)*.02*dR
    assert r["rows"][0]["derivative"]==pytest.approx(derivative,rel=1e-6)
    assert r["rows"][0]["derivative"]==pytest.approx(6*math.exp(.8),rel=.012 if method=="euler" else 1e-6)
    assert r["settings"]["start"]==5 and r["requested_end"]==7
    assert r["charged_reserved_work"]==r["reservation"]["total_reserved_work"]
    assert r["successful_engine_work"]<=r["charged_reserved_work"]
    assert m.model_dump_json()==original
    assert r["provenance"]["sensitivity_sha256"]


def test_initializer_reevaluates_changed_parameter_and_order_is_preserved():
    m=growth(initializer=True)
    r=analyze_local_sensitivity(m,[dict(id="a",step=.002),dict(id="p",step=.002)],"x")
    assert [row["parameter_id"] for row in r["rows"]]==["a","p"]
    assert r["rows"][0]["derivative"]==pytest.approx(math.exp(.8),rel=1e-8)
    assert r["completed_runs"]==9


def test_zero_constant_and_zero_output_have_defined_raw_derivative():
    m=growth("euler");m.variables[0].equation="0";m.stocks[0].initial_value=0
    m.flows[0].equation="rate"
    r=analyze_local_sensitivity(m,[dict(id="p",step=.01)],"x")
    row=r["rows"][0]
    assert row["derivative"]==pytest.approx(2)
    assert row["elasticity"] is None
    assert row["elasticity_undefined_reason"]=="zero_baseline_output"


@pytest.mark.parametrize("method",["euler","rk4"])
def test_exact_reservation_boundary_and_actual_work(method):
    m=growth(method,True)
    selected=[dict(id="p",step=.002)]
    _,_,_,reservation=_admit(m,selected,"x",2_000_000)
    bound=reservation["total_reserved_work"]
    with pytest.raises(LocalSensitivityError,match="reservation"):
        analyze_local_sensitivity(m,selected,"x",max_work_units=bound-1)
    r=analyze_local_sensitivity(m,selected,"x",max_work_units=bound)
    ordinary=(100*(5 if method=="rk4" else 1)+1)*4
    assert r["successful_engine_work"]==ordinary*5
    assert r["charged_reserved_work"]==(ordinary+16)*5


@pytest.mark.parametrize("equation",[
    "ABS(Population)","MIN(1,Population)","IF_THEN_ELSE(Population>1,1,0)",
    "RANDOM_UNIFORM(0,1)","SMOOTH(Population,2)","STEP(1,2)","TIME",
    "Population%2","Population//2","Population^0.5","Population^-1",
    "LOOKUP(Population,0,0,1,1)",
])
def test_unsupported_grammar_rejected_before_worker(equation,monkeypatch):
    m=growth();m.flows[0].equation=equation
    def forbidden(*args):raise AssertionError("worker context created")
    monkeypatch.setattr("app.core.local_sensitivity.multiprocessing.get_context",forbidden)
    with pytest.raises(LocalSensitivityError):
        analyze_local_sensitivity(m,[dict(id="p",step=.01)],"x")


@pytest.mark.parametrize("entry",[
    {"id":"p","step":True},{"id":"p","step":0},{"id":"p","step":float("nan")},
    {"id":"p","step":float("inf")},{"id":"missing","step":.1},
    {"id":"rate","step":.1},{"id":"p","step":.1,"extra":1},
])
def test_invalid_selectors_and_steps(entry):
    with pytest.raises(LocalSensitivityError):
        analyze_local_sensitivity(growth(),[entry],"x")


def test_duplicate_ids_and_names_and_cycles_rejected():
    for mutate in [
        lambda m:setattr(m.variables[1],"id","p"),
        lambda m:setattr(m.variables[1],"name","RATE"),
        lambda m:setattr(m.variables[1],"equation","scale"),
        lambda m:setattr(m.flows[0],"to_stock","absent"),
    ]:
        m=growth();mutate(m)
        with pytest.raises(LocalSensitivityError):
            analyze_local_sensitivity(m,[dict(id="p",step=.01)],"x")


def test_parameter_must_be_numeric_literal_not_constant_expression():
    m=growth();m.variables[0].equation="1/2"
    with pytest.raises(LocalSensitivityError,match="literal"):
        analyze_local_sensitivity(m,[dict(id="p",step=.01)],"x")


def test_geometry_rejection_and_real_displacements():
    m=growth();m.variables[0].equation="1e16"
    with pytest.raises(LocalSensitivityError,match="geometry"):
        analyze_local_sensitivity(m,[dict(id="p",step=3)],"x")
    p=1e8;h=.1;points=[p-h,p-h/2,p+h/2,p+h]
    row=_row(dict(baseline=p,points=points),0,[v-p for v in points])
    assert row["derivative"]==pytest.approx(1,abs=1e-14)


@pytest.mark.parametrize("scale",[1e-25,1.,1e25])
def test_diagnostics_are_output_scale_invariant(scale):
    row=_row(dict(baseline=0,points=[-.1,-.05,.05,.1]),0,[scale*.1,scale*.05,scale*.05,scale*.1])
    assert row["one_sided_disagreement"]==2
    assert row["status"]=="unstable_or_nonsmooth"


class Capture:
    def send_bytes(self,result):self.result=json.loads(result)
    def close(self):pass


@pytest.mark.parametrize("method",["euler","rk4"])
def test_failed_perturbations_charge_full_reservation_and_never_fake_derivatives(method):
    m=growth(method);m.flows[0].equation="1/(rate-0.402)"
    # Outer plus sample fails, baseline and inner samples are valid.
    snapshot,selected,_,reservation=_admit(m,[dict(id="p",step=.002)],"x",2_000_000)
    sink=Capture()
    _worker(sink,snapshot.model_dump(mode="json"),selected,"x",reservation)
    r=sink.result
    assert r["status"]=="partial_failure"
    assert r["attempted_runs"]==5 and r["completed_runs"]==4
    assert r["charged_reserved_work"]==reservation["total_reserved_work"]
    assert r["rows"][0]["status"]=="failed"
    assert "derivative" not in r["rows"][0]


def test_baseline_failure_aborts_before_perturbations():
    m=growth();m.flows[0].equation="1/(rate-0.4)"
    snapshot,selected,_,reservation=_admit(m,[dict(id="p",step=.002)],"x",2_000_000)
    sink=Capture();_worker(sink,snapshot.model_dump(mode="json"),selected,"x",reservation)
    assert sink.result["status"]=="baseline_failed"
    assert sink.result["attempted_runs"]==1 and sink.result["rows"]==[]


def test_cancelled_before_start_does_not_create_process():
    event=threading.Event();event.set()
    r=analyze_local_sensitivity(growth(),[dict(id="p",step=.01)],"x",cancel_event=event)
    assert r["status"]=="cancelled" and r["charged_reserved_work"]==0


def test_deadline_stops_worker_and_next_job_succeeds():
    before={p.pid for p in multiprocessing.active_children()}
    r=analyze_local_sensitivity(growth(),[dict(id="p",step=.01)],"x",timeout_seconds=.001)
    assert r["status"]=="deadline_exceeded" and "rows" not in r
    assert {p.pid for p in multiprocessing.active_children()}==before
    assert analyze_local_sensitivity(growth(),[dict(id="p",step=.01)],"x")["status"]=="complete"


def test_cancel_running_worker_and_concurrent_waiter():
    event=threading.Event()
    before={p.pid for p in multiprocessing.active_children()}
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(analyze_local_sensitivity,growth(),[dict(id="p",step=.01)],"x",cancel_event=event)
        time.sleep(.02);event.set()
        r=first.result(timeout=5)
    assert r["status"]=="cancelled" and "rows" not in r
    assert {p.pid for p in multiprocessing.active_children()}==before


def test_queue_deadline_does_not_charge_unstarted_work(monkeypatch):
    lock=threading.BoundedSemaphore(1);lock.acquire()
    monkeypatch.setattr("app.core.local_sensitivity._WORKER_SLOT",lock)
    r=analyze_local_sensitivity(growth(),[dict(id="p",step=.01)],"x",timeout_seconds=.01)
    assert r["status"]=="deadline_exceeded" and r["charged_reserved_work"]==0
    lock.release()


def test_retained_values_and_ast_text_are_bounded():
    m=growth();m.time_settings.dt=.0001
    with pytest.raises(LocalSensitivityError):
        analyze_local_sensitivity(m,[dict(id="p",step=.01)],"x")
    m=growth();m.flows[0].equation="1+"*17000+"1"
    with pytest.raises(LocalSensitivityError):
        analyze_local_sensitivity(m,[dict(id="p",step=.01)],"x")


@pytest.mark.parametrize("method",["euler","rk4"])
@pytest.mark.parametrize("failing",[False,True])
def test_reservation_covers_measured_equation_attempts_and_engine_charge(method,failing,monkeypatch):
    import app.core.integration as engine
    m=growth(method,True)
    # Both initializer and ordinary auxiliary dependencies authored backwards.
    from app.core.model import Variable
    m.variables.insert(0,Variable(id="b",name="Dependent",equation="rate+scale"))
    m.stocks[0].equation="Dependent"
    if failing:
        m.flows[0].equation="1/(rate-0.4)"
    _,_,_,bound=_admit(m,[dict(id="p",step=.002)],"x",2_000_000)
    real=engine.safe_eval;attempts=[]
    def counted(*args,**kwargs):
        attempts.append(1)
        return real(*args,**kwargs)
    monkeypatch.setattr(engine,"safe_eval",counted)
    if failing:
        with pytest.raises(EquationError):
            simulate(m)
    else:
        simulate(m)
    assert len(attempts)<=bound["per_run_reserved_work"]
    # Each successful stage evaluates variables/flows once; initialization also
    # evaluates the one stock initializer. No forward-DAG retries are hidden.
    if not failing:
        assert len(attempts)==(100*(5 if method=="rk4" else 1)+1)*4+1


def test_negative_unicode_literal_and_builtin_constant_shadowing():
    m=growth()
    m.variables[0].name="π rate";m.variables[0].equation="-0.4"
    m.flows[0].equation='"π rate"*Population'
    result=analyze_local_sensitivity(m,[dict(id="p",step=.002)],"x")
    assert result["status"]=="complete"
    assert result["rows"][0]["derivative"]==pytest.approx(6*math.exp(-.8),rel=1e-6)
    m.variables[1].name="e"
    m.flows[0].equation='"π rate"*Population+0*e'
    assert analyze_local_sensitivity(m,[dict(id="p",step=.002)],"x")["status"]=="complete"


def test_stock_output_requires_id_even_when_name_is_unique():
    with pytest.raises(LocalSensitivityError,match="stock ID"):
        analyze_local_sensitivity(growth(),[dict(id="p",step=.002)],"Population")


def test_partial_last_interval_endpoint_is_exact():
    m=growth();m.time_settings.dt=.3
    r=analyze_local_sensitivity(m,[dict(id="p",step=.002)],"x")
    assert r["status"]=="complete" and r["requested_end"]==7
    assert r["reservation"]["sample_points"]==8


def test_process_start_failure_releases_concurrency_slot(monkeypatch):
    import app.core.local_sensitivity as service
    original=service.multiprocessing.get_context
    def fail(*args):raise OSError("injected process setup failure")
    monkeypatch.setattr(service.multiprocessing,"get_context",fail)
    with pytest.raises(OSError):
        analyze_local_sensitivity(growth(),[dict(id="p",step=.002)],"x")
    monkeypatch.setattr(service.multiprocessing,"get_context",original)
    assert analyze_local_sensitivity(growth(),[dict(id="p",step=.002)],"x")["status"]=="complete"


def test_two_simultaneous_requests_use_one_worker_slot(monkeypatch):
    import app.core.local_sensitivity as service
    original=service.multiprocessing.get_context
    guard=threading.Lock();current=0;peak=0
    class TrackedProcess:
        def __init__(self,real):self.real=real;self.counted=False
        def start(self):
            nonlocal current,peak
            self.real.start()
            with guard:
                current+=1;peak=max(peak,current);self.counted=True
        def join(self,*args,**kwargs):
            nonlocal current
            self.real.join(*args,**kwargs)
            if not self.real.is_alive() and self.counted:
                with guard:current-=1;self.counted=False
        def __getattr__(self,key):return getattr(self.real,key)
    class Context:
        def __init__(self,real):self.real=real
        def Pipe(self,*args,**kwargs):return self.real.Pipe(*args,**kwargs)
        def Process(self,*args,**kwargs):return TrackedProcess(self.real.Process(*args,**kwargs))
    monkeypatch.setattr(service.multiprocessing,"get_context",lambda *args:Context(original(*args)))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(analyze_local_sensitivity,growth(),[dict(id="p",step=.002)],"x") for _ in range(2)]
        assert all(f.result(timeout=10)["status"]=="complete" for f in futures)
    assert peak==1 and current==0


def test_result_geometry_diagnostics_survive_output_and_parameter_units():
    p=2.;h=.01
    first=_row(dict(baseline=p,points=[p-h,p-h/2,p+h/2,p+h]),p**3,
               [(p-h)**3,(p-h/2)**3,(p+h/2)**3,(p+h)**3])
    a,b=1e-15,1e4
    second=_row(dict(baseline=p*b,points=[(p-h)*b,(p-h/2)*b,(p+h/2)*b,(p+h)*b]),a*p**3,
                [a*(p-h)**3,a*(p-h/2)**3,a*(p+h/2)**3,a*(p+h)**3])
    assert second["derivative"]==pytest.approx(first["derivative"]*a/b,rel=1e-10)
    assert second["refinement_disagreement"]==pytest.approx(first["refinement_disagreement"],abs=1e-11)
    assert second["elasticity"]==pytest.approx(first["elasticity"],rel=1e-10)


@pytest.mark.parametrize("method",["euler","rk4"])
def test_exact_success_accounting_matches_engine_reserved_work(method,monkeypatch):
    import app.core.integration as engine
    original=engine.RandomRuntime.reserve_work;calls=[]
    def tracked(self,work):
        calls.append(work)
        return original(self,work)
    monkeypatch.setattr(engine.RandomRuntime,"reserve_work",tracked)
    m=growth(method,True)
    _,_,_,bound=_admit(m,[dict(id="p",step=.002)],"x",2_000_000)
    simulate(m)
    assert calls and max(calls)==bound["per_run_success_work"]


@pytest.mark.parametrize("feature",["discrete","radau","report","structure","names","duplicate_parameter"])
def test_other_unsupported_models(feature):
    m=growth()
    if feature=="discrete":
        m.time_settings.discrete_period=.02;m.time_settings.integration_method="euler"
    elif feature=="radau":m.time_settings.integration_method="radau"
    elif feature=="report":m.variables[1].role="report"
    elif feature=="structure":m.dimensions=[{"name":"R","elements":["A"]}]
    elif feature=="names":m.variables[0].name="x"*129
    parameters=[dict(id="p",step=.002)]
    if feature=="duplicate_parameter":parameters*=2
    with pytest.raises(LocalSensitivityError):
        analyze_local_sensitivity(m,parameters,"x")


def test_scale_safe_extreme_stencil_and_stationary_warning():
    row=_row(dict(baseline=0.,points=[-1e308,-5e307,5e307,1e308]),0.,
             [-1e308,-5e307,5e307,1e308])
    assert row["derivative"]==pytest.approx(1.)
    row=_row(dict(baseline=0.,points=[-.1,-.05,.05,.1]),0.,
             [.01,.0025,.0025,.01])
    assert row["derivative"]==0 and row["status"]=="unstable_or_nonsmooth"


def _partial_frame_worker(send,*args):
    import os,struct
    os.write(send.fileno(),struct.pack("!i",100)+b"x")
    time.sleep(2)
    send.close()


def _incomplete_frame_worker(send,*args):
    import os,struct
    os.write(send.fileno(),struct.pack("!i",100)+b"x")
    send.close()


@pytest.mark.parametrize("worker,expected",[(_partial_frame_worker,"deadline_exceeded"),(_incomplete_frame_worker,"worker_failed")])
def test_partial_result_frame_never_blocks_deadline_or_cleanup(worker,expected,monkeypatch):
    import app.core.local_sensitivity as service
    before={p.pid for p in multiprocessing.active_children()}
    monkeypatch.setattr(service,"_worker",worker)
    start=time.monotonic()
    r=analyze_local_sensitivity(growth(),[dict(id="p",step=.002)],"x",timeout_seconds=.5)
    assert r["status"]==expected and "rows" not in r
    assert time.monotonic()-start<1.5
    assert {p.pid for p in multiprocessing.active_children()}==before


@pytest.mark.parametrize("kind",["description","elements","metadata_nodes","metadata_depth","integer","cycle"])
def test_oversize_caller_content_rejected_before_model_dump(kind,monkeypatch):
    from app.core.model import SourceDocument
    m=growth()
    if kind=="description":m.description="x"*(2*1024*1024+1)
    elif kind=="elements":m.variables=m.variables*51
    else:
        m.source_document=SourceDocument(format="vensim_mdl",text="source",diagnostics=[])
        if kind=="metadata_nodes":m.source_document.diagnostics=[{"items":[0]*40001}]
        elif kind=="integer":m.source_document.diagnostics=[{"value":1<<1025}]
        elif kind=="cycle":
            cycle={};cycle["self"]=cycle;m.source_document.diagnostics=[cycle]
        else:
            value={}
            for _ in range(34):value={"nested":value}
            m.source_document.diagnostics=[value]
    def forbidden(*args,**kwargs):raise AssertionError("unbounded snapshot allocation attempted")
    monkeypatch.setattr(Model,"model_dump",forbidden)
    with pytest.raises(LocalSensitivityError):
        analyze_local_sensitivity(m,[dict(id="p",step=.002)],"x")


def test_mutated_invalid_model_revalidation_is_an_admission_error():
    m=growth();m.time_settings.dt=0
    with pytest.raises(LocalSensitivityError) as exc:
        analyze_local_sensitivity(m,[dict(id="p",step=.002)],"x")
    assert exc.value.code=="invalid_request"


def test_spawn_slow_main_import_cannot_block_startup_deadline(tmp_path):
    import subprocess,os
    script=tmp_path/"slow_import.py"
    script.write_text("""
import time
if __name__=="__mp_main__":
    time.sleep(2)
if __name__=="__main__":
    import json,multiprocessing
    from app.core.model import Model
    from app.core.local_sensitivity import analyze_local_sensitivity
    m=Model(description="x"*200000,stocks=[dict(id="x",name="X",initial_value=1)],
            variables=[dict(id="p",name="p",equation="1")],
            time_settings=dict(start=0,end=1,dt=.1))
    start=time.monotonic()
    result=analyze_local_sensitivity(m,[dict(id="p",step=.01)],"x",timeout_seconds=.5)
    print(json.dumps(dict(status=result["status"],elapsed=time.monotonic()-start,
                          children=len(multiprocessing.active_children()))))
""")
    import sys
    result=subprocess.run([sys.executable,str(script)],env={**os.environ,"PYTHONPATH":str(__import__("pathlib").Path(__file__).resolve().parents[1])},
                          capture_output=True,text=True,timeout=5,check=True)
    report=json.loads(result.stdout)
    assert report["status"]=="deadline_exceeded" and report["elapsed"]<1.5
    assert report["children"]==0


def test_private_input_artifact_is_removed_and_not_in_result(tmp_path,monkeypatch):
    import app.core.local_sensitivity as service
    original=service.tempfile.mkstemp;paths=[]
    def temporary(*args,**kwargs):
        fd,path=original(*args,**kwargs,dir=tmp_path)
        import os,stat
        assert stat.S_IMODE(os.fstat(fd).st_mode)==0o600
        paths.append(path)
        return fd,path
    monkeypatch.setattr(service.tempfile,"mkstemp",temporary)
    r=analyze_local_sensitivity(growth(),[dict(id="p",step=.002)],"x")
    assert r["status"]=="complete"
    from pathlib import Path
    assert paths and not any(Path(p).exists() for p in paths)
    assert all(p not in json.dumps(r) for p in paths)


def test_nonzero_elasticity_underflow_is_not_reported_as_true_zero():
    p=1e-300;h=1e200;baseline=1e-100
    points=[p-h,p-h/2,p+h/2,p+h]
    row=_row(dict(baseline=p,points=points),baseline,
             [baseline+1e-300*(x-p) for x in points])
    assert row["derivative"]==pytest.approx(1e-300,rel=1e-12,abs=0)
    assert row["elasticity"] is None
    assert row["elasticity_undefined_reason"]=="elasticity_underflow"


@pytest.mark.parametrize("p,outputs",[(0.,[-1.,-.5,.5,1.]),(2.,[3.,3.,3.,3.])])
def test_true_zero_elasticity_remains_zero(p,outputs):
    row=_row(dict(baseline=p,points=[p-1,p-.5,p+.5,p+1]),3.,outputs)
    assert row["elasticity"]==0
    assert row["elasticity_undefined_reason"] is None


@pytest.mark.parametrize("scale",[1e-10,1.,1e10])
def test_small_baseline_warning_is_unit_invariant(scale):
    p=1.;points=[0.,.5,1.5,2.]
    baseline=1e-300*scale
    outputs=[(baseline+1e-100*(x-p)*scale) for x in points]
    row=_row(dict(baseline=p,points=points),baseline,outputs)
    assert row["small_baseline_warning"] is True
    assert row["elasticity"] is not None
    assert math.isfinite(row["elasticity"])
