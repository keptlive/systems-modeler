"""Read-only numerical MCP tools over Streamable HTTP, legacy SSE, and stdio."""
import json
import math
from statistics import mean
from typing import Optional, Annotated, Literal
from pydantic import Field, BaseModel, ConfigDict
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from app.core.model import Model, TimeSettings
from app.core.simulator import simulate
from app.storage import models as storage
from app.storage.catalog import list_summaries
from app.llm.generator import generate_model, is_llm_available
from app.llm.modifier import modify_model
from app.core.xmile_generator import generate_xmile
from app.storage import workspaces

GUIDE = """Search with list_models, inspect equations with get_model, validate, then simulate.
Use compare_scenarios to test changes. Numerical tools use no paid AI service and never
write files. AI draft tools call the configured provider and may incur charges.
Library models are illustrative legacy examples, not scientifically certified. Inspect
initial conditions, units, equations and source references before interpreting results.
Invalid equations return tool errors rather than substituted zeros. Euler uses
left-endpoint rates; RK4 integrates ordinary and hidden smoothing/material-delay stocks.
Fixed history delays and random functions require Euler. Set time_settings.random_seed
to replay stochastic runs; an automatically chosen effective seed is returned.
Use investigate_model for bounded full-horizon timestep comparisons and input evidence.
Results describe assumptions, not independently verified forecasts.
To drive a visible page, connect over HTTP/SSE and call open_workspace. Open its
private page_url, then inspect_workspace, update_workspace_model, run_workspace and
set_workspace_view. Use expected_revision to preserve concurrent browser edits.
The user's own agent authors models; page tools never call a server-side AI provider.
Prefer edit_workspace_elements for explicit changes; it retains unmentioned inputs.
inspect_workspace distinguishes desired view from browser acknowledgement and actual
view. Numerical success is not scientific validation. Use your own reasoning;
legacy paid AI drafting tools are optional and should be used only when requested.
"""
HOSTS = ['stockandflow.live', 'www.stockandflow.live', 'stockandflow.org',
         'www.stockandflow.org', 'sd.helloandy.net']
mcp = FastMCP('systems-modeler', instructions=GUIDE, website_url='https://stockandflow.live',
    streamable_http_path='/', stateless_http=True, json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
        allowed_hosts=HOSTS + ['127.0.0.1:*', 'localhost:*'],
        allowed_origins=['https://' + h for h in HOSTS] + ['http://127.0.0.1:*', 'http://localhost:*']))
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
AI = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True)
PAGE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)

def page_transport():
    if __name__=='__main__':
        raise ValueError('Visible page workspaces require the HTTP/SSE connection at https://stockandflow.live/mcp/; stdio numerical tools remain available')

@mcp.tool(annotations=PAGE)
def open_workspace(model_id: Optional[str]=None,model_json: Optional[dict]=None) -> dict:
    """Open a private temporary page for your own model reasoning. No paid AI or library writes.

    Return page_url to the user/open it in a browser. Treat workspace_key as a secret.
    HTTP/SSE only. Idle expiry one hour; sessions end when the app restarts.
    """
    page_transport()
    model=resolve_model(model_id,model_json) if model_id is not None or model_json is not None else Model()
    result=workspaces.create(model.model_dump(mode='json'))
    result['page_url']='https://stockandflow.live/#workspace='+result['workspace_key']
    result['next']='Open page_url, then inspect_workspace until browser.connected is true. Keep workspace_key private.'
    return result

@mcp.tool(annotations=READ)
def inspect_workspace(workspace_key: str) -> dict:
    """Inspect the private page model, revision, input checks and browser acknowledgement."""
    page_transport()
    from app.core.validation import inspect_inputs
    snapshot=workspaces.snapshot(workspace_key)
    snapshot['validation']=inspect_inputs(Model.model_validate(snapshot['model']))
    return snapshot

@mcp.tool(annotations=PAGE)
def update_workspace_model(workspace_key: str,model_json: dict,
                           expected_revision: Annotated[int,Field(ge=1)]) -> dict:
    """Replace this page's draft with your proposed model. Revision conflicts preserve newer edits.

    All model inputs/layout/units/provenance must be retained intentionally. Does not save to the library.
    The page displays input errors so you can inspect and correct a draft.
    """
    page_transport()
    result=workspaces.replace_model(workspace_key,model_json,expected_revision)
    from app.core.validation import inspect_inputs
    result['validation']=inspect_inputs(Model.model_validate(result['model']))
    return result

class WorkspaceElementEdit(BaseModel):
    model_config=ConfigDict(extra='forbid')
    element_type:Literal['stock','flow','variable']
    element_id:Optional[str]=None
    add:bool=False
    changes:dict

@mcp.tool(annotations=PAGE)
def edit_workspace_elements(workspace_key:str,edits:Annotated[list[WorkspaceElementEdit],Field(min_length=1,max_length=100)],
                             expected_revision:Annotated[int,Field(ge=1)],time_settings:Optional[TimeSettings]=None) -> dict:
    """Prefer this for targeted, atomic edits. All unmentioned elements, units, tables and sources survive.

    Update by element_id; add with add=true and a name. Allowed fields: name, units,
    equation, position; stocks also initial_value; flows also from_stock/to_stock.
    IDs cannot be overwritten. Rename dependent references explicitly in the same batch.
    Inspect returned validation before running. No deletions or persistent writes.
    """
    page_transport()
    result=workspaces.edit_elements(workspace_key,[edit.model_dump() for edit in edits],expected_revision,
                                    time_settings.model_dump() if time_settings else None)
    from app.core.validation import inspect_inputs
    result['validation']=inspect_inputs(Model.model_validate(result['model']))
    return result

@mcp.tool(annotations=PAGE)
def run_workspace(workspace_key: str,expected_revision: Annotated[int,Field(ge=1)]) -> dict:
    """Run the private page's exact current model and display those same results. No AI calls."""
    page_transport()
    state=workspaces.snapshot(workspace_key)
    if state['revision']!=expected_revision:
        raise workspaces.WorkspaceConflict(f"Revision conflict: current revision is {state['revision']}")
    result=simulate(Model.model_validate(state['model']))
    updated=workspaces.publish_result(workspace_key,result,expected_revision)
    updated['statistics']=summarize(result)
    updated['time_points']=len(result.time)
    updated['random_seed']=result.random_seed
    return updated

@mcp.tool(annotations=PAGE)
def set_workspace_view(workspace_key:str,section:Optional[Literal['diagram','chart','analytics','inputs']]=None,
                       fit_diagram:bool=False,select_element_id:Optional[str]=None,
                       expected_revision:Optional[Annotated[int,Field(ge=1)]]=None) -> dict:
    """Show diagram, chart, analytics or input inspection; optionally fit or select an element.

    Inspect browser.applied_revision afterward to confirm the page actually applied it.
    """
    page_transport()
    return workspaces.set_view(workspace_key,section,fit_diagram,select_element_id,expected_revision)

@mcp.tool(annotations=PAGE)
def close_workspace(workspace_key:str) -> dict:
    """Disconnect and erase this temporary session. Saved library models are unaffected."""
    page_transport();workspaces.close(workspace_key)
    return {'closed':True}

def resolve_model(model_id=None, model_json=None):
    if (model_id is None) == (model_json is None):
        raise ValueError('Provide exactly one of model_id or model_json')
    if model_id is not None:
        model = storage.get_model(model_id)
        if model is None:
            raise ValueError(f"Model '{model_id}' not found")
        return model
    return Model.model_validate(model_json)

def settings_for(model, start_time=None, end_time=None, dt=None, integration_method=None, random_seed=None, rtol=None, atol=None):
    changes = {'start': start_time, 'end': end_time, 'dt': dt, 'integration_method': integration_method, 'random_seed': random_seed, 'rtol': rtol, 'atol': atol}
    data = model.time_settings.model_dump()
    data.update({k: v for k, v in changes.items() if v is not None})
    return TimeSettings(**data)

def summarize(result):
    return {name: {'initial': vals[0], 'final': vals[-1], 'min': min(vals),
                   'max': max(vals), 'mean': mean(vals)}
            for name, vals in result.values.items()}

@mcp.tool(annotations=READ)
def list_models(category: Optional[str] = None, search: Optional[str] = None,
                limit: Annotated[int, Field(ge=1, le=100)] = 20,
                offset: Annotated[int, Field(ge=0)] = 0) -> dict:
    """Search the library with pagination; use get_model for full equations and settings."""
    all_rows = list_summaries()
    categories = {}
    for row in all_rows:
        cat = row['category']
        categories[cat] = categories.get(cat, 0) + 1
    rows = all_rows
    if category:
        rows = [m for m in rows if m['category'].casefold() == category.casefold()]
    if search:
        query = search.casefold()
        rows = [m for m in rows if query in (m['name'] + ' ' + m['description']).casefold()]
    selected = rows[offset:offset + limit]
    return {'total_in_library': len(all_rows), 'matched': len(rows), 'returned': len(selected),
            'offset': offset, 'next_offset': offset + limit if offset + limit < len(rows) else None,
            'categories': categories, 'models': selected}

@mcp.tool(annotations=READ)
def get_model(model_id: str) -> dict:
    """Read a complete model, equations, lookup tables and default time settings."""
    return resolve_model(model_id).model_dump(mode='json')

@mcp.tool(annotations=READ)
def validate_model(model_id: Optional[str] = None, model_json: Optional[dict] = None) -> dict:
    """Check structure, references and equations for one step; not scientific validation."""
    model = resolve_model(model_id, model_json)
    from app.core.validation import inspect_inputs
    return inspect_inputs(model)

@mcp.tool(annotations=READ)
def investigate_model(model_id: Optional[str] = None, model_json: Optional[dict] = None,
                      max_runs: Annotated[int, Field(ge=1, le=3)] = 3) -> dict:
    """Investigate inputs and full-horizon timestep sensitivity; no saved changes or AI.

    Compare original, half and quarter dt with exact model/engine hashes. Reports
    missing definitions, domain leads and closed-transfer sums. No invented repairs,
    no shortened horizon, and no claim of scientific validation. Stochastic runs
    are excluded from pathwise convergence comparisons. At most 3 bounded runs.
    """
    from app.core.diagnostics import investigate_model as investigate
    return investigate(resolve_model(model_id, model_json), max_runs)

@mcp.tool(annotations=READ)
def simulate_model(model_id: Optional[str] = None, model_json: Optional[dict] = None,
                   start_time: Optional[float] = None, end_time: Optional[float] = None,
                   dt: Optional[float] = None, integration_method: Optional[str] = None,
                   max_points: Annotated[int, Field(ge=2, le=2000)] = 200,
                   random_seed: Optional[Annotated[int, Field(strict=True, ge=0, le=4294967295)]] = None,
                   rtol: Optional[Annotated[float, Field(ge=1e-12, le=0.1)]] = None,
                   atol: Optional[Annotated[float, Field(gt=0)]] = None) -> dict:
    """Run Euler, RK4 or explicitly selected Radau, inheriting omitted settings from the model. No writes or paid AI.

    Returns full-series statistics and sampled data including both endpoints.
    Limits: 100,000 intervals, 500 elements, 1,000,000 retained scalar values and 1,000,000 work units (including hidden stages, random calls and RK4 evaluations). Invalid equations fail.
    Smoothing and fixed-duration material delays support RK4. Fixed history delays
    and random functions require Euler. random_seed overrides the model seed;
    omitted seeds inherit the model, with the effective seed returned for replay.
    """
    model = resolve_model(model_id, model_json)
    settings = settings_for(model, start_time, end_time, dt, integration_method, random_seed, rtol, atol)
    result = simulate(model, settings)
    n = len(result.time)
    count = min(max_points, n)
    indices = sorted({round(i * (n - 1) / (count - 1)) for i in range(count)})
    return {'model': model.name, 'time_points': n, 'time_range': [result.time[0], result.time[-1]],
            'settings': settings.model_dump(), 'integration_diagnostics': result.integration_diagnostics, 'random_seed': result.random_seed, 'variables': list(result.values),
            'summary': summarize(result), 'sampled': count < n,
            'data': {'time': [result.time[i] for i in indices],
                     **{k: [v[i] for i in indices] for k, v in result.values.items()}}}

@mcp.tool(annotations=READ)
def compare_scenarios(model_id: str, scenarios: str | list[dict],
                      random_seed: Optional[Annotated[int, Field(strict=True, ge=0, le=4294967295)]] = None) -> dict:
    """Compare 1-10 scenarios without changing the model.

    Accept a JSON array or JSON string: [{"name":"High", "parameters":{"birth_rate":0.05}}].
    Override existing variable equations or stock initial values with finite numbers.
    """
    model = resolve_model(model_id)
    rows = json.loads(scenarios) if isinstance(scenarios, str) else scenarios
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10:
        raise ValueError('Provide between one and ten scenarios')
    import secrets
    seed = random_seed if random_seed is not None else model.time_settings.random_seed
    if seed is None:
        seed = secrets.randbits(32)
    results, seeds = {}, {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError('Each scenario must be an object')
        name = row.get('name', f'Scenario {i + 1}')
        if not isinstance(name, str) or name in results:
            raise ValueError('Scenario names must be unique strings')
        mod = model.model_copy(deep=True)
        mod.time_settings = TimeSettings(**{**mod.time_settings.model_dump(), 'random_seed': seed})
        params = row.get('parameters', {})
        if not isinstance(params, dict):
            raise ValueError('parameters must be an object')
        by_name = {e.name: e for e in [*mod.variables, *mod.stocks]}
        stock_names = {s.name for s in mod.stocks}
        for key, value in params.items():
            if key not in by_name:
                raise ValueError(f"Unknown scenario parameter '{key}'")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Parameter '{key}' must be a finite number")
            element = by_name[key]
            if key in stock_names:
                element.initial_value, element.equation = value, ''
            else:
                element.equation = str(value)
        run = simulate(mod)
        results[name] = summarize(run)
        seeds[name] = run.random_seed
    return {'model': model.name, 'settings': {**model.time_settings.model_dump(), 'random_seed': seed}, 'scenarios': results,
            'random_seed': seed if any(v is not None for v in seeds.values()) else None,
            'scenario_random_seeds': seeds}

@mcp.tool(annotations=READ)
def analyze_model(model_id: Optional[str] = None, model_json: Optional[dict] = None,
                  include_descriptive: bool = True) -> dict:
    """Compute full default-run statistics without calling a paid AI provider."""
    model = resolve_model(model_id, model_json)
    result = simulate(model)
    report = {'model': model.name, 'settings': model.time_settings.model_dump(),
              'time_points': len(result.time), 'random_seed': result.random_seed, 'statistics': summarize(result)}
    if include_descriptive and result.values:
        from app.llm.analyzer import descriptive_analysis
        report['descriptive'] = descriptive_analysis(result.model_dump())
    return report

@mcp.tool(annotations=READ)
def export_model_xmile(model_id: Optional[str] = None, model_json: Optional[dict] = None) -> str:
    """Export a saved or inline model as XMILE XML, including lookup tables."""
    return generate_xmile(resolve_model(model_id, model_json))

@mcp.tool(annotations=AI)
def generate_model_from_description(description: Annotated[str, Field(min_length=1, max_length=10000)]) -> dict:
    """Draft a model with the configured AI provider (may incur charges). Does not save it."""
    if not is_llm_available():
        raise ValueError('AI generation unavailable: configure GEMINI_API_KEY or OPENROUTER_API_KEY')
    return generate_model(description).model_dump(mode='json')

@mcp.tool(annotations=AI)
def modify_existing_model(model_id: Optional[str] = None, model_json: Optional[dict] = None,
                          modification: Annotated[str, Field(min_length=1, max_length=10000)] = '') -> dict:
    """Draft an AI modification (may incur charges); never overwrites the source."""
    model = resolve_model(model_id, model_json)
    if not is_llm_available():
        raise ValueError('AI modification unavailable: configure GEMINI_API_KEY or OPENROUTER_API_KEY')
    return modify_model(model, modification).model_dump(mode='json')

@mcp.resource('systems://guide')
def modeling_guide() -> str:
    """Workflow, numerical assumptions and library limitations."""
    return GUIDE

@mcp.resource('systems://engine')
def engine_contract() -> str:
    """Machine-readable capabilities for planning compatible, reproducible models."""
    from app.core.equations import SAFE_FUNCTIONS, CONTEXT_FUNCTIONS
    return json.dumps({
        'version': '1.8.0',
        'test_inputs': 'STEP/PULSE/RAMP and their arguments are evaluated at accepted times and held over each timestep for Euler and RK4. Other time-dependent equations retain normal stage evaluation. Reduce DT to resolve off-grid events.',
        'pulse': 'PULSE(magnitude, first_time[, interval]): magnitude/DT for one DT; zero or omitted interval means one event. Not the Vensim start/width signature.',
        'integration_methods': ['euler', 'rk4', 'radau'],
        'random_binomial': {'signature': 'RANDOM_BINOMIAL(n,p[,seed])', 'scope': 'explicit extension; Euler only',
                            'trials': 'integer0..1000000; exact bounded Bernoulli summation',
                            'probability': '[0,1]', 'cost': 'n work units per new callsite/accepted-time sample, combined with integration budget',
                            'cache': 'One sample per callsite/time; unchanged parameters required on retry',
                            'generator': 'NumPy PCG64; runtime/library version is part of reproducibility'},
        'radau': {'selection': 'explicit only; never automatic', 'dt': 'retained output spacing; internal steps are adaptive',
                  'rtol': {'default': 1e-6, 'minimum': 1e-12, 'maximum': 0.1},
                  'atol': {'default': 1e-9, 'minimum': 'positive finite'},
                  'unsupported': ['random functions', 'delay/smooth', 'STEP/PULSE/RAMP', 'time-triggered conditionals/comparisons/discrete functions including TIME aliases', 'time-driven lookups across all interpolation modes, including TIME aliases and inline points', 'standard XMILE export'],
                  'work': 'All model evaluations including RHS/Jacobian probes and retained outputs count toward the 1,000,000 work limit'},
        'source_review': 'Known citation mismatches are warnings in validate_model; corrected citations do not establish equation fidelity. Read the model description and source evidence.',
        'syntax': ['lazy IF THEN ELSE(condition, yes, no)', 'XMILE brace comments',
                   'XMILE left-associated comparisons with relational precedence above equality'],
        'functions': sorted(set(SAFE_FUNCTIONS) | set(CONTEXT_FUNCTIONS)),
        'hidden_states': 'Smoothing and fixed-duration material delays support Euler and RK4',
        'euler_only': ['fixed history delays', 'random functions'],
        'seed': {'field': 'time_settings.random_seed', 'range': [0, 4294967295],
                 'effective_seed_result_field': 'random_seed',
                 'policy': 'Independent call streams, one draw per call per time; explicit function seeds override the run seed'},
        'limits': {'elements': 500, 'intervals': 100000, 'retained_samples': 100001, 'retained_scalar_values': 1000000, 'work_units': 1000000,
                   'per_interval': 'Explicit elements + hidden stages + random calls; RK4 multiplies this by five'},
        'investigation': {'tool': 'investigate_model', 'max_runs': 3,
                          'grids': ['dt', 'dt/2', 'dt/4'], 'changes_inputs': False,
                          'stochastic_path_convergence': 'not evaluated'},
        'unsupported': ['arrays', 'nested models', 'queues', 'conveyors', 'macros',
                        'nonnegative stock constraints', 'changing material/fixed delay duration',
                        'changing stateful order', 'algebraic loop solvers'],
        'interpretation': 'Numerical completion and convergence evidence do not establish scientific validity'
    }, indent=2)

@mcp.resource('systems://models/{model_id}')
def model_resource(model_id: str) -> str:
    """A complete model as JSON."""
    return json.dumps(resolve_model(model_id).model_dump(mode='json'))

@mcp.resource('systems://workspace-guide')
def workspace_guide() -> str:
    """Page-control workflow, preservation, concurrency and capability boundaries."""
    return '''Use HTTP/SSE at https://stockandflow.live/mcp/ for visible pages.
open_workspace(model_id or model_json) returns a private page_url and workspace_key.
Open the URL, then inspect_workspace until browser.connected and applied_revision
confirm that the page loaded. Prefer edit_workspace_elements with stable element IDs
and expected_revision. It retains every unmentioned element, table, unit, source and
setting. Full replacement through update_workspace_model is explicit. No operation
implicitly saves to the library. Inspect validation before run_workspace. That tool
publishes the exact result to the browser, without a second stochastic run.
set_workspace_view supports diagram/chart/analytics/inputs, fitting and selection.
Confirm browser.applied_revision, browser.view and browser.error afterward.
Inspect after a revision conflict; do not blindly retry an overwrite. The page pauses
while a user edits and offers a choice when both sides changed the model.
Private session keys grant control of one temporary page. Keep them private; do not
put them in public messages. Sessions expire after one idle hour or server restart.
close_workspace revokes access. Page tools use no server AI provider. Use your own
reasoning and report source fidelity, units, assumptions and numerical limitations.
Finite output, statistical patterns and tail stability do not establish scientific validity.'''

@mcp.prompt()
def investigate_system(question: str) -> str:
    """Plan a transparent systems-modeling investigation."""
    return (f'Investigate: {question}\nSearch the library, inspect equations and initial conditions, '
            'state assumptions and units, validate, simulate, and compare scenarios. '
            'Report settings, parameter changes, numerical limitations and unverified source claims. '
            'Use your own reasoning. For a visible page, open_workspace, make targeted revision-checked '
            'edits, run_workspace, set_workspace_view, and verify the browser acknowledgement. '
            'Use optional server AI drafting only if the user requests it.')

def create_sse_app():
    """Preserve legacy SSE while adding Streamable HTTP at /mcp/."""
    from starlette.routing import Route
    from starlette.responses import JSONResponse
    app = mcp.streamable_http_app()
    app.routes.extend(mcp.sse_app().routes)
    async def info(request):
        tools = await mcp.list_tools()
        return JSONResponse({'name': 'systems-modeler', 'version': '1.8.0',
            'streamable_http': 'https://stockandflow.live/mcp/',
            'sse': 'https://stockandflow.live/mcp/sse', 'tools': [t.name for t in tools],
            'documentation': 'https://stockandflow.live/guide'})
    app.routes.insert(0, Route('/info', info))
    return app

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    mcp.run(transport='stdio')
