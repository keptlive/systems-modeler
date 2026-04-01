"""
Systems Modeler: FastAPI Application
LLM-powered visual modeling tool for systems dynamics
"""
from dotenv import load_dotenv
import os

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api import models, simulate, llm, analyze, observability
from app.mcp_server import create_sse_app

app = FastAPI(
    title="Systems Modeler",
    description="LLM-powered visual modeling tool for systems dynamics",
    version="1.0.0"
)

# CORS middleware for API access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(simulate.router, prefix="/api", tags=["simulation"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
app.include_router(analyze.router, prefix="/api", tags=["analysis"])
app.include_router(observability.router, prefix="/llm", tags=["observability"])

# Mount MCP server (SSE transport) - must be before static files
mcp_app = create_sse_app()
app.mount("/mcp", mcp_app)
# MCP endpoints: /mcp/info, /mcp/sse, /mcp/messages/

# Mount static files
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
async def root():
    """Serve the main HTML page."""
    index_path = os.path.join(static_path, "index.html")
    return FileResponse(index_path)

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
