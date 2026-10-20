"""
Systems Modeler: FastAPI Application
LLM-powered visual modeling tool for systems dynamics
"""
from dotenv import load_dotenv
import os

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse, Response, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from fastapi.middleware.gzip import GZipMiddleware

from app.api import models, simulate, llm, analyze, observability, workspaces
from app.storage import models as model_storage
from app.mcp_server import create_sse_app, mcp


@asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield

app = FastAPI(
    title="Systems Modeler",
    description="LLM-powered visual modeling tool for systems dynamics",
    version="1.6.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exception):
    # Raw invalid inputs can contain NaN/Infinity, which cannot be JSON encoded.
    # Keep actionable field locations and messages without echoing user payloads.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exception.errors()
    ]})

# HEAD method support middleware
class HeadMethodMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "HEAD":
            request.scope["method"] = "GET"
            response = await call_next(request)
            headers = dict(response.headers)
            headers.pop("content-length", None)
            return Response(
                content=b"",
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type,
            )
        return await call_next(request)
# CORS middleware for API access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(HeadMethodMiddleware)

# Include API routers
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(simulate.router, prefix="/api", tags=["simulation"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
app.include_router(analyze.router, prefix="/api", tags=["analysis"])
app.include_router(observability.router, prefix="/llm", tags=["observability"])
app.include_router(workspaces.router,prefix='/api/workspaces',tags=['agent workspaces'])

# Mount MCP server (SSE transport) - must be before static files
mcp_app = create_sse_app()
app.mount("/mcp", mcp_app)
# MCP endpoints: /mcp/info, /mcp/sse, /mcp/messages/

# Mount static files
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/guide")
def guide():
    """Public usage, API and MCP documentation."""
    return FileResponse(os.path.join(static_path, "guide.html"))


@app.get("/library")
def library_page():
    return FileResponse(os.path.join(os.path.dirname(static_path), "sites", "library", "index.html"))

@app.get("/")
async def root():
    """Serve the main HTML page."""
    index_path = os.path.join(static_path, "index.html")
    return FileResponse(index_path)

@app.get("/robots.txt")
async def robots_txt():
    """Serve robots.txt."""
    return PlainTextResponse(
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        "Sitemap: https://stockandflow.live/sitemap.xml\n"
        "\n"
        "# See https://llmstxt.org/\n"
        "llms.txt: https://stockandflow.live/llms.txt\n"
        "llms-full.txt: https://stockandflow.live/llms-full.txt\n"
    )


@app.get("/418346ee1187bc99f05f2cc2ac847780.txt")
async def indexnow_key():
    """Serve IndexNow verification key."""
    return PlainTextResponse("418346ee1187bc99f05f2cc2ac847780")


@app.get("/humans.txt")
async def humans_txt():
    """Serve humans.txt."""
    return PlainTextResponse(
        "/* TEAM */\n"
        "Creator: Andy\n"
        "Contact: andy@agentwire.email\n"
        "Site: https://stockandflow.live\n"
        "Description: Interactive systems dynamics simulator with AI model generation\n"
        "\n"
        "/* SITE */\n"
        "Standards: HTML5, CSS3, JavaScript ES6+\n"
        "Software: FastAPI, D3.js, SQLite\n"
        "Components: AI model generation, XMILE import/export, real-time simulation\n"
    )


@app.get("/llms.txt")
async def llms_txt():
    """Current API and MCP discovery documentation."""
    return FileResponse(os.path.join(static_path, "llms-full.txt"), media_type="text/plain")


@app.get("/llms-full.txt")
async def llms_full_txt():
    """Serve llms-full.txt — expanded documentation for LLMs."""
    llms_full_path = os.path.join(static_path, "llms-full.txt")
    if os.path.exists(llms_full_path):
        with open(llms_full_path, "r") as f:
            return PlainTextResponse(f.read())
    return PlainTextResponse("Not found", status_code=404)

@app.get("/sitemap.xml")
async def sitemap_xml():
    """Serve dynamic sitemap.xml with all models."""
    from datetime import date
    from urllib.parse import quote
    today = date.today().isoformat()
    parts = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    parts.append("  <url>")
    parts.append("    <loc>https://stockandflow.live/</loc>")
    parts.append("    <lastmod>" + today + "</lastmod>")
    parts.append("    <changefreq>weekly</changefreq>")
    parts.append("    <priority>1.0</priority>")
    parts.append("  </url>")
    try:
        all_models = model_storage.list_models()
        for m in all_models:
            mid = m.id if hasattr(m, "id") else m.get("id", "")
            if mid:
                parts.append("  <url>")
                parts.append("    <loc>https://stockandflow.live/?model=" + quote(mid) + "</loc>")
                parts.append("    <changefreq>monthly</changefreq>")
                parts.append("    <priority>0.6</priority>")
                parts.append("  </url>")
    except Exception:
        pass
    parts.append("</urlset>")
    xml = "\n".join(parts) + "\n"
    return PlainTextResponse(xml, media_type="application/xml")

@app.get("/health")
@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get('/api/schema')
def public_schema():
    return app.openapi()
