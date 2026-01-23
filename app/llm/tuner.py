"""
Smart multi-phase AI tuning system with parallel simulations.
Phase 1: Analyze model relationships and build understanding
Phase 2: Use analysis to find equilibrium with multiple test simulations per step
"""
import os
import json
from typing import Optional
from dataclasses import dataclass
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor, as_completed

CUSTOM_INSTRUCTIONS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "custom_instructions.json"
)

# Pydantic models for structured output
class ParameterChange(BaseModel):
    parameter: str
    current_value: Optional[float] = None
    new_value: float
    reason: Optional[str] = None

class VariableHypothesis(BaseModel):
    variable: str
    hypothesis: str
    effect_on_stocks: str
    confidence: float

class AnalysisDocument(BaseModel):
    model_understanding: str
    variable_effects: list[VariableHypothesis]
    feedback_loops: list[str]
    key_relationships: list[str]
    recommended_strategy: str

class ProposedTest(BaseModel):
    test_name: str
    changes: list[ParameterChange]
    hypothesis: str

class OptimizationPlan(BaseModel):
    analysis: str
    proposed_tests: list[ProposedTest]
    reasoning: str

class TestEvaluation(BaseModel):
    best_test: str
    analysis: str
    goal_achieved: bool
    confidence: float
    final_changes: list[ParameterChange]

@dataclass
class TuningStep:
    iteration: int
    phase: str
    parameters: dict
    results_summary: str
    ai_analysis: str
    suggested_changes: list[dict]
    model_snapshot: dict
    test_results: Optional[dict] = None

@dataclass
class TuningResult:
    success: bool
    iterations: int
    final_model: dict
    steps: list[TuningStep]
    summary: str
    analysis_document: Optional[dict] = None

class TuneRequest(BaseModel):
    model: dict
    goal: str
    max_iterations: int = 20

def load_custom_instructions() -> dict:
    try:
        if os.path.exists(CUSTOM_INSTRUCTIONS_FILE):
            with open(CUSTOM_INSTRUCTIONS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def get_genai_client():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        try:
            from google import genai
            return genai.Client(api_key=key)
        except ImportError:
            pass
    return None

def run_simulation(model: dict) -> dict:
    from app.core.simulator import simulate
    from app.core.model import Model
    try:
        m = Model(**model) if isinstance(model, dict) else model
        r = simulate(m)
        for vals in r.values.values():
            for v in vals:
                if v != v or abs(v) == float('inf'):
                    return {"time": r.time, "values": r.values, "success": False, "error": "NaN/Inf"}
        return {"time": r.time, "values": r.values, "success": True, "error": None}
    except Exception as e:
        return {"time": [], "values": {}, "success": False, "error": str(e)}

def apply_changes_to_model(model: dict, changes: list) -> dict:
    """Apply changes and return new model."""
    m = json.loads(json.dumps(model))
    for c in changes:
        if isinstance(c, dict):
            param, val = c.get("parameter", ""), c.get("new_value")
        else:
            param, val = c.parameter, c.new_value
        if val is None:
            continue
        if isinstance(val, (int, float)):
            val = max(-1e6, min(1e6, val))
            if "rate" in param and val < 0:
                val = 0.001
        parts = param.split(":")
        if parts[0] == "stock" and len(parts) >= 3:
            for s in m.get("stocks", []):
                if s.get("name") == parts[1]:
                    s[parts[2]] = max(0, val) if parts[2] == "initial_value" else val
        elif parts[0] == "variable" and len(parts) >= 2:
            for v in m.get("variables", []):
                if v.get("name") == parts[1]:
                    v["equation"] = str(val)
    return m

def run_test_with_changes(model: dict, changes: list) -> dict:
    """Apply changes and run simulation."""
    test_model = apply_changes_to_model(model, changes)
    return run_simulation(test_model)

def summarize_results(results: dict) -> str:
    if not results.get("success"):
        return f"FAILED: {results.get('error')}"
    values = results.get("values", {})
    time = results.get("time", [])
    if not time:
        return "No data"
    lines = []
    for name, vals in values.items():
        if vals:
            i, f = vals[0], vals[-1]
            mi, ma = min(vals), max(vals)
            mean = sum(vals) / len(vals)
            chg = sum(1 for j in range(2, len(vals)) if (vals[j] > vals[j-1]) != (vals[j-1] > vals[j-2]))
            beh = "oscillating" if chg > len(vals)*0.3 else ("growing" if f > i*1.1 else ("declining" if f < i*0.9 else "stable"))
            lines.append(f"{name}: {i:.2f}->{f:.2f} (mean:{mean:.2f}, range:{mi:.2f}-{ma:.2f}) [{beh}]")
    return "; ".join(lines)

def run_multiple_simulations(model: dict, tests: list) -> dict:
    """Run multiple simulations in parallel and return results."""
    results = {}
    
    # Run baseline
    results["baseline"] = run_simulation(model)
    
    # Run each test
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for test in tests:
            test_name = test.test_name if hasattr(test, 'test_name') else test.get('test_name', 'unknown')
            changes = test.changes if hasattr(test, 'changes') else test.get('changes', [])
            # Convert Pydantic models to dicts if needed
            if changes and hasattr(changes[0], 'model_dump'):
                changes = [c.model_dump() for c in changes]
            futures[executor.submit(run_test_with_changes, model, changes)] = test_name
        
        for future in as_completed(futures):
            test_name = futures[future]
            try:
                results[test_name] = future.result()
            except Exception as e:
                results[test_name] = {"success": False, "error": str(e), "time": [], "values": {}}
    
    return results

def get_params(model: dict) -> dict:
    p = {}
    for s in model.get("stocks", []):
        p[f"stock:{s['name']}:initial_value"] = s.get("initial_value", 0)
    for v in model.get("variables", []):
        try:
            p[f"variable:{v['name']}"] = float(v.get("equation", "0"))
        except:
            pass
    return p

def get_model_description(model: dict) -> str:
    lines = [f"Model: {model.get('name', 'Unknown')}"]
    lines.append(f"Description: {model.get('description', 'N/A')}")
    lines.append("\nStocks:")
    for s in model.get("stocks", []):
        lines.append(f"  - {s['name']} (initial: {s.get('initial_value', 0)})")
    lines.append("\nFlows:")
    for f in model.get("flows", []):
        direction = f"from {f.get('from_stock', 'outside')} to {f.get('to_stock', 'outside')}"
        lines.append(f"  - {f['name']}: {f.get('equation', 'N/A')} ({direction})")
    lines.append("\nVariables (Parameters):")
    for v in model.get("variables", []):
        lines.append(f"  - {v['name']}: {v.get('equation', 'N/A')}")
    return "\n".join(lines)

def tune_model(model: dict, goal: str, max_iterations: int = 20) -> TuningResult:
    client = get_genai_client()
    if not client:
        return TuningResult(False, 0, model, [], "No API key", None)

    from google.genai import types
    
    current = json.loads(json.dumps(model))
    steps = []
    analysis_doc = None
    
    # Full context that persists across all iterations
    context = []
    context.append(f"=== MODEL STRUCTURE ===\n{get_model_description(model)}")
    context.append(f"\n=== GOAL ===\n{goal}")
    
    params = get_params(current)
    param_list = [p for p in params.keys() if "time:" not in p]
    
    # ========== PHASE 1: ANALYSIS ==========
    context.append("\n=== PHASE 1: ANALYSIS ===")
    
    # Run baseline + sensitivity tests for each parameter
    baseline = run_simulation(current)
    context.append(f"\nBaseline: {summarize_results(baseline)}")
    
    # Build sensitivity test set
    sensitivity_tests = []
    for param in param_list:
        sensitivity_tests.append({"test_name": f"{param}_up20", "changes": [{"parameter": param, "new_value": params[param] * 1.2}]})
        sensitivity_tests.append({"test_name": f"{param}_down20", "changes": [{"parameter": param, "new_value": params[param] * 0.8}]})
    
    # Run all sensitivity tests in parallel
    context.append("\n--- Sensitivity Analysis (running multiple simulations) ---")
    sens_results = run_multiple_simulations(current, sensitivity_tests)
    
    for test_name, result in sens_results.items():
        if test_name != "baseline":
            context.append(f"{test_name}: {summarize_results(result)}")
    
    # Ask AI to build analysis document
    analysis_prompt = f"""{chr(10).join(context)}

Based on these sensitivity tests, create a comprehensive analysis document.
Identify how each parameter affects the stocks, feedback loops, and a strategy for achieving: {goal}
"""
    
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=analysis_prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=AnalysisDocument,
            )
        )
        analysis_doc = resp.parsed
        
        context.append(f"\n=== ANALYSIS DOCUMENT ===")
        context.append(f"Understanding: {analysis_doc.model_understanding}")
        context.append(f"Feedback loops: {', '.join(analysis_doc.feedback_loops)}")
        context.append(f"Strategy: {analysis_doc.recommended_strategy}")
        for vh in analysis_doc.variable_effects:
            context.append(f"  {vh.variable}: {vh.effect_on_stocks}")
        
        steps.append(TuningStep(0, "analysis", params, summarize_results(baseline), 
                               analysis_doc.model_understanding, [], json.loads(json.dumps(current)), sens_results))
    except Exception as e:
        context.append(f"Analysis error: {e}")
        steps.append(TuningStep(0, "analysis", params, summarize_results(baseline), f"Error: {e}", [], json.loads(json.dumps(current))))
    
    # ========== PHASE 2: OPTIMIZATION WITH MULTIPLE TESTS ==========
    context.append("\n=== PHASE 2: OPTIMIZATION ===")
    
    for it in range(1, max_iterations + 1):
        res = run_simulation(current)
        summary = summarize_results(res)
        params = get_params(current)
        
        context.append(f"\n--- Iteration {it} ---")
        context.append(f"Current: {summary}")
        
        if not res.get("success"):
            steps.append(TuningStep(it, "optimization", params, summary, "Simulation failed", [], json.loads(json.dumps(current))))
            continue
        
        # Step 1: Ask AI to propose multiple tests
        plan_prompt = f"""{chr(10).join(context)}

Propose 3-4 different parameter adjustment tests to try. Each test should have a hypothesis.
Use the analysis document to inform your choices. Current params: {params}
"""
        
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=plan_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=OptimizationPlan,
                )
            )
            plan = resp.parsed
            
            context.append(f"Plan: {plan.reasoning}")
            
            # Step 2: Run all proposed tests in parallel
            test_results = run_multiple_simulations(current, plan.proposed_tests)
            
            # Format results for AI
            test_summaries = []
            for test in plan.proposed_tests:
                test_name = test.test_name
                if test_name in test_results:
                    test_summaries.append(f"{test_name} ({test.hypothesis}): {summarize_results(test_results[test_name])}")
            
            context.append(f"Test results:\n" + "\n".join(test_summaries))
            
            # Step 3: Ask AI to evaluate and choose best
            eval_prompt = f"""{chr(10).join(context)}

Evaluate these test results and choose the best one (or baseline if none improved).
Goal: {goal}
"""
            
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=eval_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=TestEvaluation,
                )
            )
            evaluation = resp.parsed
            
            context.append(f"Evaluation: {evaluation.analysis}")
            context.append(f"Best test: {evaluation.best_test}")
            
            changes = [{"parameter": c.parameter, "new_value": c.new_value, "reason": c.reason} for c in evaluation.final_changes]
            
            steps.append(TuningStep(it, "optimization", params, summary, evaluation.analysis, changes, 
                                   json.loads(json.dumps(current)), test_results))
            
            if evaluation.goal_achieved and evaluation.confidence > 0.7:
                if changes:
                    current = apply_changes_to_model(current, changes)
                return TuningResult(True, it, current, steps, f"Goal achieved! {evaluation.analysis}",
                                   analysis_doc.model_dump() if analysis_doc else None)
            
            if changes:
                current = apply_changes_to_model(current, changes)
                
        except Exception as e:
            context.append(f"Error: {e}")
            steps.append(TuningStep(it, "optimization", params, summary, f"Error: {e}", [], json.loads(json.dumps(current))))
    
    return TuningResult(False, max_iterations, current, steps,
                       f"Max iterations. Strategy was: {analysis_doc.recommended_strategy if analysis_doc else 'N/A'}",
                       analysis_doc.model_dump() if analysis_doc else None)
