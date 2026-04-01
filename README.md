# Stock & Flow — Systems Dynamics Simulator

A visual systems dynamics simulator with AI-powered model generation and an MCP server for AI agent integration. Includes a library of 1,078 pre-built models across 26 categories.

**App:** [stockandflow.live](https://stockandflow.live)  
**Model Library:** [stockandflow.org](https://stockandflow.org)

## Features

- **Visual Model Editor** - Drag-and-drop canvas for stocks, flows, variables, and connectors
- **1,078 Pre-built Models** - Browse by category (economics, epidemiology, climate, biology, etc.)
- **Simulation Engine** - Euler and RK4 integration methods with configurable time settings
- **AI Model Generation** - Describe a system in natural language and get a working model
- **AI Model Modification** - Modify existing models with natural language instructions
- **Scenario Comparison** - Run multiple simulations with different parameters side by side
- **XMILE Export** - Export models for Vensim, Stella, iThink, and other SD tools
- **Advanced Charts** - Line, area, stacked, and phase plots with log scale and normalization
- **Analytics** - Statistical analysis of simulation results
- **MCP Server** - Full Model Context Protocol support for AI agent integration

## Quick Start

```bash
# Clone and install
git clone https://github.com/keptlive/systems-modeler.git
cd systems-modeler
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install mcp

# Run
uvicorn app.main:app --host 0.0.0.0 --port 3250

# Open http://localhost:3250
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | No | Google Gemini API key for AI features |
| `OPENROUTER_API_KEY` | No | OpenRouter API key (fallback for AI features) |

AI model generation/modification requires at least one of these keys.

## Architecture

```
app/
  main.py              # FastAPI app entry point
  mcp_server.py        # MCP server (SSE transport)
  api/
    models.py          # REST API - model CRUD
    simulate.py        # REST API - simulation
    llm.py             # REST API - AI generation/modification
    analyze.py         # REST API - analytics
    observability.py   # REST API - LLM observability
  core/
    model.py           # Pydantic data models
    simulator.py       # Euler/RK4 simulation engine
    xmile_generator.py # XMILE format export
  llm/
    generator.py       # LLM-based model generation
    modifier.py        # LLM-based model modification
    prompts.py         # Prompt templates
  storage/
    models.py          # Model library loader
models/                # 1,078 pre-built models (JSON)
static/
  index.html           # Single-page app
  css/style.css        # Dark theme, responsive
  js/
    app.js             # App initialization
    canvas.js          # SVG canvas editor
    simulation.js      # Simulation runner
    charts.js          # D3.js chart rendering
    library.js         # Model library browser
    llm-interface.js   # AI assistant UI
    analytics.js       # Statistical analysis
    ai-agent.js        # AI insights panel
```

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/models` | GET | List all models |
| `/api/models/{id}` | GET | Get model by ID |
| `/api/simulate` | POST | Run simulation |
| `/api/llm/generate` | POST | Generate model from description |
| `/api/llm/modify` | POST | Modify model with instructions |
| `/api/models/{id}/export/xmile` | GET | Export model as XMILE |
| `/health` | GET | Health check |

## MCP Server

The built-in MCP server exposes all functionality as tools for AI agents via SSE transport.

### Connection

- **SSE endpoint:** `https://stockandflow.live/mcp/sse`
- **Info endpoint:** `https://stockandflow.live/mcp/info`

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "systems-modeler": {
      "url": "https://stockandflow.live/mcp/sse"
    }
  }
}
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `list_models` | Browse the model library with category/search filters |
| `get_model` | Get full model definition (stocks, flows, equations) |
| `simulate_model` | Run simulation and get time series results |
| `generate_model_from_description` | Create model from natural language |
| `modify_existing_model` | Modify model with natural language |
| `compare_scenarios` | Compare multiple parameter scenarios |
| `export_model_xmile` | Export to XMILE format |

### Example: Python MCP Client

```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    async with sse_client("https://stockandflow.live/mcp/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List economics models
            result = await session.call_tool("list_models", {
                "category": "economics",
                "limit": 5
            })
            print(result.content[0].text)

            # Simulate a model
            result = await session.call_tool("simulate_model", {
                "model_id": "predator-prey-stable",
                "end_time": 100
            })
            print(result.content[0].text)

asyncio.run(main())
```

## Model Categories

Agriculture, Biology, Classic, Climate, Ecology, Economics, Education, Energy, Engineering, Environment, Epidemiology, Evolution, Finance, Healthcare, Management, Marine, Neuroscience, Other, Physics, Political, Psychology, Social, Technology, Test, Transportation, Urban

## Tech Stack

- **Backend:** FastAPI, Python 3.12
- **Simulation:** NumPy, SciPy, PySD
- **Frontend:** Vanilla JS, D3.js, SVG
- **AI:** Google Gemini / OpenRouter
- **MCP:** mcp-python SDK (SSE transport)
- **Deployment:** Uvicorn, systemd, nginx

## License

MIT
