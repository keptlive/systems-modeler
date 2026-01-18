"""
LLM-based model modification.
"""
import json
from app.core.model import Model
from app.llm.prompts import get_modify_messages
from app.llm.generator import call_llm, parse_model_json, dict_to_model, LLMError


def modify_model(model: Model, modification: str) -> Model:
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
    response = call_llm(messages, json_mode=True)

    # Parse response
    data = parse_model_json(response)

    # Create new model, preserving the original ID
    new_model = dict_to_model(data)
    new_model.id = model.id
    new_model.created_at = model.created_at

    return new_model
