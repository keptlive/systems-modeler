"""
REST API endpoints for model CRUD operations.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Path
from typing import Annotated
from app.core.model import Model, ModelUpdate, ModelCreate
from app.storage import models as storage

router = APIRouter()
ModelId = Annotated[str, Path(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$")]


@router.get("/catalog")
def catalog(search: str = "", category: str = "", offset: int = Query(0, ge=0),
            limit: int = Query(2000, ge=1, le=2000)):
    """Lightweight library index; use /{id} for the complete definition."""
    from app.storage.catalog import list_summaries
    rows = list_summaries()
    if category:
        rows = [m for m in rows if m["category"].casefold() == category.casefold()]
    if search:
        query = search.casefold()
        rows = [m for m in rows if query in (m["name"] + " " + m["description"]).casefold()]
    return {"total": len(rows), "offset": offset, "models": rows[offset:offset + limit]}


@router.post("", response_model=Model)
def create_model(model_data: ModelCreate):
    """Create a new model."""
    return storage.create_model(model_data)


@router.get("", response_model=list[Model])
def list_models():
    """List all models."""
    return storage.list_models()


@router.get("/{model_id}", response_model=Model)
def get_model(model_id: ModelId):
    """Get a model by ID."""
    model = storage.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.put("/{model_id}", response_model=Model)
def update_model(model_id: ModelId, update_data: ModelUpdate):
    """Update an existing model."""
    # Convert dict to ModelUpdate to get proper Pydantic handling
    model = storage.update_model(model_id, update_data)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.delete("/{model_id}")
def delete_model(model_id: ModelId):
    """Delete a model."""
    if not storage.delete_model(model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    return {"status": "deleted", "id": model_id}


@router.post("/import/xmile", response_model=Model)
async def import_xmile(file: UploadFile = File(...)):
    """Import a model from XMILE file."""
    try:
        content = await file.read(2 * 1024 * 1024 + 1)
        if len(content) > 2 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="XMILE uploads are limited to 2 MiB")
        xml_content = content.decode("utf-8")
        
        from app.core.xmile_parser import parse_xmile
        model = parse_xmile(xml_content)
        
        # Save the imported model
        saved_model = storage.create_model(model)
        return saved_model
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse XMILE file: {str(e)}")


@router.get("/{model_id}/export/xmile")
def export_xmile(model_id: ModelId):
    """Export a model to XMILE format."""
    model = storage.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return xmile_response(model)


@router.post("/export/xmile")
def export_draft_xmile(model: Model):
    """Export the current draft without saving or exporting a stale saved copy."""
    return xmile_response(model)


def xmile_response(model: Model):
    from app.core.xmile_generator import generate_xmile
    from fastapi.responses import Response
    
    xmile_content = generate_xmile(model)
    
    # Return as XML file download
    from urllib.parse import quote
    filename = quote(model.name.replace(' ', '_') + '.xmile', safe='')
    return Response(
        content=xmile_content,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=model.xmile; filename*=UTF-8''{filename}"}
    )
