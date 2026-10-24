"""
Pydantic models for systems dynamics primitives.
"""
from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict
from typing import Optional, Literal
from datetime import datetime, timezone
import uuid
import math


def validate_unicode_text(value):
    """Reject text JSON transports cannot preserve; never normalize identifiers."""
    pending = [value]
    seen = set()
    while pending:
        current = pending.pop()
        if isinstance(current, str):
            try:
                current.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise ValueError("Text must contain valid Unicode scalar values") from exc
        elif isinstance(current, (BaseModel, dict, list, tuple, set, frozenset)):
            if id(current) in seen:
                continue
            seen.add(id(current))
            if isinstance(current, BaseModel):
                pending.extend(getattr(current, name) for name in type(current).model_fields)
            elif isinstance(current, dict):
                pending.extend(current.keys())
                pending.extend(current.values())
            else:
                pending.extend(current)


class Position(BaseModel):
    """2D position on the canvas."""
    model_config = ConfigDict(allow_inf_nan=False)
    x: float = 0
    y: float = 0


class Stock(BaseModel):
    """
    Accumulation/level in the system.
    Examples: population, inventory, capital
    """
    model_config = ConfigDict(allow_inf_nan=False)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    units: Optional[str] = None
    initial_value: float = 0
    equation: str = ""  # For computed initial values
    dimensions: list[str] = Field(default_factory=list)
    initial_values: dict[str, float] = Field(default_factory=dict)
    equations: dict[str, str] = Field(default_factory=dict)
    position: Position = Field(default_factory=Position)


class NonStockElement(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def reject_stock_only_fields(cls, value):
        if isinstance(value, dict) and value.get("initial_values"):
            raise ValueError("initial_values is supported only on stocks")
        return value


class Flow(NonStockElement):
    """
    Rate of change between stocks.
    Examples: births, sales, depreciation
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    units: Optional[str] = None
    equation: str = "0"
    dimensions: list[str] = Field(default_factory=list)
    equations: dict[str, str] = Field(default_factory=dict)
    from_stock: Optional[str] = None  # Source stock ID
    to_stock: Optional[str] = None    # Destination stock ID
    position: Position = Field(default_factory=Position)


class Variable(NonStockElement):
    """
    Auxiliary calculation or parameter.
    Examples: birth_rate, contact_rate, constants
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    units: Optional[str] = None
    role: Literal["auxiliary", "report"] = "auxiliary"
    equation: str = "0"
    dimensions: list[str] = Field(default_factory=list)
    equations: dict[str, str] = Field(default_factory=dict)
    position: Position = Field(default_factory=Position)


class Connector(BaseModel):
    """
    Information link showing dependencies between elements.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_element: str
    to_element: str


def discrete_interval_count(start, end, period):
    """Accept whole periods within representational roundoff, never a partial step."""
    count = (end - start) / period
    if not math.isfinite(count):
        raise ValueError("Discrete model duration must contain complete periods")
    nearest = round(count)
    # Subtraction of a translated time origin carries endpoint roundoff too.
    tolerance = max(8 * math.ulp(count), 2 * (math.ulp(start) + math.ulp(end)) / period)
    if (nearest < 1 or abs(count - nearest) > tolerance
            or (tolerance >= .5 and count != nearest)):
        raise ValueError("Discrete model duration must contain complete periods")
    return nearest


class TimeSettings(BaseModel):
    """Simulation time configuration."""
    model_config = ConfigDict(allow_inf_nan=False)
    units: Optional[str] = None
    start: float = 0
    end: float = 100
    dt: float = Field(default=0.25, gt=0)
    integration_method: Literal["euler", "rk4", "radau"] = "euler"
    discrete_period: Optional[float] = Field(default=None, gt=0)
    rtol: float = Field(default=1e-6, ge=1e-12, le=0.1)
    atol: float = Field(default=1e-9, gt=0)
    random_seed: Optional[int] = Field(default=None, strict=True, ge=0, le=4294967295)

    @model_validator(mode="after")
    def validate_grid(self):
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        if self.discrete_period is not None:
            if self.dt != self.discrete_period or self.integration_method != "euler":
                raise ValueError("Discrete models require Euler with dt equal to discrete_period")
            discrete_interval_count(self.start, self.end, self.discrete_period)
        steps = (self.end - self.start) / self.dt
        if steps < 1:
            # A translated one-step endpoint (5 + .1 == 5.1) may subtract
            # to slightly less than DT. Retain the nominal DT, especially for
            # DT-dependent equations and declared recurrences. Do not infer a
            # whole interval when endpoint precision cannot distinguish one.
            tolerance = max(8 * math.ulp(steps),
                            2 * (math.ulp(self.start) + math.ulp(self.end)) / self.dt)
            if tolerance >= .5 or 1 - steps > tolerance:
                raise ValueError("dt must not exceed the simulation duration")
        return self


class LookupTable(BaseModel):
    """
    Lookup table for graphical functions.
    Stores (x, y) points for linear interpolation.
    """
    model_config = ConfigDict(allow_inf_nan=False)
    name: str
    input_units: Optional[str] = None
    output_units: Optional[str] = None
    points: list[tuple[float, float]] = Field(default_factory=list)
    # Preserve historical JSON lookup behavior; XMILE imports explicitly set
    # their standard's default (continuous/clamped).
    interpolation: Literal["continuous", "extrapolate", "discrete"] = "extrapolate"

    def to_list(self) -> list[tuple[float, float]]:
        """Convert points to list of tuples for interpolation."""
        return [(p[0], p[1]) for p in self.points]


class SourceDocument(BaseModel):
    format: Literal["vensim_mdl"]
    text: str = Field(max_length=2 * 1024 * 1024)
    diagnostics: list[dict] = Field(default_factory=list, max_length=1000)


class StructuredFields(BaseModel):
    """Preserved source structure; scalar execution uses a bounded lowering pass."""
    dimensions: list[dict] = Field(default_factory=list)
    module_definitions: dict[str, dict] = Field(default_factory=dict)
    modules: list[dict] = Field(default_factory=list)
    source_document: Optional[SourceDocument] = None

    def has_structure(self):
        return bool(self.dimensions or self.modules or self.module_definitions or any(
            e.dimensions or e.equations or getattr(e, "initial_values", {})
            for e in [*getattr(self, "stocks", []), *getattr(self, "flows", []), *getattr(self, "variables", [])]))


class Model(StructuredFields):
    """
    Complete systems dynamics model.
    Contains stocks, flows, variables, connectors, lookup tables, and settings.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled Model"
    description: str = ""
    source: Optional[str] = None
    reference: Optional[str] = None
    category: Optional[str] = None  # Category from subdirectory
    stocks: list[Stock] = Field(default_factory=list)
    flows: list[Flow] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)
    connectors: list[Connector] = Field(default_factory=list)
    tables: list[LookupTable] = Field(default_factory=list)
    time_settings: TimeSettings = Field(default_factory=TimeSettings)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="after")
    def valid_text(self):
        validate_unicode_text(self)
        return self

    def model_post_init(self, __context):
        """Set timestamps if not provided."""
        now = datetime.now(timezone.utc)
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now


class ModelCreate(StructuredFields):
    """Request body for creating a new model."""
    name: str = "Untitled Model"
    description: str = ""
    source: Optional[str] = None
    reference: Optional[str] = None
    category: Optional[str] = None
    stocks: list[Stock] = Field(default_factory=list)
    flows: list[Flow] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)
    connectors: list[Connector] = Field(default_factory=list)
    tables: list[LookupTable] = Field(default_factory=list)
    time_settings: TimeSettings = Field(default_factory=TimeSettings)


class ModelUpdate(BaseModel):
    """Request body for updating a model."""
    name: Optional[str] = None
    dimensions: Optional[list[dict]] = None
    module_definitions: Optional[dict[str, dict]] = None
    modules: Optional[list[dict]] = None
    source_document: Optional[SourceDocument] = None
    description: Optional[str] = None
    source: Optional[str] = None
    reference: Optional[str] = None
    stocks: Optional[list[Stock]] = None
    flows: Optional[list[Flow]] = None
    variables: Optional[list[Variable]] = None
    connectors: Optional[list[Connector]] = None
    tables: Optional[list[LookupTable]] = None
    time_settings: Optional[TimeSettings] = None


class TimeSettingsPatch(BaseModel):
    """Explicit timing edits; validate the grid only after inheriting its model."""
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    units: Optional[str] = None
    start: Optional[float] = None
    end: Optional[float] = None
    dt: Optional[float] = Field(default=None, gt=0)
    integration_method: Optional[Literal["euler", "rk4", "radau"]] = None
    rtol: Optional[float] = Field(default=None, ge=1e-12, le=0.1)
    atol: Optional[float] = Field(default=None, gt=0)
    random_seed: Optional[int] = Field(default=None, strict=True, ge=0, le=4294967295)
    discrete_period: Optional[float] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_explicit_nulls(self):
        for name in self.model_fields_set - {"random_seed", "discrete_period", "units"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self

    def apply_to(self, settings: TimeSettings) -> TimeSettings:
        changes = self.model_dump(exclude_unset=True)
        # Timing edits cannot remove a declared recurrence. Whole-model
        # replacement remains the explicit way to change the mathematical model.
        if settings.discrete_period is not None:
            changes["discrete_period"] = settings.discrete_period
        return TimeSettings(**{**settings.model_dump(), **changes})


class SimulationRequest(BaseModel):
    """Request body for running a simulation."""
    model_id: Optional[str] = None
    model: Optional[Model] = None
    time_settings: Optional[TimeSettingsPatch] = None

    @field_validator("time_settings", mode="before")
    @classmethod
    def accept_existing_python_settings(cls, value):
        if isinstance(value, TimeSettings):
            # Existing Python callers supplied a complete validated settings
            # object. JSON objects and TimeSettingsPatch are partial edits.
            return value.model_dump()
        return value


class SimulationResult(BaseModel):
    """Result of a simulation run."""
    model_config = ConfigDict(allow_inf_nan=False)
    time: list[float]
    values: dict[str, list[float]]  # variable_name -> list of values
    report_values: dict[str, list[float | str]] = Field(default_factory=dict)
    random_seed: Optional[int] = None  # Effective seed for replaying stochastic runs
    integration_diagnostics: Optional[dict] = None  # Explicit adaptive-solver work/tolerance evidence

    @model_validator(mode="after")
    def finite_diagnostics(self):
        validate_unicode_text(self)
        # Arbitrary diagnostic dictionaries otherwise bypass finite float-field
        # validation and can fail JSON transport or silently serialize as null.
        pending = [self.integration_diagnostics]
        seen = set()
        while pending:
            value = pending.pop()
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Simulation diagnostics must contain finite numbers")
            if isinstance(value, (dict, list, tuple, set, frozenset)):
                if id(value) in seen:
                    continue
                seen.add(id(value))
                if isinstance(value, dict):
                    pending.extend(value.keys())
                    pending.extend(value.values())
                else:
                    pending.extend(value)
        return self


class LLMGenerateRequest(BaseModel):
    """Request body for generating a model from description."""
    description: str


class LLMModifyRequest(BaseModel):
    """Request body for modifying an existing model."""
    model_id: Optional[str] = None
    model: Optional[Model] = None
    modification: str


def generate_connectors_from_equations(model: Model) -> list[Connector]:
    """
    Auto-generate connectors by parsing equations to find variable dependencies.

    For each flow and variable, parse its equation to find referenced stocks/variables,
    then create connectors from referenced elements to the element using them.

    Args:
        model: The model to analyze

    Returns:
        List of Connector objects representing equation dependencies
    """
    if model.has_structure():
        return list(model.connectors)
    from app.core.equations import get_equation_variables, resolve_name

    element_names = tuple(e.name for e in (*model.stocks, *model.flows, *model.variables))

    # Collect existing connectors to avoid duplicates
    existing = set()
    for conn in model.connectors:
        existing.add((conn.from_element.lower(), conn.to_element.lower()))

    connectors = list(model.connectors)  # Start with existing connectors
    connector_id = len(connectors) + 1

    def find_element_name(ref: str) -> Optional[str]:
        """Find the actual element name for a reference."""
        return resolve_name(ref, element_names)

    # Process flows
    for flow in model.flows:
        if flow.equation:
            refs = get_equation_variables(flow.equation)
            for ref in refs:
                source_name = find_element_name(ref)
                if source_name and (source_name.lower(), flow.name.lower()) not in existing:
                    connectors.append(Connector(
                        id=f"auto-conn-{connector_id}",
                        from_element=source_name,
                        to_element=flow.name
                    ))
                    existing.add((source_name.lower(), flow.name.lower()))
                    connector_id += 1

    # Process variables
    for var in model.variables:
        if var.equation:
            refs = get_equation_variables(var.equation)
            for ref in refs:
                source_name = find_element_name(ref)
                if source_name and source_name.lower() != var.name.lower():
                    if (source_name.lower(), var.name.lower()) not in existing:
                        connectors.append(Connector(
                            id=f"auto-conn-{connector_id}",
                            from_element=source_name,
                            to_element=var.name
                        ))
                        existing.add((source_name.lower(), var.name.lower()))
                        connector_id += 1

    return connectors
