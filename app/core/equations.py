"""
Safe equation parser and evaluator.
Uses AST parsing to safely evaluate mathematical expressions.

Supports XMILE/PySD-compatible functions including:
- TIME: current simulation time
- STEP, PULSE, RAMP: time-based input functions
- IF_THEN_ELSE: conditional function
- RANDOM_UNIFORM, RANDOM_NORMAL: random number generators
- DELAY, SMOOTH: stateful functions (handled by simulator)
- LOOKUP, WITH_LOOKUP: table functions
"""
import ast
import operator
import math
import random
from typing import Callable, Any, Optional
import re


SAFE_OPERATORS: dict[type, Callable] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}


# Time-based input functions
def step_function(height: float, step_time: float, time: float) -> float:
    """Step function: returns height after step_time, 0 before."""
    return height if time >= step_time else 0.0


def pulse_function(magnitude: float, start_time: float, repeat_interval: float, time: float, dt: float) -> float:
    """
    Pulse function: returns magnitude/dt for one dt at start_time and optionally repeats.
    If repeat_interval is 0, pulse occurs only once.
    """
    if time < start_time:
        return 0.0

    # Time since first pulse
    elapsed = time - start_time

    if repeat_interval <= 0:
        # Single pulse at start_time
        if 0 <= elapsed < dt:
            return magnitude / dt
        return 0.0
    else:
        # Repeating pulse
        time_in_period = elapsed % repeat_interval
        if time_in_period < dt:
            return magnitude / dt
        return 0.0


def ramp_function(slope: float, start_time: float, end_time: float, time: float) -> float:
    """
    Ramp function: increases linearly from start_time at rate 'slope'.
    If end_time > start_time, ramp stops at end_time.
    If end_time <= start_time, ramp continues indefinitely.
    """
    if time < start_time:
        return 0.0

    if end_time > start_time and time > end_time:
        # Ramp has ended - return final value
        return slope * (end_time - start_time)

    return slope * (time - start_time)


def if_then_else(condition: float, true_value: float, false_value: float) -> float:
    """IF_THEN_ELSE function: returns true_value if condition is non-zero, else false_value."""
    return true_value if condition else false_value


def random_uniform(min_val: float, max_val: float) -> float:
    """Random uniform distribution between min and max."""
    return random.uniform(min_val, max_val)


def random_normal(mean: float, std_dev: float) -> float:
    """Random normal (Gaussian) distribution with given mean and standard deviation."""
    return random.gauss(mean, std_dev)


def lookup_interp(x: float, points: list[tuple[float, float]]) -> float:
    """
    Linear interpolation lookup.
    Points should be sorted by x value.
    Extrapolates at boundaries.
    """
    if not points:
        return 0.0

    if len(points) == 1:
        return points[0][1]

    # Sort by x value
    sorted_points = sorted(points, key=lambda p: p[0])

    # Handle boundary cases
    if x <= sorted_points[0][0]:
        # Extrapolate below first point
        x1, y1 = sorted_points[0]
        x2, y2 = sorted_points[1]
        if x2 == x1:
            return y1
        slope = (y2 - y1) / (x2 - x1)
        return y1 + slope * (x - x1)

    if x >= sorted_points[-1][0]:
        # Extrapolate above last point
        x1, y1 = sorted_points[-2]
        x2, y2 = sorted_points[-1]
        if x2 == x1:
            return y2
        slope = (y2 - y1) / (x2 - x1)
        return y2 + slope * (x - x2)

    # Find surrounding points and interpolate
    for i in range(len(sorted_points) - 1):
        x1, y1 = sorted_points[i]
        x2, y2 = sorted_points[i + 1]
        if x1 <= x <= x2:
            if x2 == x1:
                return y1
            t = (x - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)

    return sorted_points[-1][1]


SAFE_FUNCTIONS: dict[str, Callable] = {
    # Basic math functions
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "exp": math.exp,
    "log": math.log,
    "ln": math.log,  # Alias for natural log
    "log10": math.log10,
    "sqrt": math.sqrt,
    "abs": abs,
    "min": min,
    "max": max,
    "pow": pow,
    "floor": math.floor,
    "ceil": math.ceil,
    "round": round,
    # Conditional function
    "IF_THEN_ELSE": if_then_else,
    "IF": if_then_else,  # Alias for IF_THEN_ELSE
    # Random functions
    "RANDOM_UNIFORM": random_uniform,
    "RANDOM_NORMAL": random_normal,
}

# Functions that require simulation context (time, dt)
# These are handled specially by the evaluator
CONTEXT_FUNCTIONS = {"STEP", "PULSE", "RAMP", "DELAY1", "DELAY3", "DELAY_N",
                     "DELAY_FIXED", "SMOOTH", "SMOOTH3", "SMOOTH_N", "LOOKUP", "WITH_LOOKUP"}

SAFE_CONSTANTS: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
}


class EquationError(Exception):
    """Error in equation parsing or evaluation."""
    pass


class SimulationContext:
    """
    Context for simulation that provides access to time, dt, lookup tables,
    and stateful function managers (DELAY, SMOOTH).
    """
    def __init__(self, time: float = 0.0, dt: float = 0.25,
                 tables: Optional[dict[str, list[tuple[float, float]]]] = None,
                 delay_state: Optional[dict] = None,
                 smooth_state: Optional[dict] = None):
        self.time = time
        self.dt = dt
        self.tables = tables if tables is not None else {}
        self.delay_state = delay_state if delay_state is not None else {}
        self.smooth_state = smooth_state if smooth_state is not None else {}


class SafeEvaluator(ast.NodeVisitor):
    """
    Safely evaluate mathematical expressions using AST.
    No exec/eval of raw strings - only parsed AST nodes.
    """

    def __init__(self, variables: dict[str, float], context: Optional[SimulationContext] = None):
        self.variables = variables
        self.context = context or SimulationContext()

    def visit_Expression(self, node: ast.Expression) -> float:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> float:
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise EquationError(f"Invalid constant type: {type(node.value)}")

    # Note: visit_Num is not needed for Python 3.8+
    # ast.Constant handles all numeric literals

    def visit_Name(self, node: ast.Name) -> float:
        name = node.id
        # Check for TIME variable (case insensitive)
        if name.upper() == "TIME":
            return self.context.time
        # Check constants first
        if name in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[name]
        # Then check user variables - try multiple name variations
        # to handle underscore vs space naming inconsistencies
        name_variations = [
            name,
            name.replace("_", " "),  # Growth_Rate -> Growth Rate
            name.replace(" ", "_"),  # Growth Rate -> Growth_Rate
        ]
        for var_name in name_variations:
            if var_name in self.variables:
                return self.variables[var_name]
        raise EquationError(f"Unknown variable: {name}")

    def visit_BinOp(self, node: ast.BinOp) -> float:
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise EquationError(f"Unsupported operator: {op_type.__name__}")
        left = self.visit(node.left)
        right = self.visit(node.right)
        try:
            return SAFE_OPERATORS[op_type](left, right)
        except ZeroDivisionError:
            return float("inf")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise EquationError(f"Unsupported unary operator: {op_type.__name__}")
        operand = self.visit(node.operand)
        return SAFE_OPERATORS[op_type](operand)

    def visit_Call(self, node: ast.Call) -> float:
        if not isinstance(node.func, ast.Name):
            raise EquationError("Only simple function calls are allowed")
        func_name = node.func.id
        func_name_upper = func_name.upper()

        # Handle context functions that need simulation state
        if func_name_upper in CONTEXT_FUNCTIONS:
            return self._handle_context_function(func_name_upper, node.args)

        # Handle regular safe functions (case-insensitive for common ones)
        actual_func_name = func_name
        if func_name not in SAFE_FUNCTIONS:
            # Try uppercase version
            if func_name_upper in SAFE_FUNCTIONS:
                actual_func_name = func_name_upper
            # Try lowercase version
            elif func_name.lower() in SAFE_FUNCTIONS:
                actual_func_name = func_name.lower()
            else:
                raise EquationError(f"Unknown function: {func_name}")

        args = [self.visit(arg) for arg in node.args]
        try:
            return SAFE_FUNCTIONS[actual_func_name](*args)
        except (ValueError, TypeError) as e:
            raise EquationError(f"Function error in {func_name}: {e}")

    def _handle_context_function(self, func_name: str, args: list) -> float:
        """Handle functions that require simulation context."""
        # Note: Some functions like LOOKUP have special first argument handling
        # Don't pre-evaluate all args for those functions

        # Generate a call_key from the first argument's AST for stateful functions
        # This provides a stable identifier across repeated evaluations
        call_key = ast.dump(args[0]) if args else ""

        if func_name == "LOOKUP":
            # LOOKUP(table_name, input) - table_name must be a string literal or name
            if len(args) < 2:
                raise EquationError("LOOKUP requires 2 arguments: table_name, input")
            # First arg should be a Name node for the table name
            if isinstance(args[0], ast.Name):
                table_name = args[0].id
            elif isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
                table_name = args[0].value
            else:
                raise EquationError("LOOKUP first argument must be a table name")
            input_val = self.visit(args[1])
            if table_name not in self.context.tables:
                raise EquationError(f"Unknown lookup table: {table_name}")
            return lookup_interp(input_val, self.context.tables[table_name])

        if func_name == "WITH_LOOKUP":
            # WITH_LOOKUP(input, ((x1,y1),(x2,y2),...))
            if len(args) < 2:
                raise EquationError("WITH_LOOKUP requires input value and lookup points")
            input_val = self.visit(args[0])
            points = self._parse_lookup_points(args[1])
            if not points:
                raise EquationError("WITH_LOOKUP: could not parse lookup points")
            return lookup_interp(input_val, points)

        # For other functions, evaluate all args
        evaluated_args = [self.visit(arg) for arg in args]

        if func_name == "STEP":
            # STEP(height, step_time)
            if len(evaluated_args) < 2:
                raise EquationError("STEP requires 2 arguments: height, step_time")
            height, step_time = evaluated_args[0], evaluated_args[1]
            return step_function(height, step_time, self.context.time)

        elif func_name == "PULSE":
            # PULSE(magnitude, start_time, repeat_interval=0)
            if len(evaluated_args) < 2:
                raise EquationError("PULSE requires at least 2 arguments: magnitude, start_time")
            magnitude = evaluated_args[0]
            start_time = evaluated_args[1]
            repeat_interval = evaluated_args[2] if len(evaluated_args) > 2 else 0.0
            return pulse_function(magnitude, start_time, repeat_interval, self.context.time, self.context.dt)

        elif func_name == "RAMP":
            # RAMP(slope, start_time, end_time=0)
            if len(evaluated_args) < 2:
                raise EquationError("RAMP requires at least 2 arguments: slope, start_time")
            slope = evaluated_args[0]
            start_time = evaluated_args[1]
            end_time = evaluated_args[2] if len(evaluated_args) > 2 else 0.0
            return ramp_function(slope, start_time, end_time, self.context.time)

        elif func_name == "DELAY1":
            # DELAY1(input, delay_time, initial=input)
            return self._handle_delay(1, evaluated_args, call_key)

        elif func_name == "DELAY3":
            # DELAY3(input, delay_time, initial=input)
            return self._handle_delay(3, evaluated_args, call_key)

        elif func_name == "DELAY_N":
            # DELAY_N(input, delay_time, order, initial=input)
            if len(evaluated_args) < 3:
                raise EquationError("DELAY_N requires 3 arguments: input, delay_time, order")
            order = int(evaluated_args[2])
            return self._handle_delay(order, [evaluated_args[0], evaluated_args[1]] +
                                     (evaluated_args[3:] if len(evaluated_args) > 3 else []), call_key)

        elif func_name == "DELAY_FIXED":
            # DELAY_FIXED(input, delay_time, initial)
            return self._handle_delay_fixed(evaluated_args, call_key)

        elif func_name == "SMOOTH":
            # SMOOTH(input, smoothing_time, initial=input)
            return self._handle_smooth(1, evaluated_args, call_key)

        elif func_name == "SMOOTH3":
            # SMOOTH3(input, smoothing_time, initial=input)
            return self._handle_smooth(3, evaluated_args, call_key)

        elif func_name == "SMOOTH_N":
            # SMOOTH_N(input, smoothing_time, order, initial=input)
            if len(evaluated_args) < 3:
                raise EquationError("SMOOTH_N requires 3 arguments: input, smoothing_time, order")
            order = int(evaluated_args[2])
            return self._handle_smooth(order, [evaluated_args[0], evaluated_args[1]] +
                                      (evaluated_args[3:] if len(evaluated_args) > 3 else []), call_key)

        raise EquationError(f"Unhandled context function: {func_name}")

    def _parse_lookup_points(self, node: ast.AST) -> list[tuple[float, float]]:
        """Parse inline lookup points from AST."""
        points = []
        if isinstance(node, ast.Tuple) or isinstance(node, ast.List):
            for elem in node.elts:
                if isinstance(elem, ast.Tuple) and len(elem.elts) == 2:
                    x = self.visit(elem.elts[0])
                    y = self.visit(elem.elts[1])
                    points.append((x, y))
        return points

    def _handle_delay(self, order: int, args: list, call_key: str = "") -> float:
        """Handle DELAY1, DELAY3, DELAY_N functions using exponential delay."""
        if len(args) < 2:
            raise EquationError(f"DELAY{order} requires at least 2 arguments: input, delay_time")

        input_val = args[0]
        delay_time = args[1]
        initial = args[2] if len(args) > 2 else input_val

        if delay_time <= 0:
            return input_val

        # Unique key for this delay instance based on stable parameters
        # Uses order and delay_time (which are constant per equation) plus call_key
        key = f"delay_{order}_{delay_time}_{call_key}"

        if key not in self.context.delay_state:
            # Initialize delay state as a chain of order states
            self.context.delay_state[key] = [initial] * order

        state = self.context.delay_state[key]
        dt = self.context.dt

        # Time constant for each stage
        tau = delay_time / order

        # Update each stage using exponential smoothing
        for i in range(order):
            inp = input_val if i == 0 else state[i - 1]
            rate = (inp - state[i]) / tau
            state[i] = state[i] + rate * dt

        return state[-1]

    def _handle_delay_fixed(self, args: list, call_key: str = "") -> float:
        """Handle DELAY_FIXED using a circular buffer (pipeline delay)."""
        if len(args) < 3:
            raise EquationError("DELAY_FIXED requires 3 arguments: input, delay_time, initial")

        input_val = args[0]
        delay_time = args[1]
        initial = args[2]

        if delay_time <= 0:
            return input_val

        dt = self.context.dt
        buffer_size = max(1, int(delay_time / dt))

        # Unique key based on stable parameters
        key = f"delay_fixed_{delay_time}_{call_key}"

        if key not in self.context.delay_state:
            # Initialize buffer with initial values
            self.context.delay_state[key] = {
                "buffer": [initial] * buffer_size,
                "index": 0
            }

        state = self.context.delay_state[key]
        buffer = state["buffer"]
        index = state["index"]

        # Get delayed value
        output = buffer[index]

        # Store current input
        buffer[index] = input_val

        # Advance index
        state["index"] = (index + 1) % buffer_size

        return output

    def _handle_smooth(self, order: int, args: list, call_key: str = "") -> float:
        """Handle SMOOTH, SMOOTH3, SMOOTH_N functions using exponential smoothing."""
        if len(args) < 2:
            raise EquationError(f"SMOOTH{order} requires at least 2 arguments: input, smoothing_time")

        input_val = args[0]
        smooth_time = args[1]
        initial = args[2] if len(args) > 2 else input_val

        if smooth_time <= 0:
            return input_val

        # Unique key based on stable parameters
        key = f"smooth_{order}_{smooth_time}_{call_key}"

        if key not in self.context.smooth_state:
            # Initialize smooth state as a chain of order states
            self.context.smooth_state[key] = [initial] * order

        state = self.context.smooth_state[key]
        dt = self.context.dt

        # Time constant for each stage
        tau = smooth_time / order

        # Update each stage
        for i in range(order):
            inp = input_val if i == 0 else state[i - 1]
            rate = (inp - state[i]) / tau
            state[i] = state[i] + rate * dt

        return state[-1]

    def visit_Compare(self, node: ast.Compare) -> float:
        # Support comparisons returning 0 or 1
        left = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            if isinstance(op, ast.Lt):
                result = left < right
            elif isinstance(op, ast.LtE):
                result = left <= right
            elif isinstance(op, ast.Gt):
                result = left > right
            elif isinstance(op, ast.GtE):
                result = left >= right
            elif isinstance(op, ast.Eq):
                result = left == right
            elif isinstance(op, ast.NotEq):
                result = left != right
            else:
                raise EquationError(f"Unsupported comparison: {type(op).__name__}")
            if not result:
                return 0.0
            left = right
        return 1.0

    def visit_IfExp(self, node: ast.IfExp) -> float:
        # Support ternary expressions: x if condition else y
        condition = self.visit(node.test)
        if condition:
            return self.visit(node.body)
        return self.visit(node.orelse)

    def generic_visit(self, node):
        raise EquationError(f"Unsupported expression type: {type(node).__name__}")




def preprocess_equation(equation: str) -> str:
    """
    Preprocess equation to convert XMILE-style syntax to Python-parseable format.
    
    Converts:
    - IF condition THEN true_expr ELSE false_expr -> IF_THEN_ELSE(condition, true_expr, false_expr)
    - Single = in comparisons -> == (except <= >= == !=)
    """
    if not equation:
        return equation
    
    result = equation.strip()
    
    # Convert XMILE IF-THEN-ELSE to IF_THEN_ELSE function calls
    # Process repeatedly to handle nested structures
    max_iterations = 20
    
    for _ in range(max_iterations):
        upper_result = result.upper()
        
        # Find last ELSE that is not followed by " IF " (with space after IF)
        # This distinguishes "ELSE IF condition" from "ELSE IF_THEN_ELSE(" or "ELSE something_else"
        else_positions = []
        idx = 0
        while True:
            pos = upper_result.find(" ELSE ", idx)
            if pos == -1:
                break
            # Check if this is "ELSE IF " (chained conditional)
            remainder = upper_result[pos+6:].lstrip()
            # Only skip if it is "IF " followed by non-underscore (i.e., not IF_THEN_ELSE)
            if remainder.startswith("IF ") or (remainder.startswith("IF") and len(remainder) > 2 and remainder[2] not in "_"):
                pass  # This is ELSE IF, skip it for now
            else:
                else_positions.append(pos)
            idx = pos + 1
        
        if not else_positions:
            break
        
        last_else_pos = else_positions[-1]
        before_else = result[:last_else_pos]
        after_else = result[last_else_pos+6:]  # Skip " ELSE "
        
        upper_before = before_else.upper()
        then_pos = upper_before.rfind(" THEN ")
        if then_pos == -1:
            break
        
        before_then = before_else[:then_pos]
        between_then_else = before_else[then_pos+6:]
        upper_before_then = before_then.upper()
        
        # Find the IF that matches this THEN
        if_pos = upper_before_then.rfind(" IF ")
        if if_pos == -1:
            if upper_before_then.strip().upper().startswith("IF "):
                if_pos = upper_before_then.upper().find("IF ")
            else:
                break
        else:
            if_pos += 1  # Account for space
        
        prefix = before_then[:if_pos]
        condition = before_then[if_pos+3:].strip()
        true_val = between_then_else.strip()
        false_val = after_else.strip()
        
        replacement = f"IF_THEN_ELSE({condition}, {true_val}, {false_val})"
        result = prefix + replacement
    
    # Convert single = to == for comparisons (not <= >= == !=)
    result = re.sub(r"(?<![<>=!])=(?!=)", "==", result)
    
    return result


def safe_eval(equation: str, variables: dict[str, float],
              context: Optional[SimulationContext] = None) -> float:
    """
    Safely evaluate a mathematical equation with given variables.

    Args:
        equation: Mathematical expression (e.g., "population * birth_rate")
        variables: Dictionary of variable names to values
        context: Optional simulation context providing time, dt, tables, and state

    Returns:
        The computed result as a float

    Raises:
        EquationError: If the equation is invalid or uses unsafe operations
    """
    if not equation or equation.strip() == "":
        return 0.0

    # Normalize and preprocess the equation
    equation = preprocess_equation(equation)
    
    # Continue with normalization
    equation = equation.strip()

    # Handle simple numeric values
    try:
        return float(equation)
    except ValueError:
        pass

    try:
        # Parse the expression
        tree = ast.parse(equation, mode="eval")
        # Evaluate safely
        evaluator = SafeEvaluator(variables, context)
        return evaluator.visit(tree)
    except SyntaxError as e:
        raise EquationError(f"Syntax error in equation: {e}")
    except Exception as e:
        raise EquationError(f"Error evaluating equation '{equation}': {e}")


def validate_equation(equation: str, available_variables: list[str],
                     table_names: Optional[list[str]] = None) -> tuple[bool, str]:
    """
    Validate that an equation is syntactically correct and uses only known variables.

    Args:
        equation: The equation to validate
        available_variables: List of variable names that can be referenced
        table_names: Optional list of lookup table names

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not equation or equation.strip() == "":
        return True, ""

    try:
        # Parse the expression
        tree = ast.parse(equation.strip(), mode="eval")

        # Extract all variable references (excluding function call names and table names)
        referenced_vars = set()
        function_calls = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                function_calls.add(node.func.id)
                # For LOOKUP, first arg is table name - don't count as variable
                if node.func.id.upper() == "LOOKUP" and node.args:
                    if isinstance(node.args[0], ast.Name):
                        continue  # Skip the table name from variable check
            if isinstance(node, ast.Name):
                referenced_vars.add(node.id)

        # Remove function names from referenced_vars
        referenced_vars -= function_calls

        # Build known variables set
        known_vars = set(available_variables) | set(SAFE_CONSTANTS.keys())
        known_vars.add("TIME")  # TIME is always available
        known_vars.add("time")

        # Add table names if provided
        if table_names:
            known_vars.update(table_names)

        # Add known function names (case insensitive)
        all_functions = set(SAFE_FUNCTIONS.keys()) | CONTEXT_FUNCTIONS
        all_functions.update(f.lower() for f in all_functions)
        known_vars.update(all_functions)

        unknown = referenced_vars - known_vars
        if unknown:
            return False, f"Unknown variables: {', '.join(sorted(unknown))}"

        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error: {e}"


def get_equation_variables(equation: str) -> set[str]:
    """
    Extract all variable names referenced in an equation.

    Args:
        equation: The equation to analyze

    Returns:
        Set of variable names (excluding functions, constants, TIME, and table names)
    """
    if not equation or equation.strip() == "":
        return set()

    try:
        tree = ast.parse(equation.strip(), mode="eval")
        variables = set()
        function_names = set()
        table_refs = set()

        # First pass: find function calls and table references
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                function_names.add(node.func.id)
                # For LOOKUP, first arg is table name
                if node.func.id.upper() == "LOOKUP" and node.args:
                    if isinstance(node.args[0], ast.Name):
                        table_refs.add(node.args[0].id)

        # Second pass: collect variable references
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                name = node.id
                # Exclude functions, constants, TIME, and context functions
                if (name not in SAFE_FUNCTIONS and
                    name not in SAFE_CONSTANTS and
                    name.upper() not in CONTEXT_FUNCTIONS and
                    name not in function_names and
                    name not in table_refs and
                    name.upper() != "TIME"):
                    variables.add(name)
        return variables
    except SyntaxError:
        return set()
