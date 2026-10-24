"""
LLM-based model modification.
"""
import json
from app.core.model import Model
from app.llm.credentials import UserAI
from app.llm.prompts import get_modify_messages
from app.llm.generator import call_llm, parse_model_json, dict_to_model, LLMError
from app.core.equations import canonical_name


def modify_model(model: Model, modification: str, options: UserAI | None = None) -> Model:
    """
    Modify an existing model based on a natural language request.

    Args:
        model: The existing model to modify
        modification: Natural language description of the desired changes

    Returns:
        Modified Model object
    """
    # Convert model to JSON for the prompt
    model_dict = model.model_dump(mode="json", exclude={"id", "created_at", "updated_at"})
    model_json = json.dumps(model_dict, indent=2)

    # Get LLM response
    messages = get_modify_messages(model_json, modification)
    response = call_llm(messages, json_mode=True, **({"options": options} if options else {}))

    # Parse response
    data = parse_model_json(response)
    # A partial provider response must not erase unrelated model inputs.
    for field in ("name", "description", "source", "reference", "category", "stocks", "flows", "variables", "connectors", "tables", "time_settings"):
        if field not in data:
            data[field] = model_dict[field]
    if isinstance(data.get("time_settings"), dict):
        data["time_settings"] = {**model_dict["time_settings"], **data["time_settings"]}
    for field in ("stocks", "flows", "variables"):
        originals = model_dict[field]
        by_id = {item["id"]: item for item in originals}
        by_name = {canonical_name(item["name"]): item for item in originals}
        for item in data[field]:
            original = by_id.get(item.get("id")) or by_name.get(canonical_name(item.get("name", "")))
            if original:
                for key in ("id", "units"):
                    if key not in item:
                        item[key] = original.get(key)

    # Create new model, preserving the original ID
    new_model = dict_to_model(data)
    new_model.id = model.id
    new_model.created_at = model.created_at

    return new_model
