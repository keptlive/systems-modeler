"""
JSON file storage for systems dynamics models.
"""
import json
import os
from datetime import datetime, timezone
from typing import Optional, Union
from app.core.model import Model, ModelCreate, ModelUpdate
import uuid


MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")


def ensure_models_dir():
    """Ensure the models directory exists."""
    os.makedirs(MODELS_DIR, exist_ok=True)


def get_model_path(model_id: str) -> str:
    """Get the file path for a model."""
    return os.path.join(MODELS_DIR, f"{model_id}.json")


def find_model_path(model_id: str) -> Optional[str]:
    """Find a model file by ID, searching all subdirectories."""
    ensure_models_dir()
    target_filename = f"{model_id}.json"
    
    # First check root directory
    root_path = os.path.join(MODELS_DIR, target_filename)
    if os.path.exists(root_path):
        return root_path
    
    # Search subdirectories
    for root, dirs, files in os.walk(MODELS_DIR):
        if target_filename in files:
            return os.path.join(root, target_filename)
    
    return None


def list_models() -> list[Model]:
    """List all saved models. Auto-generates missing connectors from equations."""
    ensure_models_dir()
    from app.core.model import generate_connectors_from_equations

    models = []
    # Walk through all subdirectories to find model files
    for root, dirs, files in os.walk(MODELS_DIR):
        # Get category from subdirectory name
        category = os.path.basename(root) if root != MODELS_DIR else None
        
        for filename in files:
            if filename.endswith(".json"):
                try:
                    filepath = os.path.join(root, filename)
                    with open(filepath, "r") as f:
                        data = json.load(f)
                        # Add category if from subdirectory
                        if category and category != "models":
                            data["category"] = category
                        model = Model(**data)

                        # Auto-generate connectors if missing or incomplete
                        new_connectors = generate_connectors_from_equations(model)
                        if len(new_connectors) > len(model.connectors):
                            model.connectors = new_connectors

                        models.append(model)
                except (json.JSONDecodeError, ValueError) as e:
                    continue
    # Sort by updated_at, handling None values and timezone-aware vs naive datetimes
    def get_sort_key(m):
        dt = m.updated_at or m.created_at
        if dt is None:
            return datetime.min
        # Convert to naive datetime for comparison
        if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
    return sorted(models, key=get_sort_key, reverse=True)


def get_model(model_id: str) -> Optional[Model]:
    """Get a model by ID. Auto-generates missing connectors from equations."""
    ensure_models_dir()
    
    # Search for the model file in all directories
    path = find_model_path(model_id)
    if not path:
        return None
    
    try:
        with open(path, "r") as f:
            data = json.load(f)
            
            # Add category if from subdirectory
            parent_dir = os.path.basename(os.path.dirname(path))
            if parent_dir and parent_dir != "models":
                data["category"] = parent_dir
            
            model = Model(**data)

            # Auto-generate connectors if missing or incomplete
            from app.core.model import generate_connectors_from_equations
            new_connectors = generate_connectors_from_equations(model)
            if len(new_connectors) > len(model.connectors):
                model.connectors = new_connectors

            return model
    except (json.JSONDecodeError, ValueError):
        return None


def create_model(model_data: Union[Model, ModelCreate]) -> Model:
    """Create a new model. Accepts both Model and ModelCreate objects."""
    ensure_models_dir()
    now = datetime.now(timezone.utc)

    # Handle both Model and ModelCreate inputs
    model = Model(
        id=str(uuid.uuid4()),
        name=model_data.name,
        description=model_data.description,
        stocks=model_data.stocks,
        flows=model_data.flows,
        variables=model_data.variables,
        connectors=model_data.connectors,
        time_settings=model_data.time_settings,
        created_at=now,
        updated_at=now,
    )
    save_model(model)

    # Return model with connectors populated by save_model
    return model


def update_model(model_id: str, update_data: ModelUpdate) -> Optional[Model]:
    """Update an existing model."""
    model = get_model(model_id)
    if not model:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    model_dict = model.model_dump()
    model_dict.update(update_dict)
    model_dict["updated_at"] = datetime.now(timezone.utc)

    updated_model = Model(**model_dict)
    save_model(updated_model)
    return updated_model


def save_model(model: Model) -> None:
    """Save a model to disk. Auto-generates missing connectors before saving."""
    ensure_models_dir()

    # Auto-generate missing connectors before saving
    from app.core.model import generate_connectors_from_equations
    new_connectors = generate_connectors_from_equations(model)
    if len(new_connectors) > len(model.connectors):
        model.connectors = new_connectors

    path = get_model_path(model.id)
    with open(path, "w") as f:
        json.dump(model.model_dump(mode="json"), f, indent=2, default=str)


def delete_model(model_id: str) -> bool:
    """Delete a model by ID."""
    # Find the model in any subdirectory
    path = find_model_path(model_id)
    if path and os.path.exists(path):
        os.remove(path)
        return True
    return False
