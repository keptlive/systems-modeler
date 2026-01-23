import os
import json

with open('.env') as f:
    for line in f:
        if '=' in line:
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

from app.llm.tuner import tune_model

model = {
    "name": "Predator-Prey",
    "description": "Lotka-Volterra predator-prey dynamics",
    "stocks": [
        {"name": "prey", "initial_value": 40},
        {"name": "predators", "initial_value": 40}
    ],
    "flows": [
        {"name": "prey_births", "equation": "prey * prey_birth_rate", "from_stock": None, "to_stock": "prey"},
        {"name": "predation", "equation": "prey * predators * predation_rate", "from_stock": "prey", "to_stock": None},
        {"name": "predator_births", "equation": "prey * predators * predator_efficiency", "from_stock": None, "to_stock": "predators"},
        {"name": "predator_deaths", "equation": "predators * predator_death_rate", "from_stock": "predators", "to_stock": None}
    ],
    "variables": [
        {"name": "prey_birth_rate", "equation": "0.4"},
        {"name": "predation_rate", "equation": "0.01"},
        {"name": "predator_efficiency", "equation": "0.005"},
        {"name": "predator_death_rate", "equation": "0.2"}
    ],
    "time_settings": {"start": 0, "end": 100, "dt": 0.05}
}

goal = "Achieve stable oscillating equilibrium where both populations cycle without extinction"

print("Starting smart tuner with analysis phase + parallel simulations...")
result = tune_model(model, goal, max_iterations=15)

print(f"\n{'='*60}")
print(f"SUCCESS: {result.success}")
print(f"Iterations: {result.iterations}")
print(f"\nSummary: {result.summary[:400]}")

if result.analysis_document:
    print(f"\n{'='*60}")
    print("ANALYSIS DOCUMENT:")
    print(f"Understanding: {result.analysis_document.get('model_understanding', 'N/A')[:300]}")
    print(f"Strategy: {result.analysis_document.get('recommended_strategy', 'N/A')[:200]}")
    print("Feedback loops:", result.analysis_document.get('feedback_loops', []))

print(f"\n{'='*60}")
print("ITERATION HISTORY:")
for step in result.steps:
    print(f"\n[{step.phase.upper()} {step.iteration}] {step.ai_analysis[:100]}...")
    if step.suggested_changes:
        for c in step.suggested_changes[:2]:
            print(f"  -> {c.get('parameter')}: {c.get('new_value')}")

print(f"\n{'='*60}")
print("FINAL PARAMETERS:")
for v in result.final_model.get("variables", []):
    print(f"  {v['name']}: {v['equation']}")
