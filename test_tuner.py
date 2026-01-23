import os
import json

# Load env manually
with open('.env') as f:
    for line in f:
        if '=' in line:
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

from app.llm.tuner import tune_model

print(f"GEMINI_API_KEY set: {bool(os.environ.get('GEMINI_API_KEY'))}")

# Predator-prey model
model = {
    "name": "Predator-Prey Model",
    "description": "Classic Lotka-Volterra predator-prey dynamics",
    "stocks": [
        {"name": "prey", "initial_value": 100, "equation": "", "position": {"x": 200, "y": 200}},
        {"name": "predators", "initial_value": 20, "equation": "", "position": {"x": 500, "y": 200}}
    ],
    "flows": [
        {"name": "prey_births", "equation": "prey * prey_birth_rate", "from_stock": None, "to_stock": "prey", "position": {"x": 100, "y": 200}},
        {"name": "predation", "equation": "prey * predators * predation_rate", "from_stock": "prey", "to_stock": None, "position": {"x": 350, "y": 200}},
        {"name": "predator_births", "equation": "prey * predators * predator_efficiency", "from_stock": None, "to_stock": "predators", "position": {"x": 350, "y": 300}},
        {"name": "predator_deaths", "equation": "predators * predator_death_rate", "from_stock": "predators", "to_stock": None, "position": {"x": 600, "y": 200}}
    ],
    "variables": [
        {"name": "prey_birth_rate", "equation": "0.5", "position": {"x": 100, "y": 100}},
        {"name": "predation_rate", "equation": "0.01", "position": {"x": 350, "y": 100}},
        {"name": "predator_efficiency", "equation": "0.005", "position": {"x": 350, "y": 400}},
        {"name": "predator_death_rate", "equation": "0.2", "position": {"x": 600, "y": 100}}
    ],
    "connectors": [],
    "time_settings": {"start": 0, "end": 100, "dt": 0.1}
}

goal = "Find parameters that achieve dynamic equilibrium where both predator and prey populations oscillate around stable values without extinction or runaway growth"

print("Starting tuner with 15 iterations...")
result = tune_model(model, goal, max_iterations=15)

print(f"\nSuccess: {result.success}")
print(f"Iterations: {result.iterations}")
print(f"Summary: {result.summary}")

print("\n--- Steps ---")
for step in result.steps:
    print(f"\nIteration {step.iteration}:")
    print(f"  Analysis: {step.ai_analysis[:200]}...")
    if step.suggested_changes:
        for change in step.suggested_changes[:2]:
            print(f"  Change: {change.get('parameter')} -> {change.get('new_value')}")
