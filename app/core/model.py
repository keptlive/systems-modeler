"""
Pydantic models for systems dynamics primitives.
"""
from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import Optional, Literal
from datetime import datetime, timezone
import uuid


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
    position: Position = Field(default_factory=Position)


class Flow(BaseModel):
    """
    Rate of change between stocks.
    Examples: births, sales, depreciation
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    units: Optional[str] = None
    equation: str = "0"
    from_stock: Optional[str] = None  # Source stock ID
    to_stock: Optional[str] = None    # Destination stock ID
    position: Position = Field(default_factory=Position)


class Variable(BaseModel):
    """
    Auxiliary calculation or parameter.
    Examples: birth_rate, contact_rate, constants
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    units: Optional[str] = None
    equation: str = "0"
    position: Position = Field(default_factory=Position)


class Connector(BaseModel):
    """
    Information link showing dependencies between elements.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_element: str
    to_element: str


class TimeSettings(BaseModel):
    """Simulation time configuration."""
    model_config = ConfigDict(allow_inf_nan=False)
    start: float = 0
    end: float = 100
    dt: float = Field(default=0.25, gt=0)
    integration_method: Literal["euler", "rk4", "radau"] = "euler"
    rtol: float = Field(default=1e-6, ge=1e-12, le=0.1)
    atol: float = Field(default=1e-9, gt=0)
    random_seed: Optional[int] = Field(default=None, strict=True, ge=0, le=4294967295)

    @model_validator(mode="after")
    def validate_grid(self):
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        steps = (self.end - self.start) / self.dt
        if steps < 1:
            raise ValueError("dt must not exceed the simulation duration")
        return self


class LookupTable(BaseModel):
    """
    Lookup table for graphical functions.
    Stores (x, y) points for linear interpolation.
    """
    model_config = ConfigDict(allow_inf_nan=False)
    name: str
    points: list[tuple[float, float]] = Field(default_factory=list)
    # Preserve historical JSON lookup behavior; XMILE imports explicitly set
    # their standard's default (continuous/clamped).
    interpolation: Literal["continuous", "extrapolate", "discrete"] = "extrapolate"

    def to_list(self) -> list[tuple[float, float]]:
        """Convert points to list of tuples for interpolation."""
        return [(p[0], p[1]) for p in self.points]


class Model(BaseModel):
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

    def model_post_init(self, __context):
        """Set timestamps if not provided."""
        now = datetime.now(timezone.utc)
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now


class ModelCreate(BaseModel):
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
    description: Optional[str] = None
    source: Optional[str] = None
    reference: Optional[str] = None
    stocks: Optional[list[Stock]] = None
    flows: Optional[list[Flow]] = None
    variables: Optional[list[Variable]] = None
    connectors: Optional[list[Connector]] = None
    tables: Optional[list[LookupTable]] = None
    time_settings: Optional[TimeSettings] = None


class SimulationRequest(BaseModel):
    """Request body for running a simulation."""
    model_id: Optional[str] = None
    model: Optional[Model] = None
    time_settings: Optional[TimeSettings] = None


class SimulationResult(BaseModel):
    """Result of a simulation run."""
    time: list[float]
    values: dict[str, list[float]]  # variable_name -> list of values
    random_seed: Optional[int] = None  # Effective seed for replaying stochastic runs
    integration_diagnostics: Optional[dict] = None  # Explicit adaptive-solver work/tolerance evidence


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
    from app.core.equations import get_equation_variables, canonical_name

    # Build a lookup map for all element names (normalized to handle variations)
    element_names = {}  # normalized_name -> actual_name

    for stock in model.stocks:
        element_names[canonical_name(stock.name)] = stock.name
        # Store original name and underscore variant
        element_names[stock.name.lower()] = stock.name
        element_names[stock.name.lower().replace(" ", "_")] = stock.name
        element_names[stock.name.lower().replace("_", " ")] = stock.name

    for flow in model.flows:
        element_names[canonical_name(flow.name)] = flow.name
        element_names[flow.name.lower()] = flow.name
        element_names[flow.name.lower().replace(" ", "_")] = flow.name
        element_names[flow.name.lower().replace("_", " ")] = flow.name

    for var in model.variables:
        element_names[canonical_name(var.name)] = var.name
        element_names[var.name.lower()] = var.name
        element_names[var.name.lower().replace(" ", "_")] = var.name
        element_names[var.name.lower().replace("_", " ")] = var.name

    # Collect existing connectors to avoid duplicates
    existing = set()
    for conn in model.connectors:
        existing.add((conn.from_element.lower(), conn.to_element.lower()))

    connectors = list(model.connectors)  # Start with existing connectors
    connector_id = len(connectors) + 1

    def find_element_name(ref: str) -> Optional[str]:
        """Find the actual element name for a reference."""
        ref_lower = canonical_name(ref)
        if ref_lower in element_names:
            return element_names[ref_lower]
        # Try with underscore substitution
        ref_underscore = ref_lower.replace(" ", "_")
        if ref_underscore in element_names:
            return element_names[ref_underscore]
        ref_space = ref_lower.replace("_", " ")
        if ref_space in element_names:
            return element_names[ref_space]
        return None

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
