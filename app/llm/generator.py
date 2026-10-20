"""
LLM-based model generation using Google Gemini Flash 2.0.
"""
import os
import json
from typing import Optional

from app.core.model import Model, Stock, Flow, Variable, Connector, TimeSettings, Position
from app.llm.prompts import get_generate_messages


class LLMError(Exception):
    """Error in LLM operation."""
    pass


def get_llm_client():
    """Get LLM client. Prioritizes Gemini, falls back to OpenRouter."""
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            return genai, "gemini"
        except ImportError:
            pass

    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
            )
            return client, "openrouter"
        except ImportError:
            pass

    return None, None


def _call_llm(messages: list[dict], json_mode: bool = True) -> str:
    """Call the LLM."""
    client, provider = get_llm_client()
    if not client:
        raise LLMError("No LLM API key found. Set GEMINI_API_KEY or OPENROUTER_API_KEY.")

    if provider == "gemini":
        system_prompt = ""
        user_prompt = ""
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            elif msg["role"] == "user":
                user_prompt = msg["content"]

        full_prompt = f"{system_prompt}\n\nUser request: {user_prompt}"
        model = client.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            full_prompt,
            generation_config={
                "response_mime_type": "application/json" if json_mode else "text/plain",
                "max_output_tokens": 4096,
            }
        )
        return response.text

    if provider == "openrouter":
        kwargs = {
            "model": "google/gemini-2.0-flash-001",
            "messages": messages,
            "max_tokens": 4096,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    raise LLMError("Unknown LLM provider")


def call_llm(messages: list[dict], json_mode: bool = True) -> str:
    """Optional legacy drafting; never expose a provider exception or credential URL."""
    try:
        return _call_llm(messages,json_mode)
    except LLMError:
        raise
    except Exception:
        raise LLMError('Optional server AI could not complete the request. Connect your own agent through MCP, or contact the site operator.') from None


def parse_model_json(json_str: str) -> dict:
    """Parse JSON from LLM response."""
    if "```json" in json_str:
        start = json_str.find("```json") + 7
        end = json_str.find("```", start)
        json_str = json_str[start:end].strip()
    elif "```" in json_str:
        start = json_str.find("```") + 3
        end = json_str.find("```", start)
        json_str = json_str[start:end].strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise LLMError(f"Invalid JSON: {e}")


def dict_to_model(data: dict) -> Model:
    """Convert dict to Model, converting numbers to strings for equations."""
    stocks = []
    for s in data.get("stocks", []):
        pos = s.get("position", {})
        stocks.append(Stock(
            **({"id": str(s["id"])} if s.get("id") else {}),
            name=str(s["name"]),
            units=s.get("units"),
            initial_value=float(s.get("initial_value", 0)),
            equation=str(s.get("equation", "")),
            position=Position(x=float(pos.get("x", 300)), y=float(pos.get("y", 200)))
        ))

    flows = []
    for f in data.get("flows", []):
        pos = f.get("position", {})
        flows.append(Flow(
            **({"id": str(f["id"])} if f.get("id") else {}),
            name=str(f["name"]),
            units=f.get("units"),
            equation=str(f.get("equation", "0")),
            from_stock=str(f.get("from_stock")) if f.get("from_stock") else None,
            to_stock=str(f.get("to_stock")) if f.get("to_stock") else None,
            position=Position(x=float(pos.get("x", 300)), y=float(pos.get("y", 300)))
        ))

    variables = []
    for v in data.get("variables", []):
        pos = v.get("position", {})
        variables.append(Variable(
            **({"id": str(v["id"])} if v.get("id") else {}),
            name=str(v["name"]),
            units=v.get("units"),
            equation=str(v.get("equation", "0")),
            position=Position(x=float(pos.get("x", 500)), y=float(pos.get("y", 200)))
        ))

    connectors = []
    for c in data.get("connectors", []):
        from_el = c.get("from_element") or c.get("from")
        to_el = c.get("to_element") or c.get("to")
        if from_el and to_el:
            connectors.append(Connector(
                from_element=str(from_el),
                to_element=str(to_el)
            ))

    ts = data.get("time_settings", {})
    time_settings = TimeSettings(
        start=float(ts.get("start", 0)),
        end=float(ts.get("end", 100)),
        dt=float(ts.get("dt", 0.25)),
        integration_method=ts.get("integration_method", "euler"),
    )

    return Model(
        name=str(data.get("name", "Generated Model")),
        description=str(data.get("description", "")),
        source=data.get("source"),
        reference=data.get("reference"),
        stocks=stocks,
        flows=flows,
        variables=variables,
        connectors=connectors,
        tables=data.get("tables", []),
        category=data.get("category"),
        time_settings=time_settings
    )


def generate_model(description: str) -> Model:
    """Generate a model from natural language."""
    messages = get_generate_messages(description)
    response = call_llm(messages, json_mode=True)
    data = parse_model_json(response)
    return dict_to_model(data)


def is_llm_available() -> bool:
    """Check if LLM is available."""
    client, provider = get_llm_client()
    return client is not None
