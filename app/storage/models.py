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


def list_models() -> list[Model]:
    """List all saved models. Auto-generates missing connectors from equations."""
    ensure_models_dir()
    from app.core.model import generate_connectors_from_equations

    models = []
    for filename in os.listdir(MODELS_DIR):
        if filename.endswith(".json"):
            try:
                with open(os.path.join(MODELS_DIR, filename), "r") as f:
                    data = json.load(f)
                    model = Model(**data)

                    # Auto-generate connectors if missing or incomplete
                    new_connectors = generate_connectors_from_equations(model)
                    if len(new_connectors) > len(model.connectors):
                        model.connectors = new_connectors

                    models.append(model)
            except (json.JSONDecodeError, ValueError):
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
    path = get_model_path(model_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
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
    path = get_model_path(model_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
