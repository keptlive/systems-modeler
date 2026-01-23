import os
import json

# Load env
with open('.env') as f:
    for line in f:
        if '=' in line:
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

from app.llm.tuner import tune_model

# Classic predator-prey with balanced initial conditions
model = {
    "name": "Predator-Prey",
    "description": "Lotka-Volterra model",
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
    "connectors": [],
    "time_settings": {"start": 0, "end": 100, "dt": 0.05}
}

goal = "Achieve stable oscillating equilibrium where both predator and prey populations cycle without extinction or runaway growth"

print("Running tuner with 25 iterations...")
result = tune_model(model, goal, max_iterations=25)

print(f"\nSUCCESS: {result.success}")
print(f"Iterations: {result.iterations}")
print(f"Summary: {result.summary[:300]}...")

# Show key iterations
print("\n--- Key Iterations ---")
for step in result.steps[::5]:  # Every 5th iteration
    print(f"[{step.iteration}] {step.ai_analysis[:80]}...")
    if step.suggested_changes:
        for c in step.suggested_changes[:2]:
            print(f"  -> {c.get('parameter')}: {c.get('new_value')}")

# Final params
print("\n--- Final Parameters ---")
for v in result.final_model.get("variables", []):
    print(f"  {v['name']}: {v['equation']}")
