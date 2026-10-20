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
from functools import lru_cache


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
    if repeat_interval < 0:
        raise EquationError("PULSE interval must be nonnegative")
    elapsed = time - start_time
    # A distant repeat interval has no arithmetic role in the first pulse.
    # Its ULP must not widen the local event window (e.g. interval=1e20).
    tolerance = min(dt / 4, 4 * max(math.ulp(time), math.ulp(start_time),
                                   math.ulp(dt), math.ulp(elapsed)))
    if elapsed < -tolerance:
        return 0.0
    elapsed = max(0.0, elapsed)
    phase = elapsed if repeat_interval == 0 else elapsed % repeat_interval
    if repeat_interval > 0 and repeat_interval - phase <= tolerance:
        phase = 0.0
    # Decimal grids can represent an event at just below its exact boundary,
    # or the exclusive end at just below DT. Snap only within roundoff scale.
    return magnitude / dt if phase < dt and dt - phase > tolerance else 0.0


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


def lookup_interp(x: float, points: list[tuple[float, float]], interpolation: str = "extrapolate") -> float:
    """
    Linear interpolation lookup.
    Points should be sorted by x value.
    Extrapolates at boundaries.
    """
    if not points:
        raise EquationError("Lookup table must contain at least one point")
    if not math.isfinite(x):
        raise EquationError("Lookup input must be finite")
    if any(not math.isfinite(coordinate) for point in points for coordinate in point):
        raise EquationError("Lookup table points must be finite")
    if len({point[0] for point in points}) != len(points):
        raise EquationError("Lookup table x coordinates must be unique")

    if interpolation not in ("continuous", "extrapolate", "discrete"):
        raise EquationError(f"Unknown lookup interpolation: {interpolation}")
    if len(points) == 1:
        return points[0][1]

    # Sort by x value
    sorted_points = sorted(points, key=lambda p: p[0])
    if interpolation in ("continuous", "discrete"):
        if x <= sorted_points[0][0]:
            return sorted_points[0][1]
        if x >= sorted_points[-1][0]:
            return sorted_points[-1][1]
    if interpolation == "discrete":
        return next(y for at, y in reversed(sorted_points) if at <= x)

    def segment(x1, y1, x2, y2):
        if x == x1 or y1 == y2:
            return y1
        if x == x2:
            return y2
        try:
            width, distance = x2 - x1, x - x1
            if math.isfinite(width) and math.isfinite(distance):
                weight = distance / width
            else:
                # Finite coordinates may have a difference outside float range.
                scale = max(abs(x), abs(x1), abs(x2))
                weight = (x / scale - x1 / scale) / (x2 / scale - x1 / scale)
            difference = y2 - y1
            value = ((1 - weight) * y1 + weight * y2
                     if 0 <= weight <= 1 or not math.isfinite(difference)
                     else y1 + weight * difference)
        except (OverflowError, ZeroDivisionError):
            value = math.inf
        if not math.isfinite(value):
            # Extrapolation can overflow intermediates while its exact affine
            # value is finite. Fractions preserve the exact finite input floats;
            # this rare bounded fallback also handles subnormal X spacing.
            from fractions import Fraction
            exact = (Fraction(y1) + (Fraction(x) - Fraction(x1)) *
                     (Fraction(y2) - Fraction(y1)) / (Fraction(x2) - Fraction(x1)))
            try:
                value = float(exact)
            except OverflowError:
                raise EquationError("Lookup result is not finite; check extrapolation range") from None
            if not math.isfinite(value):
                raise EquationError("Lookup result is not finite; check extrapolation range")
        return value

    if x <= sorted_points[0][0]:
        return segment(*sorted_points[0], *sorted_points[1])
    if x >= sorted_points[-1][0]:
        return segment(*sorted_points[-2], *sorted_points[-1])
    for (x1, y1), (x2, y2) in zip(sorted_points, sorted_points[1:]):
        if x1 <= x <= x2:
            return segment(x1, y1, x2, y2)
    raise EquationError("Lookup interval could not be located")


SAFE_FUNCTIONS: dict[str, Callable] = {
    # Basic math functions
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "sign": lambda value: float((value > 0) - (value < 0)),
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
    "mod": operator.mod,
    # Conditional function
    "IF_THEN_ELSE": if_then_else,
    "IF": if_then_else,  # Alias for IF_THEN_ELSE
    # Random functions
    "RANDOM_UNIFORM": random_uniform,
    "RANDOM_NORMAL": random_normal,
}

# Functions that require simulation context (time, dt)
# These are handled specially by the evaluator
STOCHASTIC_FUNCTIONS = {"RANDOM", "RANDOM_UNIFORM", "RANDOM_NORMAL", "NORMAL"}

STATEFUL_ALIASES = {"SMTH1": "SMOOTH", "SMTH3": "SMOOTH3", "SMTHN": "SMOOTH_N",
                    "DELAYN": "DELAY_N", "DELAY": "DELAY_FIXED"}
STATEFUL_FUNCTIONS = {"DELAY1", "DELAY3", "DELAY_N", "DELAY_FIXED",
                      "SMOOTH", "SMOOTH3", "SMOOTH_N"} | set(STATEFUL_ALIASES)
CONTEXT_FUNCTIONS = {"STEP", "PULSE", "RAMP", "LOOKUP", "WITH_LOOKUP"} | STATEFUL_FUNCTIONS | STOCHASTIC_FUNCTIONS

SAFE_CONSTANTS: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
}


class EquationError(Exception):
    """Error in equation parsing or evaluation."""
    pass


def validate_random_seed(value):
    """XMILE seeds are integer-valued numbers in [0, 2**32)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EquationError("Random seed must be an integer between 0 and 2**32-1")
    if not 0 <= value < 2**32 or not math.isfinite(value) or value != int(value):
        raise EquationError("Random seed must be an integer between 0 and 2**32-1")
    return int(value)


class RandomRuntime:
    """Isolated per-run, per-call RNG streams with one unit draw per output time.

    Explicit function seeds initialize independent streams directly. Otherwise a
    stable hash of the run seed and call identity gives order-independent streams.
    Only the current logical timestep's draw is retained for each call, so retries
    and hidden-state evaluation reuse noise without growing history with time.
    """
    def __init__(self, seed=None):
        self.seed = random.SystemRandom().randrange(2**32) if seed is None else validate_random_seed(seed)
        self.epoch = 0
        self.streams = {}

    def unit_sample(self, key, kind, explicit_seed=None, at_time=None):
        import hashlib
        seed = validate_random_seed(explicit_seed) if explicit_seed is not None else None
        if key not in self.streams:
            if seed is None:
                identity = (str(self.seed) + ":" + key).encode("utf-8")
                stream_seed = int.from_bytes(hashlib.sha256(identity).digest(), "big")
            else:
                stream_seed = seed
            self.streams[key] = {"seed": seed, "generator": random.Random(stream_seed),
                                 "epoch": None, "sample": None}
        stream = self.streams[key]
        if seed != stream["seed"]:
            raise EquationError("Changing a random function's seed during a run is unsupported")
        epoch = (self.epoch, at_time)
        if stream["epoch"] != epoch:
            generator = stream["generator"]
            stream["sample"] = generator.random() if kind == "uniform" else generator.gauss(0, 1)
            stream["epoch"] = epoch
        return stream["sample"]


class SimulationContext:
    """
    Context for simulation that provides access to time, dt, lookup tables,
    and stateful function managers (DELAY, SMOOTH).
    """
    def __init__(self, time: float = 0.0, dt: float = 0.25,
                 tables: Optional[dict[str, list[tuple[float, float]]]] = None,
                 delay_state: Optional[dict] = None,
                 smooth_state: Optional[dict] = None, random_runtime=None):
        self.time = time
        # RK4 holds declared test-input primitives at the accepted left time.
        # Ordinary TIME and algebra still use the current RK stage time.
        self.input_time = time
        self.input_snapshot = None
        self.dt = dt
        self.tables = tables if tables is not None else {}
        self.delay_state = delay_state if delay_state is not None else {}
        self.smooth_state = smooth_state if smooth_state is not None else {}
        self.table_types = {}
        self.equation_key = ""
        self.random_runtime = random_runtime if random_runtime is not None else RandomRuntime()


ENCODED_IDENTIFIER_PREFIX = "__xmile_id_"


def _encode_identifier(value):
    return ENCODED_IDENTIFIER_PREFIX + value.encode("utf-8").hex()


def decode_identifier(value):
    """Decode only lexer-generated AST identifiers, without evaluating any code."""
    if value.startswith(ENCODED_IDENTIFIER_PREFIX):
        try:
            return bytes.fromhex(value[len(ENCODED_IDENTIFIER_PREFIX):]).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise EquationError("Malformed encoded identifier") from exc
    return value


def restore_identifiers(expression):
    """Restore quoted XMILE names after AST unparse in an XML exporter."""
    import io
    import json
    import tokenize
    output = []
    for token in tokenize.generate_tokens(io.StringIO(expression).readline):
        value = token.string
        if token.type == tokenize.NAME and value.startswith(ENCODED_IDENTIFIER_PREFIX):
            value = json.dumps(decode_identifier(value), ensure_ascii=False)
        if token.type == tokenize.OP and value in ("~", "%"):
            output.append((tokenize.NAME, "NOT" if value == "~" else "MOD"))
        else:
            output.append((token.type, value))
    return tokenize.untokenize(output).strip()


def canonical_name(value):
    """Unicode-preserving aliases, with XMILE whitespace equivalence.

    Retain historical punctuation aliases, but reject collisions at model entry.
    NFC preserves composed/decomposed Unicode identity without collapsing fullwidth
    characters into distinct ASCII characters as Python AST identifiers would.
    """
    import unicodedata
    normalized = unicodedata.normalize("NFC", value).casefold()
    normalized = re.sub(r"[ _\n\u00a0]+", "_", normalized)
    normalized = "".join(character if character.isalnum() or character == "_" else "_"
                         for character in normalized)
    return re.sub(r"_+", "_", normalized)


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
        name = decode_identifier(node.id)
        # Check for TIME variable (case insensitive)
        if name.upper() == "TIME":
            return self.context.time
        if name.upper() in ("DT", "TIME_STEP"):
            return self.context.dt
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
        matched = [value for key, value in self.variables.items() if canonical_name(key) == canonical_name(name)]
        if len(matched) == 1:
            return matched[0]
        if len(matched) > 1:
            raise EquationError(f"Ambiguous variable alias: {name}")
        if name.lower() in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[name.lower()]
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
            raise EquationError("Division by zero")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        op_type = type(node.op)
        if op_type in (ast.Not, ast.Invert):
            return float(not self.visit(node.operand))
        if op_type not in SAFE_OPERATORS:
            raise EquationError(f"Unsupported unary operator: {op_type.__name__}")
        operand = self.visit(node.operand)
        return SAFE_OPERATORS[op_type](operand)

    def visit_Call(self, node: ast.Call) -> float:
        if not isinstance(node.func, ast.Name):
            raise EquationError("Only simple function calls are allowed")
        if node.keywords:
            raise EquationError("Keyword arguments are unsupported")
        func_name = decode_identifier(node.func.id)
        func_name_upper = func_name.upper()

        # XMILE permits table_name(input) as well as LOOKUP(table_name, input).
        table_name = self._table_name(func_name)
        if table_name is not None:
            if len(node.args) != 1:
                raise EquationError("A graphical function requires one input")
            return lookup_interp(self.visit(node.args[0]), self.context.tables[table_name],
                                 self.context.table_types.get(table_name, "extrapolate"))

        if func_name_upper in STOCHASTIC_FUNCTIONS:
            return self._random_value(func_name_upper, node)

        # Conditionals must evaluate only the selected branch.
        if func_name_upper in ("IF", "IF_THEN_ELSE"):
            if len(node.args) != 3:
                raise EquationError("IF_THEN_ELSE requires three arguments")
            return self.visit(node.args[1] if self.visit(node.args[0]) else node.args[2])

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

    def _random_value(self, function, node):
        if not 2 <= len(node.args) <= 3:
            raise EquationError(f"{function} requires 2 or 3 arguments; zero-argument RANDOM is unsupported")
        parameters = [float(self.visit(argument)) for argument in node.args[:2]]
        if not all(math.isfinite(parameter) for parameter in parameters):
            raise EquationError("Random distribution parameters must be finite")
        seed = None
        if len(node.args) == 3:
            if isinstance(node.args[2], ast.Constant) and isinstance(node.args[2].value, bool):
                raise EquationError("Random seed must be an integer, not a boolean")
            seed = validate_random_seed(self.visit(node.args[2]))
        kind = "normal" if function in ("RANDOM_NORMAL", "NORMAL") else "uniform"
        first, second = parameters
        if kind == "uniform" and first > second:
            raise EquationError("Uniform minimum must not exceed maximum")
        if kind == "normal" and second < 0:
            raise EquationError("Normal standard deviation must be nonnegative")
        key = f"{canonical_name(self.context.equation_key)}:{node.lineno}:{node.col_offset}:{kind}"
        unit = self.context.random_runtime.unit_sample(key, kind, seed, self.context.time)
        # The convex form avoids max-min overflowing for finite opposite endpoints.
        if kind == "uniform":
            value = first if first == second else (1 - unit) * first + unit * second
        else:
            value = first + second * unit
        if not math.isfinite(value):
            raise EquationError("Random result is not finite; check distribution parameters")
        return value

    def _table_name(self, requested):
        if requested in self.context.tables:
            return requested
        matches = [name for name in self.context.tables if canonical_name(name) == canonical_name(requested)]
        if len(matches) > 1:
            raise EquationError(f"Ambiguous lookup table alias: {requested}")
        return matches[0] if matches else None

    def _handle_context_function(self, func_name: str, args: list) -> float:
        """Handle functions that require simulation context."""
        # Note: Some functions like LOOKUP have special first argument handling
        # Don't pre-evaluate all args for those functions

        # Generate a call_key from the first argument's AST for stateful functions
        # This provides a stable identifier across repeated evaluations
        call_key = getattr(self.context, "equation_key", "") + ":" + str(
            (getattr(args[0], "col_offset", 0) if args else 0)) + ":" + (ast.dump(args[0]) if args else "")

        if func_name == "LOOKUP":
            # LOOKUP(table_name, input) - table_name must be a string literal or name
            if len(args) != 2:
                raise EquationError("LOOKUP requires 2 arguments: table_name, input")
            # First arg should be a Name node for the table name
            if isinstance(args[0], ast.Name):
                table_name = decode_identifier(args[0].id)
            elif isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
                table_name = args[0].value
            else:
                raise EquationError("LOOKUP first argument must be a table name")
            input_val = self.visit(args[1])
            requested_name = table_name
            table_name = self._table_name(requested_name)
            if table_name is None:
                raise EquationError(f"Unknown lookup table: {requested_name}")
            return lookup_interp(input_val, self.context.tables[table_name],
                                 self.context.table_types.get(table_name, "extrapolate"))

        if func_name == "WITH_LOOKUP":
            # WITH_LOOKUP(input, ((x1,y1),(x2,y2),...))
            if len(args) != 2:
                raise EquationError("WITH_LOOKUP requires input value and lookup points")
            input_val = self.visit(args[0])
            points = self._parse_lookup_points(args[1])
            if not points:
                raise EquationError("WITH_LOOKUP: could not parse lookup points")
            return lookup_interp(input_val, points)

        if func_name in STATEFUL_FUNCTIONS:
            return self._stateful_value(func_name, args, call_key)

        # Hold the complete primitive, including time/state-dependent arguments,
        # at the accepted left state during RK4. Only declared test primitives
        # use this snapshot; ordinary TIME/algebra and hidden states keep stage
        # values. The accepted context has no snapshot, avoiding recursion.
        if func_name in {"STEP", "PULSE", "RAMP"} and self.context.input_snapshot is not None:
            accepted_values, accepted_context = self.context.input_snapshot
            accepted_context.equation_key = self.context.equation_key
            return SafeEvaluator(accepted_values, accepted_context)._handle_context_function(func_name, args)

        # For other functions, evaluate all args
        evaluated_args = [self.visit(arg) for arg in args]
        if func_name in {"STEP", "PULSE", "RAMP"} and not all(
            math.isfinite(value) for value in evaluated_args
        ):
            raise EquationError(f"{func_name} parameters must be finite")

        if func_name == "STEP":
            # STEP(height, step_time)
            if len(evaluated_args) != 2:
                raise EquationError("STEP requires 2 arguments: height, step_time")
            height, step_time = evaluated_args[0], evaluated_args[1]
            return step_function(height, step_time, self.context.input_time)

        elif func_name == "PULSE":
            # PULSE(magnitude, start_time, repeat_interval=0)
            if not 2 <= len(evaluated_args) <= 3:
                raise EquationError("PULSE requires 2 or 3 arguments: magnitude, start_time, optional repeat_interval")
            magnitude = evaluated_args[0]
            start_time = evaluated_args[1]
            repeat_interval = evaluated_args[2] if len(evaluated_args) > 2 else 0.0
            return pulse_function(magnitude, start_time, repeat_interval, self.context.input_time, self.context.dt)

        elif func_name == "RAMP":
            # RAMP(slope, start_time, end_time=0)
            if not 2 <= len(evaluated_args) <= 3:
                raise EquationError("RAMP requires 2 or 3 arguments: slope, start_time, optional end_time")
            slope = evaluated_args[0]
            start_time = evaluated_args[1]
            end_time = evaluated_args[2] if len(evaluated_args) > 2 else 0.0
            return ramp_function(slope, start_time, end_time, self.context.input_time)

        raise EquationError(f"Unhandled context function: {func_name}")

    def _parse_lookup_points(self, node: ast.AST) -> list[tuple[float, float]]:
        """Parse inline lookup points from AST."""
        if not isinstance(node, (ast.Tuple, ast.List)):
            raise EquationError("Inline lookup points must be coordinate pairs")
        points = []
        for elem in node.elts:
            if not isinstance(elem, (ast.Tuple, ast.List)) or len(elem.elts) != 2:
                raise EquationError("Each inline lookup point must contain exactly two coordinates")
            points.append((self.visit(elem.elts[0]), self.visit(elem.elts[1])))
        return points

    def _stateful_value(self, function, args, call_key):
        """Return a hidden stock's present value; never integrate while evaluating."""
        function = STATEFUL_ALIASES.get(function, function)
        is_fixed = function == "DELAY_FIXED"
        is_n = function in ("DELAY_N", "SMOOTH_N")
        minimum, maximum = (3, 4) if is_n else (2, 3)
        if not minimum <= len(args) <= maximum:
            raise EquationError(f"{function} requires {minimum} or {maximum} arguments")
        order = 3 if function in ("DELAY3", "SMOOTH3") else 1
        if is_n:
            raw_order = self.visit(args[2])
            order = int(raw_order)
            if order != raw_order:
                raise EquationError("Delay/smooth order must be an integer")
        if not 1 <= order <= 100:
            raise EquationError("Delay/smooth order must be between 1 and 100")
        duration = float(self.visit(args[1]))
        if not math.isfinite(duration) or duration <= 0:
            raise EquationError("Delay/smooth time must be finite and greater than zero")
        # Fixed delays promise a fixed duration; accepting a varying duration changes
        # material conservation and requires a different, unsupported delay operator.
        states = self.context.smooth_state if function.startswith("SMOOTH") else self.context.delay_state
        key = function + ":" + call_key
        if key not in states:
            initial_index = 3 if is_n else 2
            initial = float(self.visit(args[initial_index] if len(args) > initial_index else args[0]))
            if not math.isfinite(initial):
                raise EquationError("Delay/smooth initial value must be finite")
            states[key] = {"function": function, "args": args, "equation_key": self.context.equation_key,
                           "duration": duration, "order": order, "initial": initial,
                           "stages": [initial] * order, "history": []}
        state = states[key]
        if state["order"] != order:
            raise EquationError("Changing delay/smooth order is unsupported")
        if is_fixed:
            if duration != state["duration"]:
                raise EquationError("Changing fixed delay time is unsupported")
            target = self.context.time - duration
            # Left-continuous sample-and-hold history is deterministic for delays
            # that are not exact multiples of dt; no fabricated future samples.
            from bisect import bisect_right
            history = state["history"]
            tolerance = 4 * max(math.ulp(self.context.time), math.ulp(duration), math.ulp(target))
            index = bisect_right(history, (target + tolerance, math.inf)) - 1
            return history[index][1] if index >= 0 else state["initial"]
        if function.startswith("DELAY") and duration != state["duration"]:
            raise EquationError("Changing material delay time is unsupported; use SMOOTH for information")
        return state["stages"][-1]

    def visit_Compare(self, node: ast.Compare) -> float:
        # XMILE 1.0 section 3.3.1: relational operators bind more tightly
        # than equality, and both groups associate left to right. Python's
        # comparison-chain semantics differ; explicit parentheses are already
        # separate nested nodes and are preserved by this grouping.
        comparisons = {ast.Lt: operator.lt, ast.LtE: operator.le,
                       ast.Gt: operator.gt, ast.GtE: operator.ge,
                       ast.Eq: operator.eq, ast.NotEq: operator.ne}
        values = [self.visit(node.left), *(self.visit(value) for value in node.comparators)]
        groups = [values[0]]
        equalities = []
        for op, right in zip(node.ops, values[1:]):
            function = comparisons.get(type(op))
            if function is None:
                raise EquationError(f"Unsupported comparison: {type(op).__name__}")
            if isinstance(op, (ast.Eq, ast.NotEq)):
                equalities.append(function)
                groups.append(right)
            else:
                groups[-1] = float(function(groups[-1], right))
        result = groups[0]
        for function, right in zip(equalities, groups[1:]):
            result = float(function(result, right))
        return result

    def visit_IfExp(self, node: ast.IfExp) -> float:
        # Support ternary expressions: x if condition else y
        condition = self.visit(node.test)
        if condition:
            return self.visit(node.body)
        return self.visit(node.orelse)

    def visit_BoolOp(self, node: ast.BoolOp) -> float:
        for value in node.values:
            result = bool(self.visit(value))
            if isinstance(node.op, ast.And) and not result:
                return 0.0
            if isinstance(node.op, ast.Or) and result:
                return 1.0
        return float(isinstance(node.op, ast.And))

    def generic_visit(self, node):
        raise EquationError(f"Unsupported expression type: {type(node).__name__}")




def _strip_comments(equation: str) -> str:
    """Remove XMILE brace comments without consuming quoted identifiers."""
    output = []
    quote = None
    escaped = False
    in_comment = False
    for character in equation:
        if in_comment:
            if character == "}":
                in_comment = False
            output.append("\n" if character == "\n" else " ")
        elif quote is not None:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
        elif character in ("'", '"'):
            quote = character
            output.append(character)
        elif character == "{":
            in_comment = True
            output.append(" ")
        elif character == "}":
            raise EquationError("Unexpected comment terminator }")
        else:
            output.append(character)
    if in_comment:
        raise EquationError("Unclosed XMILE brace comment")
    return "".join(output)


@lru_cache(maxsize=8192)
def preprocess_equation(equation: str) -> str:
    """Translate XMILE conditionals with nesting and argument boundaries intact."""
    if not equation or not equation.strip():
        return equation
    if len(equation) > 10000:
        raise EquationError("Equation exceeds 10,000 characters")
    import io
    import tokenize
    try:
        tokens = [token.string for token in tokenize.generate_tokens(io.StringIO(_strip_comments(equation)).readline)
                  if token.type not in (tokenize.ENDMARKER, tokenize.NEWLINE,
                                        tokenize.NL, tokenize.INDENT, tokenize.DEDENT)]
    except (tokenize.TokenError, IndentationError) as exc:
        raise EquationError(f"Syntax error in equation: {exc}") from exc
    import keyword
    for index, token in enumerate(tokens):
        if token.startswith('"'):
            if token.startswith('"""') or re.search(r'\\(?!["n\\])', token):
                raise EquationError("Invalid quoted XMILE identifier escape")
            try:
                value = ast.literal_eval(token)
            except (SyntaxError, ValueError) as exc:
                raise EquationError("Invalid quoted XMILE identifier") from exc
            tokens[index] = _encode_identifier(value)
        elif token == "~":
            raise EquationError("Use XMILE NOT for logical negation; raw ~ is unsupported")
        elif (token.startswith(ENCODED_IDENTIFIER_PREFIX)
              or (token.isidentifier() and any(ord(character) > 127 for character in token))
              or (keyword.iskeyword(token) and token.upper() not in {"IF", "ELSE", "AND", "OR", "NOT", "TRUE", "FALSE"})):
            tokens[index] = _encode_identifier(token)
    # Exact Vensim built-in spelling, verified against its official manual
    # and the author's original School Closure Initial Model.mdl. Match tokens
    # only, so quoted names and statement-form IF expressions remain intact.
    index = 0
    while index + 3 < len(tokens):
        if [token.upper() for token in tokens[index:index + 4]] == ["IF", "THEN", "ELSE", "("]:
            tokens[index:index + 3] = ["IF_THEN_ELSE"]
        index += 1
    position = 0

    def is_statement_if(index):
        depth = 0
        for token in tokens[index + 1:]:
            upper = token.upper()
            if depth == 0 and upper == "THEN":
                return True
            if depth == 0 and (token in (",", ")", "]") or upper == "ELSE"):
                return False
            if token in ("(", "["):
                depth += 1
            elif token in (")", "]"):
                depth -= 1
        return False

    def sequence(stops):
        nonlocal position
        output = []
        while position < len(tokens) and tokens[position].upper() not in stops:
            token = tokens[position]
            upper = token.upper()
            if upper == "IF" and is_statement_if(position):
                position += 1
                condition = sequence({"THEN"})
                if position >= len(tokens) or tokens[position].upper() != "THEN":
                    raise EquationError("IF requires THEN")
                position += 1
                when_true = sequence({"ELSE"})
                if position >= len(tokens) or tokens[position].upper() != "ELSE":
                    raise EquationError("IF requires ELSE")
                position += 1
                when_false = sequence(stops)
                output.append(f"IF_THEN_ELSE({condition}, {when_true}, {when_false})")
            elif token in ("(", "["):
                close = ")" if token == "(" else "]"
                position += 1
                parts = []
                while True:
                    parts.append(sequence({close, ","}))
                    if position >= len(tokens):
                        raise EquationError("Unclosed expression")
                    delimiter = tokens[position]
                    position += 1
                    if delimiter == close:
                        break
                output.append(token + ", ".join(parts) + close)
            else:
                position += 1
                if upper in ("AND", "OR"):
                    token = upper.lower()
                elif upper == "NOT":
                    # Python's unary ~ has the XMILE NOT precedence relative to
                    # exponentiation/arithmetic. The evaluator gives it logical,
                    # never bitwise, semantics. Raw source ~ is rejected above.
                    token = "~"
                elif upper == "MOD" and position >= 2 and (
                    (tokens[position - 2].isidentifier() and tokens[position - 2].upper() not in
                     {"IF", "THEN", "ELSE", "AND", "OR", "NOT"}) or tokens[position - 2] in (")", "]")
                    or tokens[position - 2][0].isdigit() or tokens[position - 2].startswith(".")):
                    token = "%"
                elif token == "^":
                    token = "**"
                elif token == "=":
                    token = "=="
                elif token == "<>":
                    token = "!="
                elif token == "<" and position < len(tokens) and tokens[position] == ">":
                    token = "!="
                    position += 1
                output.append(token)
        return " ".join(output)

    return sequence(set())


@lru_cache(maxsize=8192)
def _parse_expression(equation):
    if len(equation) > 10000:
        raise EquationError("Equation exceeds 10,000 characters")
    tree = ast.parse(equation, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 1000:
        raise EquationError("Equation is too complex")
    return tree


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
        tree = _parse_expression(equation)
        # Evaluate safely
        evaluator = SafeEvaluator(variables, context)
        return evaluator.visit(tree)
    except SyntaxError as e:
        raise EquationError(f"Syntax error in equation: {e}")
    except Exception as e:
        raise EquationError(f"Error evaluating equation '{equation}': {e}")


def discover_stateful(equation, variables, context):
    """Initialize every hidden stock, including those in inactive IF branches."""
    if not equation.strip():
        return
    tree = _parse_expression(preprocess_equation(equation))
    evaluator = SafeEvaluator(variables, context)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if decode_identifier(node.func.id).upper() in STATEFUL_FUNCTIONS:
                evaluator.visit(node)


def stateful_derivatives(variables, context):
    """Hidden exponential stages' instantaneous derivatives without mutation."""
    derivatives = {}
    for collection in (context.delay_state, context.smooth_state):
        for key, state in collection.items():
            if state["function"] == "DELAY_FIXED":
                continue
            context.equation_key = state["equation_key"]
            evaluator = SafeEvaluator(variables, context)
            args = state["args"]
            input_value = float(evaluator.visit(args[0]))
            duration = float(evaluator.visit(args[1]))
            if state["function"] in ("DELAY_N", "SMOOTH_N"):
                order = float(evaluator.visit(args[2]))
                if order != state["order"]:
                    raise EquationError("Changing delay/smooth order is unsupported")
            if not math.isfinite(input_value) or not math.isfinite(duration) or duration <= 0:
                raise EquationError("Delay/smooth input must be finite and time must be positive")
            if state["function"].startswith("DELAY") and duration != state["duration"]:
                raise EquationError("Changing material delay time is unsupported; use SMOOTH for information")
            previous = state["stages"]
            tau = duration / state["order"]
            rates = [((input_value if i == 0 else previous[i - 1]) - value) / tau
                     for i, value in enumerate(previous)]
            if not all(math.isfinite(rate) for rate in rates):
                raise EquationError("Non-finite delay/smooth derivative; check equations and duration")
            derivatives[key] = rates
    return derivatives


def advance_stateful(variables, context, h):
    """Commit a simultaneous Euler step from inputs at t, never from t+h."""
    rates = stateful_derivatives(variables, context)
    changes, histories = [], []
    for collection in (context.delay_state, context.smooth_state):
        for key, state in collection.items():
            if state["function"] == "DELAY_FIXED":
                context.equation_key = state["equation_key"]
                evaluator = SafeEvaluator(variables, context)
                input_value = float(evaluator.visit(state["args"][0]))
                duration = float(evaluator.visit(state["args"][1]))
                if not math.isfinite(input_value):
                    raise EquationError("Fixed delay input must be finite")
                if duration != state["duration"]:
                    raise EquationError("Changing fixed delay time is unsupported")
                histories.append((state, (context.time, input_value)))
                continue
            updated = [value + h * rate for value, rate in zip(state["stages"], rates[key])]
            if not all(math.isfinite(value) for value in updated):
                raise EquationError("Non-finite delay/smooth state; reduce dt or check equations")
            changes.append((state, updated))
    for state, sample in histories:
        if not state["history"] or state["history"][-1][0] != sample[0]:
            state["history"].append(sample)
    for state, updated in changes:
        state["stages"] = updated


def equation_features(equation, table_names=()):
    """Identify supported stochastic/fixed-delay calls, respecting table precedence."""
    if not equation.strip():
        return {"random_calls": 0, "fixed_delay": False}
    try:
        tree = _parse_expression(preprocess_equation(equation))
    except SyntaxError as exc:
        raise EquationError(f"Syntax error in equation: {exc}") from exc
    tables = {canonical_name(name) for name in table_names}
    calls = [decode_identifier(node.func.id).upper() for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and canonical_name(decode_identifier(node.func.id)) not in tables]
    return {"random_calls": sum(name in STOCHASTIC_FUNCTIONS for name in calls),
            "fixed_delay": any(name in ("DELAY", "DELAY_FIXED") for name in calls)}


def _reference_names(tree):
    """AST names excluding function positions and named LOOKUP table arguments."""
    excluded = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                excluded.add(id(node.func))
                if decode_identifier(node.func.id).upper() == "LOOKUP" and node.args and isinstance(node.args[0], ast.Name):
                    excluded.add(id(node.args[0]))
    return {decode_identifier(node.id) for node in ast.walk(tree) if isinstance(node, ast.Name) and id(node) not in excluded}


def validate_equation(equation: str, available_variables: list[str],
                      table_names: Optional[list[str]] = None) -> tuple[bool, str]:
    """Validate using the same syntax, names and supported functions as simulation."""
    if not equation or not equation.strip():
        return True, ""
    try:
        tree = _parse_expression(preprocess_equation(equation))
        known = {canonical_name(name) for name in available_variables}
        known |= {canonical_name(name) for name in SAFE_CONSTANTS}
        known |= {"time", "dt", "time_step"}
        tables = {canonical_name(name) for name in (table_names or [])}
        functions = {name.upper() for name in SAFE_FUNCTIONS} | CONTEXT_FUNCTIONS
        allowed_nodes = (ast.Expression, ast.Constant, ast.Name, ast.Load, ast.BinOp,
                         ast.UnaryOp, ast.Call, ast.Compare, ast.IfExp, ast.BoolOp,
                         ast.operator, ast.unaryop, ast.cmpop, ast.boolop, ast.Tuple, ast.List)
        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                return False, f"Unsupported expression type: {type(node).__name__}"
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name):
                    return False, "Only simple function calls are allowed"
                if node.keywords:
                    return False, "Keyword arguments are unsupported"
                function = decode_identifier(node.func.id)
                if function.upper() not in functions and canonical_name(function) not in tables:
                    return False, f"Unknown function: {function}"
                if function.upper() == "LOOKUP" and node.args:
                    argument = node.args[0]
                    table = decode_identifier(argument.id) if isinstance(argument, ast.Name) else (
                        argument.value if isinstance(argument, ast.Constant) and isinstance(argument.value, str) else None)
                    if table is None or canonical_name(table) not in tables:
                        return False, f"Unknown lookup table: {table}"
        unknown = {name for name in _reference_names(tree) if canonical_name(name) not in known}
        if unknown:
            return False, f"Unknown variables: {', '.join(sorted(unknown))}"
        return True, ""
    except (SyntaxError, EquationError, ValueError, RecursionError) as exc:
        return False, str(exc)


def get_equation_variables(equation: str) -> set[str]:
    """References for connectors using simulation syntax and aliases.

    Include e/pi because a model parameter may shadow a mathematical constant;
    connector generation filters these against actual model element names.
    """
    if not equation or not equation.strip():
        return set()
    try:
        names = _reference_names(_parse_expression(preprocess_equation(equation)))
        return {name for name in names if name.upper() not in ("TIME", "DT", "TIME_STEP")}
    except (SyntaxError, EquationError, ValueError, RecursionError):
        return set()
