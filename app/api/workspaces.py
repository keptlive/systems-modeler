"""Private transient page synchronization. Tokens stay out of request URLs."""
from typing import Annotated,Optional,Literal
from fastapi import APIRouter,Header,HTTPException,Response
from pydantic import BaseModel,Field
from app.core.model import Model
from app.storage import workspaces as store

router=APIRouter()
class Create(BaseModel): model:Optional[Model]=None
class Update(BaseModel):
    model:Model
    expected_revision:int=Field(ge=1)
class Ack(BaseModel):
    applied_revision:int=Field(ge=0)
    error:Optional[str]=Field(default=None,max_length=500)
    view:Optional[Literal['diagram','chart','analytics','ai','properties','inputs']]=None
    selection:Optional[str]=Field(default=None,max_length=200)

def key(identifier,authorization):
    if not authorization.startswith('Bearer '): raise HTTPException(404,'Workspace not found or expired')
    value=authorization[7:]
    if value.partition('.')[0]!=identifier: raise HTTPException(404,'Workspace not found or expired')
    return value

def invoke(function,*args,**kwargs):
    try: return function(*args,**kwargs)
    except store.WorkspaceMissing as error: raise HTTPException(404,str(error)) from error
    except store.WorkspaceConflict as error: raise HTTPException(409,str(error)) from error
    except store.WorkspaceError as error: raise HTTPException(400,str(error)) from error

@router.post('')
def create_workspace(request:Create,response:Response):
    response.headers['Cache-Control']='no-store'
    return invoke(store.create,request.model.model_dump(mode='json') if request.model else None)

@router.get('/{identifier}')
def get_workspace(identifier:str,response:Response,authorization:Annotated[str,Header()]='',after_revision:Optional[int]=None):
    response.headers['Cache-Control']='no-store'
    return invoke(store.snapshot,key(identifier,authorization),after_revision,True)

@router.put('/{identifier}/model')
def update_workspace(identifier:str,request:Update,response:Response,authorization:Annotated[str,Header()]=''):
    response.headers['Cache-Control']='no-store'
    return invoke(store.replace_model,key(identifier,authorization),request.model.model_dump(mode='json'),request.expected_revision)

@router.post('/{identifier}/ack')
def acknowledge_workspace(identifier:str,request:Ack,authorization:Annotated[str,Header()]=''):
    invoke(store.acknowledge,key(identifier,authorization),request.applied_revision,request.error,request.view,request.selection)
    return {'acknowledged':True}

@router.delete('/{identifier}')
def close_workspace(identifier:str,authorization:Annotated[str,Header()]=''):
    invoke(store.close,key(identifier,authorization))
    return {'closed':True}
