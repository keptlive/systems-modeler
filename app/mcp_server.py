"""
Systems Modeler MCP Server
Exposes systems dynamics simulation as MCP tools for AI agents.
Supports both stdio and SSE transport.
"""
import json
from typing import Optional
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.core.model import (
    Model, Stock, Flow, Variable, Connector, TimeSettings, Position,
    SimulationRequest
)
from app.core.simulator import simulate
from app.storage import models as storage
from app.llm.generator import generate_model, is_llm_available, LLMError
from app.llm.modifier import modify_model
from app.core.xmile_generator import generate_xmile


# Create MCP server with security settings for public access
mcp = FastMCP(
    "systems-modeler",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "sd.helloandy.net",
            "127.0.0.1:*",
            "localhost:*",
        ],
        allowed_origins=[
            "https://sd.helloandy.net",
            "http://127.0.0.1:*",
            "http://localhost:*",
        ],
    ),
)


def model_to_summary(m) -> dict:
    """Convert model to a summary dict."""
    return {
        "id": m.id,
        "name": m.name,
        "description": m.description[:200] if m.description else "",
        "category": m.category or "other",
        "stocks": len(m.stocks),
        "flows": len(m.flows),
        "variables": len(m.variables),
    }


@mcp.tool()
def list_models(
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20
) -> str:
    """Browse the model library with 1000+ pre-built systems dynamics models across 26 categories.

    Args:
        category: Filter by category (e.g. 'economics', 'epidemiology', 'climate', 'biology')
        search: Search keyword in model names and descriptions
        limit: Maximum number of results (default 20)
    """
    models = storage.list_models()

    if category:
        models = [m for m in models if m.category == category.lower()]

    if search:
        query = search.lower()
        models = [m for m in models if
                  query in m.name.lower() or
                  (m.description and query in m.description.lower())]

    models = models[:limit]
    result = [model_to_summary(m) for m in models]

    # Also collect categories
    all_models = storage.list_models()
    cats = {}
    for m in all_models:
        c = m.category or "other"
        cats[c] = cats.get(c, 0) + 1

    return json.dumps({
        "total_in_library": len(all_models),
        "returned": len(result),
        "categories": cats,
        "models": result
    }, indent=2)


@mcp.tool()
def get_model(model_id: str) -> str:
    """Get the full definition of a model including stocks, flows, variables, equations, and time settings.

    Args:
        model_id: The model ID to retrieve
    """
    model = storage.get_model(model_id)
    if not model:
        return json.dumps({"error": f"Model '{model_id}' not found"})

    return json.dumps(model.model_dump(), indent=2, default=str)


@mcp.tool()
def simulate_model(
    model_id: Optional[str] = None,
    model_json: Optional[dict] = None,
    start_time: float = 0,
    end_time: float = 100,
    dt: float = 0.25,
    integration_method: str = "euler"
) -> str:
    """Run a simulation on a systems dynamics model and return time series results.

    Args:
        model_id: ID of a library model to simulate
        model_json: JSON object of a custom model to simulate (alternative to model_id)
        start_time: Simulation start time (default 0)
        end_time: Simulation end time (default 100)
        dt: Time step (default 0.25)
        integration_method: 'euler' or 'rk4' (default 'euler')
    """
    if model_id:
        model = storage.get_model(model_id)
        if not model:
            return json.dumps({"error": f"Model '{model_id}' not found"})
    elif model_json:
        try:
            data = model_json if isinstance(model_json, dict) else json.loads(model_json)
            model = Model(**data)
        except Exception as e:
            return json.dumps({"error": f"Invalid model JSON: {str(e)}"})
    else:
        return json.dumps({"error": "Provide model_id or model_json"})

    ts = TimeSettings(
        start=start_time,
        end=end_time,
        dt=dt,
        integration_method=integration_method
    )

    try:
        result = simulate(model, ts)

        # Compute summary statistics
        summary = {}
        for name, values in result.values.items():
            vals = [v for v in values if isinstance(v, (int, float)) and abs(v) < 1e15]
            if vals:
                summary[name] = {
                    "initial": round(vals[0], 4),
                    "final": round(vals[-1], 4),
                    "min": round(min(vals), 4),
                    "max": round(max(vals), 4),
                    "mean": round(sum(vals) / len(vals), 4),
                }

        return json.dumps({
            "model": model.name,
            "time_points": len(result.time),
            "time_range": [result.time[0], result.time[-1]],
            "variables": list(result.values.keys()),
            "summary": summary,
            "data": {
                "time": result.time[::max(1, len(result.time) // 50)],
                **{k: v[::max(1, len(v) // 50)] for k, v in result.values.items()}
            }
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Simulation failed: {str(e)}"})


@mcp.tool()
def generate_model_from_description(description: str) -> str:
    """Generate a new systems dynamics model from a natural language description using AI.

    Args:
        description: Natural language description of the system to model (e.g. 'Population growth with births and deaths')
    """
    if not is_llm_available():
        return json.dumps({"error": "LLM not available"})

    try:
        model = generate_model(description)
        return json.dumps(model.model_dump(), indent=2, default=str)
    except LLMError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def modify_existing_model(
    model_id: Optional[str] = None,
    model_json: Optional[dict] = None,
    modification: str = ""
) -> str:
    """Modify an existing model using natural language instructions.

    Args:
        model_id: ID of a library model to modify
        model_json: JSON object of a custom model to modify
        modification: Natural language modification request (e.g. 'Add a vaccination flow')
    """
    if not is_llm_available():
        return json.dumps({"error": "LLM not available"})

    if model_id:
        model = storage.get_model(model_id)
        if not model:
            return json.dumps({"error": f"Model '{model_id}' not found"})
    elif model_json:
        try:
            data = model_json if isinstance(model_json, dict) else json.loads(model_json)
            model = Model(**data)
        except Exception as e:
            return json.dumps({"error": f"Invalid model JSON: {str(e)}"})
    else:
        return json.dumps({"error": "Provide model_id or model_json"})

    try:
        modified = modify_model(model, modification)
        return json.dumps(modified.model_dump(), indent=2, default=str)
    except LLMError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def compare_scenarios(
    model_id: str,
    scenarios: str
) -> str:
    """Run multiple simulations with different parameter overrides and compare results.

    Args:
        model_id: ID of the base model
        scenarios: JSON string of scenarios, e.g. [{"name": "High growth", "parameters": {"birth_rate": 0.05}}, {"name": "Low growth", "parameters": {"birth_rate": 0.01}}]
    """
    model = storage.get_model(model_id)
    if not model:
        return json.dumps({"error": f"Model '{model_id}' not found"})

    try:
        scenario_list = json.loads(scenarios)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid scenarios JSON"})

    results = {}
    for scenario in scenario_list:
        name = scenario.get("name", "unnamed")
        params = scenario.get("parameters", {})

        # Create modified model with parameter overrides
        mod = model.model_copy(deep=True)
        for var in mod.variables:
            if var.name in params:
                var.equation = str(params[var.name])
        for stock in mod.stocks:
            if stock.name in params:
                stock.initial_value = float(params[stock.name])

        result = simulate(mod)
        summary = {}
        for vname, values in result.values.items():
            vals = [v for v in values if isinstance(v, (int, float)) and abs(v) < 1e15]
            if vals:
                summary[vname] = {"final": round(vals[-1], 4), "max": round(max(vals), 4)}

        results[name] = summary

    return json.dumps({"model": model.name, "scenarios": results}, indent=2)


@mcp.tool()
def export_model_xmile(model_id: str) -> str:
    """Export a model to XMILE format for use with Vensim, Stella, iThink, and other SD tools.

    Args:
        model_id: ID of the model to export
    """
    model = storage.get_model(model_id)
    if not model:
        return json.dumps({"error": f"Model '{model_id}' not found"})

    xmile = generate_xmile(model)
    return xmile


def create_sse_app():
    """Create a Starlette app with SSE transport for the MCP server."""
    from starlette.routing import Route
    from starlette.responses import JSONResponse

    sse_app = mcp.sse_app()

    async def mcp_info(request):
        return JSONResponse({
            "name": "systems-modeler",
            "version": "1.0.0",
            "description": "Systems Dynamics Modeling MCP Server - simulate, analyze, and explore 1000+ pre-built models",
            "tools": [
                "list_models", "get_model", "simulate_model",
                "generate_model_from_description", "modify_existing_model",
                "compare_scenarios", "export_model_xmile"
            ]
        })

    # Add info route to existing SSE app
    sse_app.routes.insert(0, Route("/info", mcp_info))
    return sse_app
