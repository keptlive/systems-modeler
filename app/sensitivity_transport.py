"""Shared bounded HTTP/MCP local-sensitivity service and POSIX admission.

No library writes. The persistent lock inode must never be unlinked at runtime.
"""
import asyncio
import contextlib
import fcntl
import json
import os
import stat
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import get_args, get_origin, Union
import types

import anyio
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.core.model import Model, TimeSettingsPatch
from app.core.local_sensitivity import analyze_local_sensitivity, LocalSensitivityError, _bounded_source
from app.storage import models as storage

MAX_REQUEST_BYTES=2*1024*1024
router=APIRouter()


class SensitivityParameter(BaseModel):
    model_config=ConfigDict(extra="forbid")
    id: str=Field(min_length=1,max_length=128,strict=True)
    step: float=Field(gt=0,allow_inf_nan=False)
    @field_validator("step",mode="before")
    @classmethod
    def numeric_step(cls,value):
        if type(value) not in (int,float):
            raise ValueError("step must be a finite number, not a boolean or string")
        return value


class SensitivityRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    model: dict | None=None
    model_id: str | None=Field(default=None,min_length=1,max_length=256)
    parameters: list[SensitivityParameter]=Field(min_length=1,max_length=8)
    output_stock_id: str=Field(min_length=1,max_length=128,strict=True)
    time_settings: TimeSettingsPatch | None=None
    timeout_seconds: float=Field(default=10,gt=0,le=30,allow_inf_nan=False)
    max_work_units: int=Field(default=2_000_000,ge=1,le=2_000_000,strict=True)
    @field_validator("timeout_seconds",mode="before")
    @classmethod
    def numeric_timeout(cls,value):
        if type(value) not in (int,float):
            raise ValueError("timeout_seconds must be a finite number")
        return value


class SensitivityTransportError(ValueError):
    def __init__(self,message,code="invalid_request",http_status=422):
        super().__init__(message)
        self.code=code
        self.http_status=http_status


def error_payload(error):
    message=str(error)[:1000]
    return dict(detail=message,failure=dict(code=getattr(error,"code","invalid_request"),message=message))


def decode_request_json(value,limit=MAX_REQUEST_BYTES):
    if isinstance(value,str):
        if len(value)>limit or len(value.encode("utf-8"))>limit:
            raise SensitivityTransportError("Request exceeds 2MiB","capacity",413)
        try:
            value=json.loads(value,parse_constant=lambda token: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
        except (ValueError,RecursionError) as exc:
            raise SensitivityTransportError("Invalid finite JSON request") from exc
    if not isinstance(value,dict):
        raise SensitivityTransportError("Request must be a JSON object")
    # Bound caller-owned object forms BEFORE full serialization or validation.
    _bounded_source(value)
    encoded=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode("utf-8")
    if len(encoded)>limit:
        raise SensitivityTransportError("Request exceeds 2MiB","capacity",413)
    return value



def _strict_schema_keys(value,schema,path="model"):
    """Reject discarded schema keys; declared plain dict metadata stays opaque."""
    if not isinstance(value,dict):
        return  # Pydantic reports ordinary type/required-field failures.
    unknown=set(value)-set(schema.model_fields)
    if unknown:
        names=", ".join(sorted(str(key)[:128] for key in unknown)[:8])
        raise SensitivityTransportError(f"Unknown fields at {path}: {names}")
    def visit(item,annotation,location):
        origin=get_origin(annotation)
        if isinstance(annotation,type) and issubclass(annotation,BaseModel):
            _strict_schema_keys(item,annotation,location)
        elif origin in (list,tuple) and isinstance(item,(list,tuple)):
            arguments=get_args(annotation)
            if arguments:
                for index,child in enumerate(item):
                    visit(child,arguments[0],f"{location}[{index}]")
        elif origin in (Union,types.UnionType):
            for branch in get_args(annotation):
                visit(item,branch,location)
        # Plain dict fields intentionally carry arbitrary source/diagnostic
        # metadata. Their contents remain bounded by decode_request_json.
    for key,item in value.items():
        visit(item,schema.model_fields[key].annotation,f"{path}.{key}")


def resolve_sensitivity_model(model_id=None,model_json=None,time_settings=None):
    if (model_id is None)==(model_json is None):
        raise SensitivityTransportError("Provide exactly one model or model_id")
    try:
        if model_json is not None:
            raw=decode_request_json(model_json)
            _strict_schema_keys(raw,Model)
            model=Model.model_validate(raw)
        else:
            if not isinstance(model_id,str) or not 1<=len(model_id)<=256:
                raise SensitivityTransportError("Invalid model_id")
            model=storage.get_model(model_id)
            if model is None:
                raise SensitivityTransportError("Model not found","model_not_found",404)
        _bounded_source(model)
        if time_settings is not None:
            patch=time_settings if isinstance(time_settings,TimeSettingsPatch) else TimeSettingsPatch.model_validate(time_settings)
            model=model.model_copy(update={"time_settings":patch.apply_to(model.time_settings)})
        return model
    except SensitivityTransportError:
        raise
    except (ValueError,TypeError,RecursionError) as exc:
        raise SensitivityTransportError("Invalid model or settings: "+str(exc)[:500],
                                        getattr(exc,"code","invalid_request")) from exc


def _quota_directory():
    configured=os.environ.get("SYSTEMS_MODELER_SENSITIVITY_QUOTA_DIR")
    path=configured or f"/tmp/stockandflow-sensitivity-{os.geteuid()}"
    parts=Path(path).parts
    if not path.startswith("/") or len(path)>512 or ".." in parts or len(parts)<2:
        raise OSError("Quota directory must be an absolute bounded path")
    descriptor=os.open("/",os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:
        for index,part in enumerate(parts[1:]):
            created=False
            if index==len(parts)-2:
                try:
                    os.mkdir(part,0o700,dir_fd=descriptor)
                    created=True
                except FileExistsError:
                    pass
            following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=descriptor)
            os.close(descriptor);descriptor=following
            if created:
                os.fchmod(descriptor,0o700)
        info=os.fstat(descriptor)
        if info.st_uid!=os.geteuid() or stat.S_IMODE(info.st_mode)!=0o700:
            raise OSError("Quota directory must be private and owned by the service user")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


@contextmanager
def deployment_quota():
    """One host/filesystem-shared slot across HTTP/MCP processes; reject if busy."""
    directory=descriptor=None
    try:
        directory=_quota_directory()
        flags=os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC
        try:
            descriptor=os.open("slot.lock",flags|os.O_CREAT|os.O_EXCL,0o600,dir_fd=directory)
            os.fchmod(descriptor,0o600)
        except FileExistsError:
            descriptor=os.open("slot.lock",flags,dir_fd=directory)
        info=os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid()
                or stat.S_IMODE(info.st_mode)!=0o600 or info.st_nlink!=1):
            raise OSError("Quota lock must be a private single-link regular file")
        try:
            fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SensitivityTransportError("Another local sensitivity experiment is running",
                                            "sensitivity_busy",429) from exc
        yield
    except SensitivityTransportError:
        raise
    except OSError as exc:
        raise SensitivityTransportError("Shared sensitivity quota is unavailable",
                                        "quota_unavailable",503) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


async def run_sensitivity(model,parameters,output_stock_id,*,timeout_seconds=10,max_work_units=2_000_000,cancel_event=None):
    """Transport cancellation waits for worker cleanup before releasing flock."""
    event=cancel_event or threading.Event()
    with deployment_quota():
        task=asyncio.create_task(asyncio.to_thread(
            analyze_local_sensitivity,model,parameters,output_stock_id,
            timeout_seconds=timeout_seconds,max_work_units=max_work_units,cancel_event=event))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            event.set()
            # AnyIO request scopes may keep cancellation active. Shield that
            # scope as well as the asyncio task, and retain quota until joined.
            with anyio.CancelScope(shield=True):
                while not task.done():
                    try:
                        await asyncio.shield(task)
                    except asyncio.CancelledError:
                        continue
                    except Exception:
                        break
            if task.done() and not task.cancelled():
                with contextlib.suppress(Exception):
                    task.result()
            raise
        except OSError as exc:
            raise SensitivityTransportError("Sensitivity worker is unavailable",
                                            "worker_unavailable",503) from exc


async def _bounded_body(request):
    length=request.headers.get("content-length")
    if length is not None:
        try:
            if int(length)<0 or int(length)>MAX_REQUEST_BYTES:
                raise ValueError()
        except ValueError as exc:
            raise SensitivityTransportError("Request exceeds its byte limit or has invalid length","capacity",413) from exc
    body=bytearray()
    async for chunk in request.stream():
        if len(body)+len(chunk)>MAX_REQUEST_BYTES:
            raise SensitivityTransportError("Request exceeds 2MiB","capacity",413)
        body.extend(chunk)
    try:
        return decode_request_json(body.decode("utf-8"))
    except UnicodeError as exc:
        raise SensitivityTransportError("Request must be UTF-8 JSON") from exc


@router.post("/sensitivity/local")
async def local_sensitivity_endpoint(request:Request):
    """Read-only local partial derivatives; disconnect cancels the worker."""
    watcher=None
    try:
        try:
            parsed=SensitivityRequest.model_validate(await _bounded_body(request))
        except ValidationError as exc:
            raise SensitivityTransportError("Invalid sensitivity fields: "+str(exc)[:500]) from exc
        model=resolve_sensitivity_model(parsed.model_id,parsed.model,parsed.time_settings)
        event=threading.Event()
        async def disconnected():
            while not event.is_set():
                if await request.is_disconnected():
                    event.set()
                    return
                await asyncio.sleep(.02)
        watcher=asyncio.create_task(disconnected())
        return await run_sensitivity(model,[p.model_dump() for p in parsed.parameters],parsed.output_stock_id,
                                     timeout_seconds=parsed.timeout_seconds,max_work_units=parsed.max_work_units,
                                     cancel_event=event)
    except (SensitivityTransportError,LocalSensitivityError) as exc:
        return JSONResponse(status_code=getattr(exc,"http_status",422),content=error_payload(exc))
    finally:
        if watcher is not None:
            watcher.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watcher
