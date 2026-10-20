"""Ephemeral capability-scoped agent/page workspaces. No model-store writes."""
import hashlib
import hmac
import json
import secrets
import time
from copy import deepcopy
from threading import RLock
from app.core.model import Model

IDLE_SECONDS=3600
MAX_WORKSPACES=16
MAX_MODEL_BYTES=262144
MAX_RESULT_BYTES=32*1024*1024
_lock=RLock()
_sessions={}

class WorkspaceError(ValueError): pass
class WorkspaceConflict(WorkspaceError): pass
class WorkspaceMissing(WorkspaceError): pass

def _purge():
    now=time.monotonic()
    for identifier in list(_sessions):
        row=_sessions[identifier]
        if now-row['touched']>IDLE_SECONDS or now-row['created']>86400:
            del _sessions[identifier]

def _model(model):
    data=Model.model_validate(model).model_dump(mode='json')
    if len(json.dumps(data).encode())>MAX_MODEL_BYTES:
        raise WorkspaceError('Workspace model exceeds 256 KiB')
    return data

def _authorized(key):
    _purge()
    identifier,separator,secret=key.partition('.')
    row=_sessions.get(identifier)
    if not separator or not row or not hmac.compare_digest(row['secret_hash'],hashlib.sha256(secret.encode()).digest()):
        raise WorkspaceMissing('Workspace not found or expired')
    row['touched']=time.monotonic()
    return row

def create(model=None):
    data=_model(model or Model().model_dump(mode='json'))
    with _lock:
        _purge()
        if len(_sessions)>=MAX_WORKSPACES:
            raise WorkspaceError('Workspace capacity reached; close an unused workspace or retry after expiry')
        identifier=secrets.token_urlsafe(12);secret=secrets.token_urlsafe(32)
        now=time.monotonic()
        _sessions[identifier]={'id':identifier,'secret_hash':hashlib.sha256(secret.encode()).digest(),
            'created':now,'touched':now,'revision':1,'model':data,'model_revision':1,
            'result':None,'result_revision':0,'result_bytes':0,
            'view':{'section':'diagram','fit':1,'selection':None},
            'browser':{'seen':None,'applied_revision':0,'error':None}}
        return {'workspace_id':identifier,'workspace_key':identifier+'.'+secret,'revision':1,
                'idle_timeout_seconds':IDLE_SECONDS,'saved_to_library':False}

def snapshot(key,after_revision=None,include_result=False):
    with _lock:
        row=_authorized(key)
        browser=deepcopy(row['browser']);seen=browser.pop('seen')
        browser['connected']=seen is not None and time.monotonic()-seen<20
        data={'workspace_id':row['id'],'revision':row['revision'],'model_revision':row['model_revision'],
              'result_revision':row['result_revision'],'view':deepcopy(row['view']),'browser':browser}
        if after_revision!=row['revision']:
            data['model']=deepcopy(row['model'])
            if include_result: data['result']=deepcopy(row['result'])
        return data

def replace_model(key,model,expected_revision):
    data=_model(model)
    with _lock:
        row=_authorized(key)
        if row['revision']!=expected_revision:
            raise WorkspaceConflict(f"Revision conflict: current revision is {row['revision']}; inspect before replacing")
        row['revision']+=1;row['model_revision']=row['revision'];row['model']=data
        row['result']=None;row['result_revision']=0;row['result_bytes']=0
        return snapshot(key)

def edit_elements(key,edits,expected_revision,time_settings=None):
    """Apply an explicit batch atomically, retaining all unmentioned inputs."""
    state=snapshot(key)
    if state['revision']!=expected_revision:
        raise WorkspaceConflict(f"Revision conflict: current revision is {state['revision']}")
    model=state['model']
    if not 1<=len(edits)<=100: raise WorkspaceError('Provide between one and 100 explicit element edits')
    allowed={'stock':{'name','units','initial_value','equation','position'},
             'flow':{'name','units','equation','position','from_stock','to_stock'},
             'variable':{'name','units','equation','position'}}
    from app.core.model import Stock,Flow,Variable
    classes={'stock':Stock,'flow':Flow,'variable':Variable}
    for edit in edits:
        kind=edit['element_type'];changes=edit['changes']
        if set(changes)-allowed[kind]: raise WorkspaceError('Unsupported element fields: '+', '.join(sorted(set(changes)-allowed[kind])))
        group=model[{'stock':'stocks','flow':'flows','variable':'variables'}[kind]]
        identifier=edit.get('element_id')
        if edit.get('add'):
            if identifier: raise WorkspaceError('Do not provide element_id when adding; the new ID is returned')
            if not changes.get('name'): raise WorkspaceError('An added element requires a name')
            group.append(classes[kind].model_validate(changes).model_dump(mode='json'))
        else:
            element=next((x for x in group if x['id']==identifier),None)
            if element is None: raise WorkspaceError('Element not found; inspect the workspace before editing')
            element.update(changes)
            classes[kind].model_validate(element)
    if time_settings is not None:model['time_settings']=time_settings
    return replace_model(key,model,expected_revision)

def publish_result(key,result,expected_revision):
    data=result.model_dump(mode='json')
    size=len(json.dumps(data).encode())
    with _lock:
        row=_authorized(key)
        if row['revision']!=expected_revision:
            raise WorkspaceConflict('Workspace changed during simulation; inspect and run the current model')
        if sum(session['result_bytes'] for session in _sessions.values())-row['result_bytes']+size>MAX_RESULT_BYTES:
            raise WorkspaceError('Workspace result memory limit reached; shorten the run or close an unused workspace')
        row['revision']+=1;row['result_revision']=row['revision'];row['result']=data;row['result_bytes']=size
        row['view']['section']='chart'
        return snapshot(key)

def set_view(key,section=None,fit=False,selection=None,expected_revision=None):
    if section not in (None,'diagram','chart','analytics','inputs'):
        raise WorkspaceError('Unknown workspace view')
    with _lock:
        row=_authorized(key)
        if expected_revision is not None and row['revision']!=expected_revision:
            raise WorkspaceConflict(f"Revision conflict: current revision is {row['revision']}")
        if selection is not None and selection not in {x['id'] for group in ('stocks','flows','variables') for x in row['model'][group]}:
            raise WorkspaceError('Selected element does not exist')
        row['revision']+=1
        if section: row['view']['section']=section
        if fit: row['view']['fit']+=1
        row['view']['selection']=selection
        return snapshot(key)

def acknowledge(key,revision,error=None,view=None,selection=None):
    with _lock:
        row=_authorized(key)
        if revision<0 or revision>row['revision']: raise WorkspaceError('Invalid acknowledgement revision')
        row['browser']={'seen':time.monotonic(),'applied_revision':revision,'error':str(error)[:500] if error else None,
                        'view':view,'selection':selection}

def close(key):
    with _lock:
        row=_authorized(key);del _sessions[row['id']]
