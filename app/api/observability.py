"""
API endpoints for LLM observability/transparency.
"""
import os
import json
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from app.llm.prompts import SYSTEM_PROMPT_GENERATE, SYSTEM_PROMPT_MODIFY

router = APIRouter()

CUSTOM_INSTRUCTIONS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "custom_instructions.json"
)

class CustomInstructions(BaseModel):
    generation: str = ""
    modification: str = ""
    analysis: str = ""
    tuning: str = ""

def load_custom_instructions() -> dict:
    try:
        if os.path.exists(CUSTOM_INSTRUCTIONS_FILE):
            with open(CUSTOM_INSTRUCTIONS_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {"generation": "", "modification": "", "analysis": "", "tuning": ""}

def save_custom_instructions(instructions: dict):
    with open(CUSTOM_INSTRUCTIONS_FILE, "w") as f:
        json.dump(instructions, f, indent=2)

@router.get("/prompts")
async def get_all_prompts():
    custom = load_custom_instructions()
    return {
        "model_generation": {
            "description": "Used when generating new models from natural language",
            "base_prompt": SYSTEM_PROMPT_GENERATE[:500] + "...",
            "custom_instructions": custom.get("generation", "")
        },
        "model_modification": {
            "description": "Used when modifying existing models",
            "base_prompt": SYSTEM_PROMPT_MODIFY[:500] + "...",
            "custom_instructions": custom.get("modification", "")
        },
        "smart_tuner": {
            "description": "Two-phase AI tuner with analysis and optimization",
            "phases": {
                "analysis": "Runs parallel sensitivity tests, identifies feedback loops, builds strategy",
                "optimization": "Proposes multiple tests per iteration, runs in parallel, picks best"
            },
            "custom_instructions": custom.get("tuning", "")
        }
    }

@router.get("/custom")
async def get_custom_instructions():
    return load_custom_instructions()

@router.post("/custom")
async def update_custom_instructions(instructions: CustomInstructions):
    data = {
        "generation": instructions.generation,
        "modification": instructions.modification,
        "analysis": instructions.analysis,
        "tuning": instructions.tuning
    }
    save_custom_instructions(data)
    return {"status": "saved", "instructions": data}

@router.get("", response_class=HTMLResponse)
async def observability_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Observability - Systems Modeler</title>
    <style>
        :root { --bg: #0d1117; --bg2: #161b22; --bg3: #21262d; --border: #30363d; --text: #c9d1d9; --muted: #8b949e; --accent: #58a6ff; --green: #3fb950; --purple: #a371f7; --orange: #d29922; --red: #f85149; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; padding: 20px; max-width: 1200px; margin: 0 auto; }
        h1 { color: var(--accent); margin-bottom: 10px; }
        h2 { color: var(--purple); font-size: 1.2em; margin-bottom: 10px; }
        h3 { color: var(--green); font-size: 1em; margin: 15px 0 10px; }
        .subtitle { color: var(--muted); margin-bottom: 30px; }
        .nav { margin-bottom: 20px; }
        .nav a { color: var(--accent); text-decoration: none; margin-right: 20px; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab { padding: 10px 20px; background: var(--bg2); border: 1px solid var(--border); border-radius: 8px; cursor: pointer; color: var(--muted); transition: all 0.2s; }
        .tab:hover { background: var(--bg3); }
        .tab.active { background: var(--accent); color: var(--bg); }
        .panel { display: none; }
        .panel.active { display: block; }
        .card { background: var(--bg2); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 20px; }
        .card-header { padding: 15px 20px; background: var(--bg3); border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .card-body { padding: 20px; }
        .badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 600; }
        .badge-blue { background: var(--accent); color: var(--bg); }
        .badge-green { background: var(--green); color: var(--bg); }
        .badge-orange { background: var(--orange); color: var(--bg); }
        .badge-purple { background: var(--purple); color: var(--bg); }
        pre { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 15px; overflow-x: auto; font-family: Monaco, monospace; font-size: 12px; max-height: 300px; overflow-y: auto; white-space: pre-wrap; }
        textarea { width: 100%; min-height: 120px; padding: 15px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-family: Monaco, monospace; font-size: 13px; resize: vertical; }
        textarea:focus { outline: none; border-color: var(--accent); }
        .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; background: var(--accent); color: var(--bg); }
        .btn:hover { background: #79b8ff; }
        .status { padding: 10px 15px; border-radius: 6px; margin-top: 15px; display: none; }
        .status.show { display: block; }
        .status.success { background: rgba(63, 185, 80, 0.2); color: var(--green); }
        .status.error { background: rgba(248, 81, 73, 0.2); color: var(--red); }
        .info-box { background: rgba(88, 166, 255, 0.1); border: 1px solid rgba(88, 166, 255, 0.3); border-radius: 8px; padding: 15px; margin-bottom: 20px; }
        .phase-box { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 15px; margin: 10px 0; }
        .phase-box h4 { color: var(--orange); margin-bottom: 8px; }
        .feature-list { list-style: none; padding-left: 0; }
        .feature-list li { padding: 5px 0; padding-left: 20px; position: relative; }
        .feature-list li:before { content: "→"; position: absolute; left: 0; color: var(--green); }
        .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        @media (max-width: 768px) { .two-col { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <nav class="nav"><a href="/">← Back to App</a><a href="/api/llm/status">API Status</a></nav>
    <h1>LLM Observability</h1>
    <p class="subtitle">AI transparency and customization for Systems Modeler</p>

    <div class="tabs">
        <div class="tab active" data-tab="tuner">Smart Tuner</div>
        <div class="tab" data-tab="generation">Model Generation</div>
        <div class="tab" data-tab="modification">Model Modification</div>
        <div class="tab" data-tab="custom">Custom Instructions</div>
    </div>

    <!-- Smart Tuner Panel -->
    <div class="panel active" id="panel-tuner">
        <div class="card">
            <div class="card-header">
                <h2>Smart Two-Phase Tuner</h2>
                <span class="badge badge-green">NEW</span>
            </div>
            <div class="card-body">
                <p style="color: var(--muted); margin-bottom: 15px;">AI-powered parameter tuning that understands your model before optimizing it.</p>
                
                <div class="two-col">
                    <div class="phase-box">
                        <h4>Phase 1: Analysis</h4>
                        <ul class="feature-list">
                            <li>Runs parallel sensitivity tests on all parameters</li>
                            <li>Identifies feedback loops (reinforcing & balancing)</li>
                            <li>Maps variable effects on stocks</li>
                            <li>Builds optimization strategy document</li>
                        </ul>
                    </div>
                    <div class="phase-box">
                        <h4>Phase 2: Optimization</h4>
                        <ul class="feature-list">
                            <li>Proposes 3-4 parameter tests per iteration</li>
                            <li>Runs all tests in parallel</li>
                            <li>Evaluates results and picks best</li>
                            <li>Maintains full context across iterations</li>
                        </ul>
                    </div>
                </div>

                <h3>How It Works</h3>
                <pre>1. Submit model + goal via POST /api/llm/tune
2. AI runs sensitivity analysis (±20% on each param)
3. AI builds analysis document with feedback loops
4. For each optimization iteration:
   - AI proposes multiple test configurations
   - All tests run in parallel
   - AI evaluates results against goal
   - Best configuration applied
5. Returns when goal achieved or max iterations</pre>

                <h3>API Endpoint</h3>
                <pre>POST /api/llm/tune
{
  "model": { ... model JSON ... },
  "goal": "Achieve stable oscillating equilibrium",
  "max_iterations": 20
}</pre>

                <h3>Response Includes</h3>
                <ul class="feature-list">
                    <li>success: boolean - whether goal was achieved</li>
                    <li>iterations: number of iterations run</li>
                    <li>final_model: optimized model parameters</li>
                    <li>analysis_document: AI understanding of model</li>
                    <li>steps: full history of all iterations</li>
                </ul>
            </div>
        </div>
    </div>

    <!-- Generation Panel -->
    <div class="panel" id="panel-generation">
        <div class="card">
            <div class="card-header"><h2>Model Generation Prompt</h2><span class="badge badge-blue">Gemini 2.5 Flash</span></div>
            <div class="card-body">
                <p style="color: var(--muted); margin-bottom: 10px;">Used when creating new models from natural language descriptions.</p>
                <pre id="gen-prompt">Loading...</pre>
            </div>
        </div>
    </div>

    <!-- Modification Panel -->
    <div class="panel" id="panel-modification">
        <div class="card">
            <div class="card-header"><h2>Model Modification Prompt</h2><span class="badge badge-blue">Gemini 2.5 Flash</span></div>
            <div class="card-body">
                <p style="color: var(--muted); margin-bottom: 10px;">Used when modifying existing models based on user requests.</p>
                <pre id="mod-prompt">Loading...</pre>
            </div>
        </div>
    </div>

    <!-- Custom Instructions Panel -->
    <div class="panel" id="panel-custom">
        <div class="card">
            <div class="card-header"><h2>Custom Instructions</h2><span class="badge badge-orange">Editable</span></div>
            <div class="card-body">
                <p style="color: var(--muted); margin-bottom: 15px;">Add custom instructions that are appended to the AI prompts.</p>
                
                <h3>Generation Instructions</h3>
                <textarea id="custom-gen" placeholder="Extra instructions for model generation..."></textarea>
                
                <h3>Modification Instructions</h3>
                <textarea id="custom-mod" placeholder="Extra instructions for model modification..."></textarea>
                
                <h3>Tuning Instructions</h3>
                <textarea id="custom-tune" placeholder="Extra instructions for the smart tuner..."></textarea>
                
                <button class="btn" onclick="saveCustom()" style="margin-top: 15px;">Save All</button>
                <div class="status" id="save-status"></div>
            </div>
        </div>
    </div>

    <div class="info-box">
        <p><strong>Powered by:</strong> Google Gemini 2.5 Flash with Pydantic structured output schemas for guaranteed valid JSON responses.</p>
    </div>

    <script>
        document.querySelectorAll(".tab").forEach(tab => {
            tab.addEventListener("click", () => {
                document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
                document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
                tab.classList.add("active");
                document.getElementById("panel-" + tab.dataset.tab).classList.add("active");
            });
        });

        async function loadData() {
            try {
                const resp = await fetch("/llm/prompts");
                const data = await resp.json();
                document.getElementById("gen-prompt").textContent = data.model_generation.base_prompt;
                document.getElementById("mod-prompt").textContent = data.model_modification.base_prompt;
                document.getElementById("custom-gen").value = data.model_generation.custom_instructions || "";
                document.getElementById("custom-mod").value = data.model_modification.custom_instructions || "";
                document.getElementById("custom-tune").value = data.smart_tuner.custom_instructions || "";
            } catch (e) { console.error(e); }
        }

        async function saveCustom() {
            const status = document.getElementById("save-status");
            try {
                const resp = await fetch("/llm/custom", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        generation: document.getElementById("custom-gen").value,
                        modification: document.getElementById("custom-mod").value,
                        analysis: "",
                        tuning: document.getElementById("custom-tune").value
                    })
                });
                if (resp.ok) {
                    status.textContent = "Saved!";
                    status.className = "status show success";
                } else throw new Error("Save failed");
            } catch (e) {
                status.textContent = "Error: " + e.message;
                status.className = "status show error";
            }
            setTimeout(() => status.classList.remove("show"), 3000);
        }

        loadData();
    </script>
</body>
</html>"""
