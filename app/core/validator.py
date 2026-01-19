"""
Model Validator - Checks model integrity and completeness.

Validates:
- All stocks have at least one connected flow
- All equation variable references exist
- Equations are syntactically valid
- No orphaned elements
"""
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from app.core.model import Model
from app.core.equations import validate_equation, get_equation_variables


class ValidationSeverity(Enum):
    ERROR = "error"      # Model will not simulate correctly
    WARNING = "warning"  # Model may have issues
    INFO = "info"        # Suggestion for improvement


@dataclass
class ValidationIssue:
    severity: ValidationSeverity
    code: str
    message: str
    element_type: Optional[str] = None  # stock, flow, variable
    element_name: Optional[str] = None
    
    def to_dict(self):
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "element_type": self.element_type,
            "element_name": self.element_name
        }


@dataclass 
class ValidationResult:
    is_valid: bool
    issues: List[ValidationIssue]
    
    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
    
    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [i.to_dict() for i in self.issues]
        }


def validate_model(model: Model) -> ValidationResult:
    """
    Validate a model for completeness and correctness.
    
    Returns ValidationResult with any issues found.
    """
    issues: List[ValidationIssue] = []
    
    # Build lookup sets
    stock_ids = {s.id for s in model.stocks}
    stock_names = {s.name for s in model.stocks}
    flow_names = {f.name for f in model.flows}
    var_names = {v.name for v in model.variables}
    all_names = stock_names | flow_names | var_names
    
    # Check 1: Stocks without flows (ERROR)
    issues.extend(_check_disconnected_stocks(model, stock_ids, stock_names))
    
    # Check 2: Empty model (WARNING)
    if len(model.stocks) == 0 and len(model.flows) == 0:
        issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            code="EMPTY_MODEL",
            message="Model has no stocks or flows"
        ))
    
    # Check 3: Flows with invalid stock references (ERROR)
    issues.extend(_check_flow_references(model, stock_ids, stock_names))
    
    # Check 4: Equation syntax and variable references (ERROR/WARNING)
    issues.extend(_check_equations(model, all_names))
    
    # Check 5: Stocks with no initial value and no equation (WARNING)
    for stock in model.stocks:
        if stock.initial_value == 0 and not stock.equation:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="ZERO_INITIAL_VALUE", 
                message=f"Stock {stock.name} has initial value of 0",
                element_type="stock",
                element_name=stock.name
            ))
    
    # Determine overall validity (no errors = valid)
    is_valid = len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0
    
    return ValidationResult(is_valid=is_valid, issues=issues)


def _check_disconnected_stocks(model: Model, stock_ids: set, stock_names: set) -> List[ValidationIssue]:
    """Check that all stocks have at least one flow connection."""
    issues = []
    
    # Find stocks referenced by flows
    connected_stocks = set()
    for flow in model.flows:
        if flow.from_stock:
            connected_stocks.add(flow.from_stock)
        if flow.to_stock:
            connected_stocks.add(flow.to_stock)
    
    # Check each stock
    for stock in model.stocks:
        is_connected = (
            stock.id in connected_stocks or 
            stock.name in connected_stocks
        )
        if not is_connected:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="DISCONNECTED_STOCK",
                message=f"Stock {stock.name} has no connected flows - will remain constant",
                element_type="stock",
                element_name=stock.name
            ))
    
    return issues


def _check_flow_references(model: Model, stock_ids: set, stock_names: set) -> List[ValidationIssue]:
    """Check that flows reference valid stocks."""
    issues = []
    all_stock_refs = stock_ids | stock_names
    
    for flow in model.flows:
        # Check from_stock
        if flow.from_stock and flow.from_stock not in all_stock_refs:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_FLOW_SOURCE",
                message=f"Flow {flow.name} references non-existent source stock {flow.from_stock}",
                element_type="flow",
                element_name=flow.name
            ))
        
        # Check to_stock
        if flow.to_stock and flow.to_stock not in all_stock_refs:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_FLOW_TARGET",
                message=f"Flow {flow.name} references non-existent target stock {flow.to_stock}",
                element_type="flow",
                element_name=flow.name
            ))
        
        # Check that flow has at least one stock connection
        if not flow.from_stock and not flow.to_stock:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="ORPHAN_FLOW",
                message=f"Flow {flow.name} is not connected to any stock",
                element_type="flow",
                element_name=flow.name
            ))
    
    return issues


def _check_equations(model: Model, all_names: set) -> List[ValidationIssue]:
    """Check equation syntax and variable references."""
    issues = []
    
    # Add TIME as valid reference
    valid_refs = all_names | {"TIME", "time"}
    
    # Get table names if any
    table_names = [t.name for t in model.tables] if model.tables else []
    
    # Check flow equations
    for flow in model.flows:
        if flow.equation:
            eq_issues = _validate_single_equation(
                flow.equation, valid_refs, table_names, "flow", flow.name
            )
            issues.extend(eq_issues)
    
    # Check variable equations
    for var in model.variables:
        if var.equation:
            eq_issues = _validate_single_equation(
                var.equation, valid_refs, table_names, "variable", var.name
            )
            issues.extend(eq_issues)
    
    # Check stock equations (initial value expressions)
    for stock in model.stocks:
        if stock.equation:
            eq_issues = _validate_single_equation(
                stock.equation, valid_refs, table_names, "stock", stock.name
            )
            issues.extend(eq_issues)
    
    return issues


def _validate_single_equation(
    equation: str, 
    valid_refs: set, 
    table_names: list,
    element_type: str,
    element_name: str
) -> List[ValidationIssue]:
    """Validate a single equation."""
    issues = []
    
    # Skip simple numeric values
    try:
        float(equation.strip())
        return []
    except ValueError:
        pass
    
    # Get referenced variables
    try:
        referenced = get_equation_variables(equation)
    except Exception as e:
        issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            code="EQUATION_PARSE_ERROR",
            message=f"Cannot parse equation in {element_type} {element_name}: {str(e)}",
            element_type=element_type,
            element_name=element_name
        ))
        return issues
    
    # Check for undefined references
    # Allow underscore/space variations
    for ref in referenced:
        ref_variations = {ref, ref.replace("_", " "), ref.replace(" ", "_")}
        if not any(v in valid_refs for v in ref_variations):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="UNDEFINED_REFERENCE",
                message=f"Equation in {element_type} {element_name} references undefined variable {ref}",
                element_type=element_type,
                element_name=element_name
            ))
    
    return issues


def validate_all_models(models_dir: str = None) -> dict:
    """
    Validate all models in the models directory.
    
    Returns dict with model_id -> ValidationResult mapping.
    """
    import os
    import json
    from app.core.model import Model
    
    if models_dir is None:
        # Default to the models directory relative to app
        import pathlib
        models_dir = pathlib.Path(__file__).parent.parent.parent / "models"
    
    results = {}
    
    for root, dirs, files in os.walk(models_dir):
        for file in files:
            if file.endswith(".json"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                    
                    model = Model(**data)
                    result = validate_model(model)
                    
                    if result.issues:  # Only include models with issues
                        results[model.id] = {
                            "name": model.name,
                            "path": filepath,
                            "validation": result.to_dict()
                        }
                        
                except Exception as e:
                    results[file] = {
                        "name": file,
                        "path": filepath,
                        "validation": {
                            "is_valid": False,
                            "error_count": 1,
                            "warning_count": 0,
                            "issues": [{
                                "severity": "error",
                                "code": "LOAD_ERROR",
                                "message": f"Failed to load model: {str(e)}"
                            }]
                        }
                    }
    
    return results
