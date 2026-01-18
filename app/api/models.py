"""
REST API endpoints for model CRUD operations.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.core.model import Model, ModelUpdate
from app.storage import models as storage

router = APIRouter()


@router.post("", response_model=Model)
async def create_model(model_data: dict):
    """Create a new model."""
    model = Model(**model_data)
    return storage.create_model(model)


@router.get("", response_model=list[Model])
async def list_models():
    """List all models."""
    return storage.list_models()


@router.get("/{model_id}", response_model=Model)
async def get_model(model_id: str):
    """Get a model by ID."""
    model = storage.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.put("/{model_id}", response_model=Model)
async def update_model(model_id: str, update_data: dict):
    """Update an existing model."""
    # Convert dict to ModelUpdate to get proper Pydantic handling
    model_update = ModelUpdate(**update_data)
    model = storage.update_model(model_id, model_update)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.delete("/{model_id}")
async def delete_model(model_id: str):
    """Delete a model."""
    if not storage.delete_model(model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    return {"status": "deleted", "id": model_id}


@router.post("/import/xmile", response_model=Model)
async def import_xmile(file: UploadFile = File(...)):
    """Import a model from XMILE file."""
    try:
        content = await file.read()
        xml_content = content.decode("utf-8")
        
        from app.core.xmile_parser import parse_xmile
        model = parse_xmile(xml_content)
        
        # Save the imported model
        saved_model = storage.create_model(model)
        return saved_model
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse XMILE file: {str(e)}")


@router.get("/{model_id}/export/xmile")
async def export_xmile(model_id: str):
    """Export a model to XMILE format."""
    model = storage.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    from app.core.xmile_generator import generate_xmile
    from fastapi.responses import Response
    
    xmile_content = generate_xmile(model)
    
    # Return as XML file download
    filename = f"{model.name.replace(' ', '_')}.xmile"
    return Response(
        content=xmile_content,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
