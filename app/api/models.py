"""
REST API endpoints for model CRUD operations.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Path, Response
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
def get_model(model_id: ModelId, response: Response):
    """Get a stored definition, or a read-only migrated May preset draft."""
    model = storage.get_model(model_id)
    # Existing user/private definitions always win over retired public aliases.
    if model is not None:
        return model
    presets = {"may-logistic-chaos": 3.7, "may-ecological-chaos-eco": 3.8}
    if model_id in presets:
        canonical = storage.get_model("may-chaos-population-eco")
        if canonical is not None:
            from uuid import uuid4
            model = canonical.model_copy(deep=True)
            model.id = str(uuid4())  # Fresh unsaved draft: never reuse a saved/canonical ID.
            rate = presets[model_id]
            parameters = [v for v in model.variables if v.name == "r"]
            populations = [s for s in model.stocks if s.name == "Population"]
            if (len(parameters) != 1 or len(populations) != 1 or len(model.stocks) != 1
                    or model.time_settings.discrete_period != 1
                    or model.time_settings.dt != 1
                    or model.time_settings.integration_method != "euler"):
                raise HTTPException(status_code=409, detail="Migrated May preset unavailable: canonical generation contract changed")
            parameter, population = parameters[0], populations[0]
            parameter.equation = str(rate)
            population.initial_value = 0.1
            population.equation = ""
            model.time_settings = model.time_settings.model_copy(update={
                "start": 0, "end": 100, "dt": 1, "integration_method": "euler",
                "discrete_period": 1})
            model.name = f"May logistic generation map (legacy r={rate} preset)"
            notice = (f"Migrated {model_id} to an unsaved May preset draft (r={rate}). "
                      "Save creates a separate model. Legacy diagnostic columns differ; "
                      "see the migration notes in the description.")
            model.description = notice + "\n\n" + model.description
            response.headers["X-Model-Migration"] = notice
            response.headers["Cache-Control"] = "no-store"
            return model
    raise HTTPException(status_code=404, detail="Model not found")


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


@router.post("/import/mdl", response_model=Model)
async def import_mdl(file: UploadFile = File(...)):
    """Import the supported native MDL subset, retaining exact source and caveats."""
    from app.core.mdl_parser import parse_mdl, MDLImportError
    try:
        content = await file.read(2 * 1024 * 1024 + 1)
        if len(content) > 2 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="MDL uploads are limited to 2 MiB")
        source = content.decode("utf-8-sig")
        parsed = parse_mdl(source)
        model = Model(**{**parsed["model"], "source_document": {
            "format": "vensim_mdl", "text": source, "diagnostics": parsed["diagnostics"]}})
        return storage.create_model(model)
    except HTTPException:
        raise
    except (MDLImportError, ValueError, UnicodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
    
    try:
        xmile_content = generate_xmile(model)
    except ValueError as exc:
        # Expected unsupported-export admission only. Keep unexpected failures
        # visible as server errors, and expose a bounded text detail as JSON.
        message = str(exc)[:1024]
        message = ''.join(char if ord(char) >= 32 and ord(char) != 127 else ' '
                          for char in message)
        detail = ' '.join(message.split())[:500]
        raise HTTPException(status_code=422, detail=detail or
                            'XMILE export is unsupported; use JSON to preserve model settings') from exc
    
    # Return as XML file download
    from urllib.parse import quote
    filename = quote(model.name.replace(' ', '_') + '.xmile', safe='')
    return Response(
        content=xmile_content,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=model.xmile; filename*=UTF-8''{filename}"}
    )
