"""Bounded pure-function compatibility; dialect differences are intentional."""
import math
import pytest
from app.core.equations import EquationError, SimulationContext, safe_eval

@pytest.mark.parametrize("name,argument,expected", [
    ("ARCSIN", .5, math.pi/6), ("ARCCOS", .5, math.pi/3),
    ("ARCTAN", 1, math.pi/4), ("arcsin", -1, -math.pi/2),
    ("INT", -3.2, -4), ("INT", 3.2, 3),
    ("TRUNC", -3.2, -3), ("TRUNC", 3.2, 3),
])
def test_unary(name, argument, expected):
    assert safe_eval(f"{name}({argument})", {}) == pytest.approx(expected)

@pytest.mark.parametrize("x,q,expected", [
    (-9.9,3,-9), (9.9,3,9), (-9.9,-3,-9.9), (9.9,0,9.9),
    (-.2,.5,0), (6,3,6),
])
def test_quantum(x,q,expected):
    assert safe_eval(f"QUANTUM({x},{q})", {}) == pytest.approx(expected)

@pytest.mark.parametrize("expression,expected", [
    ("SAFEDIV(4,2)",2), ("SAFEDIV(4,0)",0),
    ("SAFEDIV(4,-0.0,7)",7), ("SAFEDIV(4,1e-7,7)",4e7),
    ("ZIDZ(4,1e-7)",0), ("XIDZ(4,-1e-7,7)",7),
    ("XIDZ(4,1e-6,7)",4e6), ("XIDZ(4,-1e-6,7)",-4e6),
    ("ZIDZ(4,0)",0), ("XIDZ(4,0,7)",7),
])
def test_division_dialect_boundaries(expression,expected):
    assert safe_eval(expression,{}) == expected

@pytest.mark.parametrize("expression", [
    "INT()", "TRUNC(1,2)", "QUANTUM(2)", "SAFEDIV(1)",
    "SAFEDIV(1,2,3,4)", "ZIDZ(1,2,3)", "XIDZ(1,2)",
])
def test_arity_diagnostics(expression):
    with pytest.raises(EquationError) as error:
        safe_eval(expression,{})
    assert error.value.code == "function_signature"

@pytest.mark.parametrize("expression", [
    "ARCSIN(2)", "ARCCOS(-2)", "SAFEDIV(1,1e-320)", "QUANTUM(1,1e-320)",
])
def test_domain_and_finite_guards(expression):
    with pytest.raises(EquationError):
        safe_eval(expression,{})

def test_time_bounds_context_and_declared_ownership():
    context=SimulationContext(time=8,start_time=5,stop_time=20)
    assert safe_eval("STARTTIME+STOPTIME",{},context)==25
    assert safe_eval("STARTTIME",{"STARTTIME":12},context)==12
    context.declared_symbols=("STARTTIME",)
    with pytest.raises(EquationError,match="Unknown variable"):
        safe_eval("STARTTIME",{},context)

def test_new_function_table_ownership_is_preserved():
    context=SimulationContext(tables={"INT":[(0,10),(1,20)]})
    assert safe_eval("INT(.5)",{},context)==15

@pytest.mark.parametrize("expression", [
    "SAFEDIV(1,2,1/0)", "XIDZ(1,2,1/0)", "ZIDZ(1/0,0)",
])
def test_pure_arguments_remain_eager(expression):
    with pytest.raises(EquationError) as error:
        safe_eval(expression,{})
    assert error.value.code=="division_by_zero"
