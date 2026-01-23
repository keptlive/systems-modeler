import os
import json

# Load env manually
with open('.env') as f:
    for line in f:
        if '=' in line:
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

from app.llm.tuner import tune_model

# Better starting parameters for predator-prey
# For Lotka-Volterra equilibrium: prey* = d/c, predator* = a/b
# where a=prey_birth_rate, b=predation_rate, c=predator_efficiency, d=predator_death_rate
# With these params: prey*=0.2/0.005=40, predator*=0.4/0.008=50
model = {
    "name": "Predator-Prey Model",
    "description": "Classic Lotka-Volterra predator-prey dynamics",
    "stocks": [
        {"name": "prey", "initial_value": 40, "equation": "", "position": {"x": 200, "y": 200}},
        {"name": "predators", "initial_value": 50, "equation": "", "position": {"x": 500, "y": 200}}
    ],
    "flows": [
        {"name": "prey_births", "equation": "prey * prey_birth_rate", "from_stock": None, "to_stock": "prey", "position": {"x": 100, "y": 200}},
        {"name": "predation", "equation": "prey * predators * predation_rate", "from_stock": "prey", "to_stock": None, "position": {"x": 350, "y": 200}},
        {"name": "predator_births", "equation": "prey * predators * predator_efficiency", "from_stock": None, "to_stock": "predators", "position": {"x": 350, "y": 300}},
        {"name": "predator_deaths", "equation": "predators * predator_death_rate", "from_stock": "predators", "to_stock": None, "position": {"x": 600, "y": 200}}
    ],
    "variables": [
        {"name": "prey_birth_rate", "equation": "0.4", "position": {"x": 100, "y": 100}},
        {"name": "predation_rate", "equation": "0.008", "position": {"x": 350, "y": 100}},
        {"name": "predator_efficiency", "equation": "0.005", "position": {"x": 350, "y": 400}},
        {"name": "predator_death_rate", "equation": "0.2", "position": {"x": 600, "y": 100}}
    ],
    "connectors": [],
    "time_settings": {"start": 0, "end": 200, "dt": 0.05}
}

goal = "Achieve stable oscillating equilibrium where both predator and prey populations cycle around their equilibrium values without extinction or runaway growth"

print("Starting tuner with 10 iterations and better starting parameters...")
result = tune_model(model, goal, max_iterations=10)

print(f"\nSuccess: {result.success}")
print(f"Iterations: {result.iterations}")
print(f"Summary: {result.summary[:300]}...")

print("\n--- Final Parameters ---")
if result.final_model:
    for v in result.final_model.get("variables", []):
        print(f"  {v['name']}: {v['equation']}")
    for s in result.final_model.get("stocks", []):
        print(f"  {s['name']} initial: {s['initial_value']}")
