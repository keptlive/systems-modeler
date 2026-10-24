"""Bounded local final-stock finite differences; no persistence or transport layer.

The admitted pure scalar DAG grammar permits a conservative whole-experiment
work reservation. A spawned process supplies an independently enforceable deadline.
"""
import ast
import os
import struct
import tempfile
import json
import math
import multiprocessing
import threading
import hashlib
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
import time
from typing import Any

from app.core.model import Model
from app.core.equations import _parse_expression, preprocess_equation, decode_identifier, canonical_name
from app.core.execution_order import derive_execution_order
from app.core.diagnostics import model_hash, source_hashes

MAX_RESULT_BYTES = 65536
MAX_MODEL_BYTES = 2 * 1024 * 1024
MAX_ELEMENTS = 100
MAX_POINTS = 2001
MAX_PARAMETERS = 8
MAX_WORK = 2_000_000
MAX_AST_NODES = 4096
MAX_EQUATION_CHARACTERS = 32768
_WORKER_SLOT = threading.BoundedSemaphore(1)
CONTRACT_VERSION = "local-final-stock-v1"
_FUNCTIONS = frozenset({"SIN", "COS", "EXP", "ATAN"})
_NODES = (ast.Expression, ast.Name, ast.Load, ast.Constant, ast.BinOp,
          ast.UnaryOp, ast.Call, ast.UAdd, ast.USub,
          ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)


class LocalSensitivityError(ValueError):
    """Admission failures occur before a worker starts."""
    def __init__(self, message, code="invalid_request"):
        super().__init__(message)
        self.code = code


def _reject(message, code="unsupported_model"):
    raise LocalSensitivityError(message, code)


def _finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _literal(tree):
    node = tree.body
    sign = 1
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        sign = -1 if isinstance(node.op, ast.USub) else 1
        node = node.operand
    if not isinstance(node, ast.Constant) or not _finite_number(node.value):
        _reject("Selected variables must have finite numeric literal equations")
    return sign * float(node.value)


def _geometry(p, h):
    if not _finite_number(h) or h <= 0:
        _reject("Steps must be finite positive numbers", "invalid_step")
    points = [p-h, p-h/2, p+h/2, p+h]
    expected = [-h, -h/2, h/2, h]
    if (not all(math.isfinite(v) for v in points)
            or len(set(points + [p])) != 5):
        _reject("Step cannot be represented at this parameter scale", "invalid_step")
    distances = [v-p for v in points]
    if not all(math.isfinite(v) and abs(v/e-1) <= 1e-6
               for v, e in zip(distances, expected)):
        _reject("Floating-point sample geometry is distorted", "invalid_step")
    return points



def _bounded_source(model):
    """Inspect caller-owned content before model_dump can allocate a copy.

    No collection is expanded into a work list. Depth, visits and accumulated
    string bytes are bounded, including unused metadata and preserved sources.
    """
    visits = 0
    text_bytes = 0
    active = set()
    def inspect(value, depth):
        nonlocal visits, text_bytes
        visits += 1
        if visits > 40000 or depth > 32:
            _reject("Source metadata exceeds the node/depth bound", "capacity")
        if isinstance(value, str):
            if len(value)>MAX_MODEL_BYTES-text_bytes:
                _reject("Source text exceeds the pre-serialization bound", "capacity")
            for offset in range(0,len(value),1024):
                text_bytes += len(value[offset:offset+1024].encode("utf-8"))
                if text_bytes>MAX_MODEL_BYTES:
                    _reject("Source text exceeds the pre-serialization bound", "capacity")
        elif value is None or type(value) is bool or isinstance(value,datetime):
            return
        elif type(value) is int:
            if value.bit_length()>1024:
                _reject("Source integer exceeds the serialization bound", "capacity")
        elif type(value) is float:
            if not math.isfinite(value):
                _reject("Source contains nonfinite metadata", "invalid_request")
        elif isinstance(value,(BaseModel,dict,list,tuple)):
            if id(value) in active:
                _reject("Cyclic source metadata cannot be serialized", "invalid_request")
            size=len(type(value).model_fields) if isinstance(value,BaseModel) else len(value)
            if size>40000-visits:
                _reject("Source collection exceeds the node bound", "capacity")
            active.add(id(value))
            try:
                if isinstance(value,BaseModel):
                    for key in type(value).model_fields:
                        inspect(key,depth+1)
                        inspect(getattr(value,key),depth+1)
                elif isinstance(value,dict):
                    for key,item in value.items():
                        if not isinstance(key,str):
                            _reject("Source metadata keys must be strings", "invalid_request")
                        inspect(key,depth+1)
                        inspect(item,depth+1)
                else:
                    for item in value:
                        inspect(item,depth+1)
            finally:
                active.remove(id(value))
        else:
            _reject("Source contains unsupported metadata values", "invalid_request")
    inspect(model,0)


def _admit(model, parameters, output_stock_id, max_work_units):
    if os.name != "posix":
        _reject("Local sensitivity requires the POSIX bounded worker transport", "unsupported_environment")
    if not isinstance(model, Model):
        _reject("model must be a validated Model", "invalid_request")
    if type(max_work_units) is not int or not 1 <= max_work_units <= MAX_WORK:
        _reject("Aggregate work budget must be an integer from 1 to 2000000", "invalid_request")
    if not isinstance(parameters, list) or not 1 <= len(parameters) <= MAX_PARAMETERS:
        _reject("Select 1..8 unique scalar constant variables", "invalid_request")
    if not isinstance(output_stock_id, str) or not output_stock_id:
        _reject("An output stock ID is required", "invalid_request")
    if any(not isinstance(getattr(model,key),list) for key in ("stocks","flows","variables")):
        _reject("Model element collections must be lists", "invalid_request")
    if len(model.stocks)+len(model.flows)+len(model.variables)>MAX_ELEMENTS:
        _reject("Local sensitivity supports at most 100 elements", "capacity")
    _bounded_source(model)
    try:
        raw = model.model_dump(mode="json")
        encoded = json.dumps(raw, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > MAX_MODEL_BYTES:
            _reject("Model exceeds the 2MiB local sensitivity limit", "capacity")
        # Snapshot validated bytes, never retain caller-owned nested objects.
        snapshot = Model.model_validate_json(encoded)
    except LocalSensitivityError:
        raise
    except (ValueError,TypeError,OverflowError) as exc:
        _reject("Model snapshot is invalid: "+str(exc)[:500], "invalid_request")
    settings = snapshot.time_settings
    if (snapshot.has_structure() or snapshot.tables
            or settings.discrete_period is not None
            or settings.integration_method not in {"euler", "rk4"}):
        _reject("Only scalar continuous Euler/RK4 models without tables are supported")
    elements = [*snapshot.stocks, *snapshot.flows, *snapshot.variables]
    if not snapshot.stocks or len(elements) > MAX_ELEMENTS:
        _reject("Select a model with stocks and at most 100 elements", "capacity")
    if (any(len(e.id)>128 or len(e.name)>128 or (e.units is not None and len(e.units)>128)
            for e in elements)
            or (settings.units is not None and len(settings.units)>128)):
        _reject("Element identifiers, names and unit labels are limited to 128 characters", "capacity")
    ids = [e.id for e in elements]
    if len(set(ids)) != len(ids) or any(not isinstance(i, str) or not i for i in ids):
        _reject("Every element must have a unique nonempty ID")
    if any(v.role != "auxiliary" for v in snapshot.variables):
        _reject("Report variables are unsupported")
    if sum(len(e.equation) for e in elements) > MAX_EQUATION_CHARACTERS:
        _reject("Equations exceed the local sensitivity text limit", "capacity")
    stock_aliases = {}
    for stock in snapshot.stocks:
        for alias in {stock.id, stock.name}:
            if alias in stock_aliases and stock_aliases[alias] != stock.id:
                _reject("Stock ID/name references are ambiguous")
            stock_aliases[alias] = stock.id
    for flow in snapshot.flows:
        if any(endpoint is not None and endpoint not in stock_aliases
               for endpoint in (flow.from_stock, flow.to_stock)):
            _reject("Flow refers to an unknown stock")
    output = next((s for s in snapshot.stocks if s.id == output_stock_id), None)
    if output is None:
        _reject("Output must identify an existing stock ID", "invalid_selector")
    trees = {}
    count = 0
    try:
        for element in elements:
            if not element.equation and element in snapshot.stocks:
                continue
            tree = _parse_expression(preprocess_equation(element.equation))
            trees[element.id] = tree
            nodes = list(ast.walk(tree))
            count += len(nodes)
            if count > MAX_AST_NODES:
                _reject("Equations exceed the local sensitivity AST limit", "capacity")
            for node in nodes:
                if not isinstance(node, _NODES):
                    _reject("Unsupported nonsmooth, conditional or contextual syntax")
                if isinstance(node, ast.Name) and canonical_name(decode_identifier(node.id)) in {"time","dt","time_step"}:
                    _reject("Time and timestep references are unsupported")
                if isinstance(node, ast.Constant) and not _finite_number(node.value):
                    _reject("Only finite numeric constants are supported")
                if isinstance(node, ast.Call):
                    if (not isinstance(node.func, ast.Name) or node.keywords
                            or decode_identifier(node.func.id).upper() not in _FUNCTIONS
                            or len(node.args) != 1):
                        _reject("Only unary SIN, COS, EXP and ATAN calls are supported")
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
                    if (not isinstance(node.right, ast.Constant)
                            or type(node.right.value) is not int
                            or not 0 <= node.right.value <= 16):
                        _reject("Powers require literal integer exponents from 0 to 16")
        if derive_execution_order(snapshot) is None or derive_execution_order(snapshot, initial=True) is None:
            _reject("Model must have unambiguous autonomous pure dependency DAGs")
    except LocalSensitivityError:
        raise
    except (ValueError, SyntaxError, OverflowError, RecursionError) as exc:
        _reject("Equation admission failed: " + str(exc)[:300])
    selected = []
    seen = set()
    variables = {v.id: v for v in snapshot.variables}
    for entry in parameters:
        if not isinstance(entry, dict) or set(entry) != {"id", "step"}:
            _reject("Each parameter requires exactly id and step", "invalid_request")
        identity = entry["id"]
        if not isinstance(identity, str) or identity in seen or identity not in variables:
            _reject("Parameter IDs must be unique existing variable IDs", "invalid_selector")
        seen.add(identity)
        variable = variables[identity]
        p = _literal(trees[identity])
        points = _geometry(p, entry["step"])
        selected.append(dict(id=identity, name=variable.name, units=variable.units,
                             baseline=p, step=float(entry["step"]), points=points))
    intervals = (settings.end-settings.start)/settings.dt
    if not math.isfinite(intervals) or intervals > MAX_POINTS-1:
        _reject("Local sensitivity supports at most 2001 sample points", "capacity")
    steps = math.ceil(intervals-1e-10)
    if steps < 1:
        _reject("Invalid output grid")
    times = [min(settings.end, settings.start+i*settings.dt) for i in range(steps+1)]
    times[-1] = settings.end
    if any(b <= a for a, b in zip(times, times[1:])):
        _reject("Output grid is not representable")
    # Same engine's ordinary charge; a failed DAG evaluation can retry at most
    # N² attempts. Success has no retries. Reserve before starting ANY run.
    ordinary = (steps*(5 if settings.integration_method == "rk4" else 1)+1)*max(1,len(elements))
    per_run = ordinary + len(elements)**2
    runs = 1+4*len(selected)
    reserved = per_run*runs
    if per_run > 1_000_000 or reserved > max_work_units:
        _reject("Experiment exceeds its conservative aggregate work reservation", "capacity")
    return snapshot, selected, output, dict(
        runs=runs, per_run_success_work=ordinary, per_run_reserved_work=per_run, total_reserved_work=reserved,
        aggregate_limit=max_work_units, per_run_retained_values=(steps+1)*len(elements),
        sample_points=steps+1)


def _relative_difference(a, b):
    scale = max(abs(a), abs(b))
    return abs(a/scale-b/scale) if scale else 0.0


def _slope(a, b, distance):
    difference = a-b
    return difference/distance if math.isfinite(difference) else a/distance-b/distance


def _row(parameter, baseline, outputs):
    p = parameter["baseline"]
    x = parameter["points"]
    a, b = p-x[0], x[3]-p
    c, d = p-x[1], x[2]-p
    def interpolate(left, right, a, b):
        left_slope = _slope(baseline, left, a)
        right_slope = _slope(right, baseline, b)
        scale = max(a,b)
        wa, wb = a/scale, b/scale
        derivative = math.fsum((wb/(wa+wb)*left_slope, wa/(wa+wb)*right_slope))
        return derivative, left_slope, right_slope
    coarse, _, _ = interpolate(outputs[0], outputs[3], a, b)
    fine, left, right = interpolate(outputs[1], outputs[2], c, d)
    if not all(math.isfinite(v) for v in (coarse,fine,left,right)):
        raise ArithmeticError("Nonfinite derivative")
    refinement = _relative_difference(fine,coarse)
    asymmetry = _relative_difference(left,right)
    elasticity = None
    elasticity_reason = "zero_baseline_output" if baseline == 0 else None
    if baseline != 0:
        # Combine binary exponents rather than overflowing or underflowing
        # intermediate products/quotients that have a representable final value.
        pm, pe = math.frexp(p)
        dm, de = math.frexp(fine)
        ym, ye = math.frexp(baseline)
        try:
            elasticity = math.ldexp(pm*dm/ym, pe+de-ye)
        except OverflowError:
            elasticity = None
        if elasticity is None or not math.isfinite(elasticity):
            elasticity = None
            elasticity_reason = "nonfinite_elasticity"
        elif elasticity == 0 and p != 0 and fine != 0:
            elasticity = None
            elasticity_reason = "elasticity_underflow"
    output_scale = max(abs(baseline), *(abs(value) for value in outputs))
    small_baseline = baseline != 0 and abs(baseline)/output_scale <= 1e-12
    return dict(derivative=fine, coarse_derivative=coarse,
                refinement_disagreement=refinement, one_sided_disagreement=asymmetry,
                status="unstable_or_nonsmooth" if refinement>.01 or asymmetry>.1 else "locally_consistent",
                elasticity=elasticity, elasticity_undefined_reason=elasticity_reason,
                small_baseline_warning=small_baseline,
                resolution_warning=any(value == baseline for value in outputs))


def _failure(exc):
    return dict(code=str(getattr(exc,"code",None) or "simulation_failed")[:100],
                message=str(exc)[:1000])



def _publish(send, result):
    payload = json.dumps(result,ensure_ascii=False,allow_nan=False).encode("utf-8")
    if len(payload) > MAX_RESULT_BYTES:
        raise RuntimeError("Sensitivity result exceeds the scalar response budget")
    send.send_bytes(payload)


def _worker_loss(envelope, reservation, message="Worker exited without a complete result"):
    return dict(envelope,status="worker_failed",
                error=dict(code="worker_exit",message=message),
                completed_runs=None,attempted_runs=None,
                charged_reserved_work=reservation["total_reserved_work"],
                successful_engine_work=None)


def _worker(send, raw, selected, output_id, reservation):
    """Sequential child, bounded trajectories discarded after each scalar reduction."""
    from app.core.simulator import simulate
    successful_work = 0
    completed = 0
    charged = 0
    try:
        model = Model(**raw)
        output = next(s for s in model.stocks if s.id == output_id)
        result = dict(status="complete", baseline_output=None, rows=[],
                      completed_runs=0, charged_reserved_work=0, successful_engine_work=0)
        def run(parameter=None, value=None):
            nonlocal successful_work, completed, charged
            charged += reservation["per_run_reserved_work"]
            copied = model.model_copy(deep=True)
            if parameter is not None:
                next(v for v in copied.variables if v.id==parameter).equation = repr(value)
            trajectory = simulate(copied)
            diagnostics = trajectory.integration_diagnostics or {}
            # Explicit deterministic successful DAG runs emit no work diagnostics
            # when there were no retries; use the engine's exact ordinary formula.
            work = diagnostics.get("work_units", reservation["per_run_success_work"])
            if work > reservation["per_run_reserved_work"]:
                raise RuntimeError("Engine work exceeded the admitted reservation")
            successful_work += work
            completed += 1
            final = trajectory.values[output.name][-1]
            if trajectory.time[-1] != model.time_settings.end or not math.isfinite(final):
                raise ArithmeticError("Output endpoint or value is invalid")
            return final
        try:
            baseline = run()
            result["baseline_output"] = baseline
            result["actual_final_sample_time"] = model.time_settings.end
        except Exception as exc:
            result.update(status="baseline_failed", error=_failure(exc))
        else:
            for parameter in selected:
                row = dict(parameter_id=parameter["id"], parameter_name=parameter["name"],
                           parameter_units=parameter["units"], parameter_baseline=parameter["baseline"],
                           requested_step=parameter["step"], sample_values=parameter["points"])
                outputs = []
                errors = []
                for point in parameter["points"]:
                    try:
                        outputs.append(run(parameter["id"], point))
                    except Exception as exc:
                        outputs.append(None)
                        errors.append(dict(parameter_value=point, **_failure(exc)))
                if errors:
                    row.update(status="failed", failures=errors)
                    result["status"] = "partial_failure"
                else:
                    try:
                        row.update(_row(parameter, baseline, outputs))
                    except (ArithmeticError, ValueError) as exc:
                        row.update(status="failed", failures=[_failure(exc)])
                        result["status"] = "partial_failure"
                row["sample_outputs"] = outputs
                result["rows"].append(row)
        result.update(completed_runs=completed, attempted_runs=charged//reservation["per_run_reserved_work"],
                      charged_reserved_work=charged, successful_engine_work=successful_work)
        _publish(send, result)
    except Exception as exc:
        _publish(send, dict(status="worker_failed",error=_failure(exc),
                       attempted_runs=charged//reservation["per_run_reserved_work"],
                       completed_runs=completed,charged_reserved_work=charged,
                       successful_engine_work=successful_work))
    finally:
        send.close()



def _worker_bootstrap(send, input_path, target):
    # Only small handles/path/function identity enter Process.start's synchronous
    # spawn bootstrap pipe. Large model serialization cannot block start while
    # the child imports its main module. The child may block; parent can kill it.
    try:
        with open(input_path,"rb") as source:
            payload=source.read(MAX_MODEL_BYTES+32768+1)
        if len(payload)>MAX_MODEL_BYTES+32768:
            raise ValueError("Worker input exceeds the bounded artifact limit")
        request=json.loads(payload)
        target(send,request["model"],request["selected"],request["output_id"],request["reservation"])
    except Exception as exc:
        try:
            _publish(send,dict(status="worker_failed",error=_failure(exc)))
        finally:
            send.close()


def analyze_local_sensitivity(model: Model, parameters: list[dict[str, Any]], output_stock_id: str,
                              *, max_work_units=MAX_WORK, timeout_seconds=10.0, cancel_event=None):
    """Return read-only local final-stock finite differences.

    Admission errors raise LocalSensitivityError before execution. Baseline,
    perturbation, deadline and cancellation failures return explicit statuses.
    cancel_event may be a threading.Event-like object; it is never sent to child.
    """
    if not _finite_number(timeout_seconds) or not 0 < timeout_seconds <= 30:
        _reject("Deadline must be finite, positive and at most 30 seconds", "invalid_request")
    snapshot, selected, output, reservation = _admit(model, parameters, output_stock_id,max_work_units)
    envelope = dict(contract_version=CONTRACT_VERSION,method="central_finite_difference",
                    scope="local_final_stock", output_stock_id=output.id,output_name=output.name,
                    output_units=output.units, settings=snapshot.time_settings.model_dump(mode="json"),
                    requested_end=snapshot.time_settings.end, reservation=reservation,
                    provenance=dict(normalized_model_sha256=model_hash(snapshot),engine_sha256=source_hashes(),
                                    sensitivity_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    if cancel_event is not None and cancel_event.is_set():
        return dict(envelope,status="cancelled",completed_runs=0,attempted_runs=0,
                    charged_reserved_work=0,successful_engine_work=0)
    deadline = time.monotonic()+timeout_seconds
    acquired = False
    while not acquired:
        if cancel_event is not None and cancel_event.is_set():
            return dict(envelope,status="cancelled",completed_runs=0,attempted_runs=0,
                        charged_reserved_work=0,successful_engine_work=0)
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            return dict(envelope,status="deadline_exceeded",completed_runs=0,attempted_runs=0,
                        charged_reserved_work=0,successful_engine_work=0)
        acquired = _WORKER_SLOT.acquire(timeout=min(.02,remaining))
    receive = send = process = None
    input_path = None
    try:
        payload=json.dumps(dict(model=snapshot.model_dump(mode="json"),selected=selected,
                                output_id=output.id,reservation=reservation),
                           ensure_ascii=False,allow_nan=False).encode("utf-8")
        if len(payload)>MAX_MODEL_BYTES+32768:
            _reject("Worker input exceeds the bounded artifact limit", "capacity")
        descriptor,input_path=tempfile.mkstemp(prefix="local-sensitivity-",suffix=".json")
        with os.fdopen(descriptor,"wb") as artifact:
            artifact.write(payload)
        if time.monotonic()>=deadline:
            return dict(envelope,status="deadline_exceeded",completed_runs=0,attempted_runs=0,
                        charged_reserved_work=0,successful_engine_work=0)
        context = multiprocessing.get_context("spawn")
        receive, send = context.Pipe(duplex=False)
        process = context.Process(target=_worker_bootstrap,args=(send,input_path,_worker))
        process.start()
        send.close()
        # Connection.poll()+recv() is unsafe: readiness may cover only part of
        # a frame and recv then blocks past deadline. POSIX nonblocking reads
        # instead bound each operation and keep partial publication interruptible.
        os.set_blocking(receive.fileno(), False)
        buffer = bytearray()
        expected = None
        while True:
            cancelled = cancel_event is not None and cancel_event.is_set()
            if cancelled or time.monotonic() >= deadline:
                return dict(envelope,status="cancelled" if cancelled else "deadline_exceeded",
                            completed_runs=None,attempted_runs=None,
                            charged_reserved_work=reservation["total_reserved_work"],
                            successful_engine_work=None)
            try:
                chunk = os.read(receive.fileno(), min(4096,MAX_RESULT_BYTES+4-len(buffer)))
            except BlockingIOError:
                chunk = None
            except OSError:
                return _worker_loss(envelope,reservation,"Worker result transport failed")
            if chunk == b"":
                return _worker_loss(envelope,reservation)
            if chunk:
                buffer.extend(chunk)
                if expected is None and len(buffer)>=4:
                    expected = struct.unpack("!i",buffer[:4])[0]
                    if not 0 < expected <= MAX_RESULT_BYTES:
                        return _worker_loss(envelope,reservation,"Invalid worker frame size")
                if expected is not None and len(buffer)>=expected+4:
                    try:
                        def invalid_constant(value):
                            raise ValueError("Nonfinite JSON")
                        report=json.loads(bytes(buffer[4:expected+4]),parse_constant=invalid_constant)
                        if not isinstance(report,dict) or "status" not in report:
                            raise ValueError("Invalid worker result")
                    except (ValueError,UnicodeError):
                        return _worker_loss(envelope,reservation,"Invalid worker result")
                    return dict(envelope,**report)
            else:
                time.sleep(min(.01,max(0,deadline-time.monotonic())))

    finally:
        if process is not None and process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join()
        if receive is not None:
            receive.close()
        if send is not None:
            send.close()
        try:
            if input_path is not None:
                try:
                    os.unlink(input_path)
                except FileNotFoundError:
                    pass
        finally:
            _WORKER_SLOT.release()
