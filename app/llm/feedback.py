"""
AI Model Feedback System for Systems Modeler.
Provides:
1. Find Equilibrium - Adjust parameters to achieve steady state
2. Match Historical Data - Fit model to user-provided data
3. Refine Model - Iteratively improve based on user feedback
"""
import os
import json
import numpy as np
from typing import Optional
from dataclasses import dataclass
from scipy.optimize import minimize, differential_evolution
from app.core.model import Model
from app.core.simulator import simulate as simulate_model


@dataclass
class EquilibriumResult:
    """Result of equilibrium finding."""
    found: bool
    parameters: dict[str, float]
    equilibrium_values: dict[str, float]
    convergence_time: float
    message: str


@dataclass
class FitResult:
    """Result of data fitting."""
    success: bool
    parameters: dict[str, float]
    r_squared: float
    rmse: float
    fitted_values: dict[str, list[float]]
    message: str


@dataclass
class RefinementResult:
    """Result of model refinement."""
    success: bool
    suggestions: list[dict]
    modified_model: Optional[dict]
    explanation: str


def get_gemini_client():
    """Get configured Gemini client."""
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            return genai
        except ImportError:
            pass
    return None


def extract_parameters(model: Model) -> dict[str, tuple[float, float, float]]:
    """
    Extract adjustable parameters from model.
    Returns dict of {param_name: (current_value, min_bound, max_bound)}
    """
    params = {}

    # Extract from stocks (initial values)
    for stock in model.stocks:
        param_name = f"{stock.name}_initial"
        val = stock.initial_value
        # Set reasonable bounds
        if val > 0:
            params[param_name] = (val, val * 0.01, val * 100)
        elif val < 0:
            params[param_name] = (val, val * 100, val * 0.01)
        else:
            params[param_name] = (val, -100, 100)

    # Extract from variables (constants/rates)
    for var in model.variables:
        eq = var.equation.strip()
        # Only extract if equation is a simple number
        try:
            val = float(eq)
            param_name = var.name
            if val > 0:
                params[param_name] = (val, val * 0.01, val * 100)
            elif val < 0:
                params[param_name] = (val, val * 100, val * 0.01)
            else:
                params[param_name] = (val, -1, 1)
        except ValueError:
            continue

    return params


def update_model_parameters(model: Model, params: dict[str, float]) -> Model:
    """Create a new model with updated parameter values."""
    model_dict = model.model_dump()

    for param_name, value in params.items():
        # Update stock initial values
        if param_name.endswith("_initial"):
            stock_name = param_name.rsplit("_initial", 1)[0]
            for stock in model_dict["stocks"]:
                if stock["name"] == stock_name:
                    stock["initial_value"] = value
                    break
        else:
            # Update variable equations
            for var in model_dict["variables"]:
                if var["name"] == param_name:
                    var["equation"] = str(value)
                    break

    return Model(**model_dict)


def check_equilibrium(results: dict, threshold: float = 0.01) -> dict:
    """Check if simulation results show equilibrium."""
    values = results.get("values", {})
    time = results.get("time", [])

    if not values or not time:
        return {"reached": False}

    equilibrium_values = {}
    all_stable = True
    convergence_time = None

    for name, vals in values.items():
        arr = np.array(vals)
        if len(arr) < 10:
            all_stable = False
            continue

        # Check last 20% for stability
        check_start = int(len(arr) * 0.8)
        check_vals = arr[check_start:]

        mean_val = np.mean(check_vals)
        if mean_val == 0:
            variation = 0 if np.std(check_vals) < 0.001 else 1
        else:
            variation = np.std(check_vals) / abs(mean_val)

        if variation < threshold:
            equilibrium_values[name] = float(mean_val)
            # Find when stability started
            for i in range(len(arr) - 1, 0, -1):
                window = arr[max(0, i-5):i+1]
                if len(window) < 2:
                    continue
                w_mean = np.mean(window)
                w_var = np.std(window) / abs(w_mean) if w_mean != 0 else 0
                if w_var > threshold:
                    if convergence_time is None or time[i] < convergence_time:
                        convergence_time = time[i]
                    break
        else:
            all_stable = False

    return {
        "reached": all_stable and len(equilibrium_values) > 0,
        "values": equilibrium_values,
        "convergence_time": convergence_time
    }


def find_equilibrium(model: Model, target_stocks: list[str] = None,
                    max_iterations: int = 100) -> EquilibriumResult:
    """
    Find parameter values that lead to system equilibrium.

    Args:
        model: The system dynamics model
        target_stocks: Optional list of stocks that must reach equilibrium
        max_iterations: Maximum optimization iterations

    Returns:
        EquilibriumResult with found parameters
    """
    params = extract_parameters(model)
    if not params:
        return EquilibriumResult(
            found=False,
            parameters={},
            equilibrium_values={},
            convergence_time=0,
            message="No adjustable parameters found in model"
        )

    param_names = list(params.keys())
    initial_values = [params[p][0] for p in param_names]
    bounds = [(params[p][1], params[p][2]) for p in param_names]

    # Get stock names to check
    stock_names = target_stocks or [s.name for s in model.stocks]

    def objective(x):
        """Objective: minimize instability at end of simulation."""
        param_dict = {name: val for name, val in zip(param_names, x)}
        test_model = update_model_parameters(model, param_dict)

        try:
            results = simulate_model(test_model)
            values = results.get("values", {})

            total_instability = 0
            for stock_name in stock_names:
                if stock_name in values:
                    arr = np.array(values[stock_name])
                    if len(arr) > 10:
                        # Check last 20% for instability
                        check_vals = arr[int(len(arr) * 0.8):]
                        mean_val = np.mean(check_vals)
                        if mean_val != 0:
                            variation = np.std(check_vals) / abs(mean_val)
                            total_instability += variation

                        # Penalize large derivatives at end
                        end_derivative = abs(arr[-1] - arr[-2]) if len(arr) > 1 else 0
                        total_instability += end_derivative * 0.1

            return total_instability

        except Exception:
            return float('inf')

    try:
        # Use differential evolution for global optimization
        result = differential_evolution(
            objective,
            bounds=bounds,
            maxiter=max_iterations,
            seed=42,
            polish=True,
            tol=1e-4
        )

        # Create final model and simulate
        final_params = {name: val for name, val in zip(param_names, result.x)}
        final_model = update_model_parameters(model, final_params)
        final_results = simulate_model(final_model)

        eq_check = check_equilibrium(final_results)

        return EquilibriumResult(
            found=eq_check["reached"],
            parameters=final_params,
            equilibrium_values=eq_check.get("values", {}),
            convergence_time=eq_check.get("convergence_time", 0) or 0,
            message="Equilibrium found!" if eq_check["reached"] else
                   "Partial equilibrium achieved - some variables still varying"
        )

    except Exception as e:
        return EquilibriumResult(
            found=False,
            parameters={},
            equilibrium_values={},
            convergence_time=0,
            message=f"Optimization failed: {str(e)}"
        )


def fit_to_data(model: Model, historical_data: dict[str, list[float]],
                time_points: list[float], max_iterations: int = 200) -> FitResult:
    """
    Adjust model parameters to fit historical data.

    Args:
        model: The system dynamics model
        historical_data: Dict of {variable_name: [values at time_points]}
        time_points: Time points corresponding to historical data
        max_iterations: Maximum optimization iterations

    Returns:
        FitResult with optimized parameters and fit quality
    """
    params = extract_parameters(model)
    if not params:
        return FitResult(
            success=False,
            parameters={},
            r_squared=0,
            rmse=float('inf'),
            fitted_values={},
            message="No adjustable parameters found"
        )

    param_names = list(params.keys())
    bounds = [(params[p][1], params[p][2]) for p in param_names]

    # Prepare historical data arrays
    hist_arrays = {}
    for name, values in historical_data.items():
        hist_arrays[name] = np.array(values)

    # Adjust model time settings to cover historical data
    model_dict = model.model_dump()
    model_dict["time_settings"]["start"] = min(time_points)
    model_dict["time_settings"]["end"] = max(time_points)
    model_dict["time_settings"]["dt"] = (max(time_points) - min(time_points)) / (len(time_points) * 4)

    def objective(x):
        """Objective: minimize squared error between simulation and data."""
        param_dict = {name: val for name, val in zip(param_names, x)}
        test_model_dict = model_dict.copy()
        test_model = update_model_parameters(Model(**test_model_dict), param_dict)

        try:
            results = simulate_model(test_model)
            sim_time = np.array(results["time"])

            total_error = 0
            for var_name, hist_values in hist_arrays.items():
                if var_name in results["values"]:
                    sim_values = np.array(results["values"][var_name])

                    # Interpolate simulation to match historical time points
                    interp_values = np.interp(time_points, sim_time, sim_values)

                    # Calculate squared error
                    error = np.sum((interp_values - hist_values) ** 2)
                    total_error += error

            return total_error

        except Exception:
            return float('inf')

    try:
        result = differential_evolution(
            objective,
            bounds=bounds,
            maxiter=max_iterations,
            seed=42,
            polish=True,
            tol=1e-6
        )

        # Calculate final fit quality
        final_params = {name: val for name, val in zip(param_names, result.x)}
        final_model_dict = model_dict.copy()
        final_model = update_model_parameters(Model(**final_model_dict), final_params)
        final_results = simulate_model(final_model)

        sim_time = np.array(final_results["time"])
        fitted_values = {}
        total_ss_res = 0
        total_ss_tot = 0
        n_points = 0

        for var_name, hist_values in hist_arrays.items():
            if var_name in final_results["values"]:
                sim_values = np.array(final_results["values"][var_name])
                interp_values = np.interp(time_points, sim_time, sim_values)
                fitted_values[var_name] = interp_values.tolist()

                # Calculate R-squared components
                ss_res = np.sum((hist_values - interp_values) ** 2)
                ss_tot = np.sum((hist_values - np.mean(hist_values)) ** 2)
                total_ss_res += ss_res
                total_ss_tot += ss_tot
                n_points += len(hist_values)

        r_squared = 1 - (total_ss_res / total_ss_tot) if total_ss_tot > 0 else 0
        rmse = np.sqrt(total_ss_res / n_points) if n_points > 0 else float('inf')

        return FitResult(
            success=True,
            parameters=final_params,
            r_squared=float(r_squared),
            rmse=float(rmse),
            fitted_values=fitted_values,
            message=f"Fit completed. R² = {r_squared:.4f}, RMSE = {rmse:.4f}"
        )

    except Exception as e:
        return FitResult(
            success=False,
            parameters={},
            r_squared=0,
            rmse=float('inf'),
            fitted_values={},
            message=f"Fitting failed: {str(e)}"
        )


def refine_model(model: Model, simulation_results: dict,
                 feedback: str) -> RefinementResult:
    """
    Use AI to suggest model refinements based on user feedback.

    Args:
        model: Current model
        simulation_results: Results from last simulation
        feedback: User's feedback about what should change

    Returns:
        RefinementResult with suggestions and potentially modified model
    """
    client = get_gemini_client()

    if not client:
        return RefinementResult(
            success=False,
            suggestions=[],
            modified_model=None,
            explanation="AI refinement requires GEMINI_API_KEY to be set"
        )

    # Build prompt for AI
    prompt = """You are an expert systems dynamics modeler. Analyze this model and user feedback to suggest parameter changes.

## Current Model
"""
    prompt += f"Name: {model.name}\n"
    prompt += f"Description: {model.description}\n\n"

    prompt += "### Stocks\n"
    for stock in model.stocks:
        prompt += f"- {stock.name}: initial_value={stock.initial_value}\n"

    prompt += "\n### Flows\n"
    for flow in model.flows:
        prompt += f"- {flow.name}: equation=\"{flow.equation}\"\n"

    prompt += "\n### Variables (Parameters)\n"
    for var in model.variables:
        prompt += f"- {var.name}: equation=\"{var.equation}\"\n"

    prompt += "\n## Current Simulation Results\n"
    time = simulation_results.get("time", [])
    if time:
        prompt += f"Time range: {time[0]} to {time[-1]}\n"

    for name, values in simulation_results.get("values", {}).items():
        if values:
            arr = np.array(values)
            prompt += f"- {name}: min={arr.min():.2f}, max={arr.max():.2f}, final={arr[-1]:.2f}\n"

    prompt += f"""
## User Feedback
"{feedback}"

## Your Task
Suggest specific parameter changes to address the user's feedback. Respond in JSON format:

{{
    "suggestions": [
        {{
            "parameter": "parameter_name",
            "current_value": 0.5,
            "suggested_value": 0.8,
            "reasoning": "Explain why this change will help"
        }}
    ],
    "explanation": "Overall explanation of how these changes address the feedback",
    "expected_outcome": "What the user should expect after these changes"
}}

Only suggest changes to existing parameters (stock initial values or variable equations that are simple numbers).
Respond with ONLY valid JSON."""

    try:
        gen_model = client.GenerativeModel("gemini-2.0-flash")
        response = gen_model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "max_output_tokens": 1024,
            }
        )

        response_text = response.text
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()

        data = json.loads(response_text)
        suggestions = data.get("suggestions", [])

        # Create modified model if suggestions exist
        modified_model = None
        if suggestions:
            model_dict = model.model_dump()
            for suggestion in suggestions:
                param = suggestion.get("parameter")
                new_value = suggestion.get("suggested_value")

                if param and new_value is not None:
                    # Check stocks
                    for stock in model_dict["stocks"]:
                        if stock["name"] == param or f"{stock['name']}_initial" == param:
                            stock["initial_value"] = float(new_value)

                    # Check variables
                    for var in model_dict["variables"]:
                        if var["name"] == param:
                            var["equation"] = str(new_value)

            modified_model = model_dict

        return RefinementResult(
            success=True,
            suggestions=suggestions,
            modified_model=modified_model,
            explanation=data.get("explanation", "") + "\n\n" + data.get("expected_outcome", "")
        )

    except Exception as e:
        return RefinementResult(
            success=False,
            suggestions=[],
            modified_model=None,
            explanation=f"AI refinement failed: {str(e)}"
        )
