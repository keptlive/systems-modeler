"""Complete simulation and interchange checks for compatibility additions."""
import math
import pytest
from app.core.model import Model
from app.core.simulator import simulate
from app.core.xmile_parser import parse_xmile
from app.core.xmile_generator import generate_xmile
from app.core.units import analyze_units
from app.core.equations import EquationError


@pytest.mark.parametrize('method', ['euler', 'rk4', 'radau'])
def test_time_bounds_follow_model_settings_at_nonzero_start(method):
    model = Model(variables=[{'name': 'Bounds', 'equation': 'STOPTIME-STARTTIME'},
                            {'name': 'Elapsed', 'equation': 'TIME-STARTTIME'}],
                  time_settings={'start': 3, 'end': 5, 'dt': .25, 'integration_method': method})
    result = simulate(model)
    assert result.values['Bounds'] == [2]*9
    assert result.values['Elapsed'] == pytest.approx([n*.25 for n in range(9)])


@pytest.mark.parametrize('equation,expected', [
    ('asin(.5)', math.pi/6), ('ARCSIN(.5)', math.pi/6),
    ('acos(.5)', math.pi/3), ('ARCCOS(.5)', math.pi/3),
    ('atan(1)', math.pi/4), ('ARCTAN(1)', math.pi/4),
    ('STOPTIME-STARTTIME', 2),
    ('STOPTIME()-STARTTIME()', 2),
    ('INT(-1.5)', -2), ('TRUNC(-1.5)', -1), ('QUANTUM(-5, 2)', -4),
    ('SAFEDIV(1, 0, 7)', 7), ('SAFEDIV(1, 0)', 0),
])
def test_scalar_compatibility_xmile_roundtrip(equation, expected):
    model = Model(variables=[{'name': 'Result', 'equation': equation}],
                  time_settings={'start': 3, 'end': 5, 'dt': .25})
    before = simulate(model)
    restored = parse_xmile(generate_xmile(model))
    after = simulate(restored)
    assert after.time == before.time
    assert after.values == before.values
    assert after.values['Result'] == pytest.approx([expected]*9)


def test_declared_time_bound_names_preserve_existing_scalar_models():
    model = Model(variables=[{'name': 'Result', 'equation': 'STARTTIME+STOPTIME'},
                            {'name': 'STARTTIME', 'equation': '11'},
                            {'name': 'STOPTIME', 'equation': '13'}],
                  time_settings={'start': 3, 'end': 5, 'dt': .25})
    assert simulate(model).values['Result'] == [24]*9


def test_time_bound_units_and_inverse_trig_units():
    model = Model(variables=[{'name': 'Duration', 'equation': 'STOPTIME-STARTTIME', 'units': 'year'},
                            {'name': 'Angle', 'equation': 'ARCSIN(.5)', 'units': 'dimensionless'}],
                  time_settings={'start': 3, 'end': 5, 'dt': .25, 'units': 'year'})
    assert analyze_units(model)['status'] == 'consistent'
    model.variables[1].equation = 'ARCSIN(Duration)'
    assert analyze_units(model)['status'] == 'inconsistent'


@pytest.mark.parametrize('expression', ['INT(TIME)', 'TRUNC(TIME)', 'QUANTUM(TIME, .1)',
                                       'SAFEDIV(1, TIME-4)', 'ZIDZ(1, TIME-4)', 'XIDZ(1, TIME-4, 7)'])
def test_radau_rejects_new_uncertified_time_switches(expression):
    model = Model(stocks=[{'id': 's', 'name': 'Stock', 'initial_value': 0}],
                  flows=[{'name': 'Rate', 'equation': expression, 'to_stock': 's'}],
                  time_settings={'start': 3, 'end': 5, 'dt': .25, 'integration_method': 'radau'})
    with pytest.raises(EquationError) as caught:
        simulate(model)
    assert caught.value.code == 'unsupported_method_features'


def test_radau_allows_safe_division_with_constant_denominator():
    model = Model(stocks=[{'id': 's', 'name': 'Stock', 'initial_value': 1}],
                  flows=[{'name': 'Rate', 'equation': 'SAFEDIV(Stock, 2)', 'to_stock': 's'}],
                  time_settings={'end': 2, 'dt': .25, 'integration_method': 'radau'})
    assert simulate(model).values['Stock'][-1] == pytest.approx(math.e, rel=1e-5)


def test_time_bounds_honor_run_overrides_without_mutating_source():
    model = Model(variables=[{'name': 'Bounds', 'equation': 'STOPTIME-STARTTIME'}],
                  time_settings={'start': 3, 'end': 5, 'dt': .25})
    settings = model.time_settings.model_copy(update={'start': 10, 'end': 11})
    assert simulate(model, settings).values['Bounds'] == [1]*5
    assert model.time_settings.start == 3
    assert simulate(model).values['Bounds'] == [2]*9


@pytest.mark.parametrize('name', ['TRUNC', 'QUANTUM', 'SAFEDIV'])
def test_preexisting_scalar_function_names_still_roundtrip(name):
    model = Model(variables=[{'name': name, 'equation': '3'},
                            {'name': 'Result', 'equation': f'"{name}"+1'}],
                  time_settings={'end': 1, 'dt': .25})
    assert simulate(parse_xmile(generate_xmile(model))).values['Result'] == [4]*5


@pytest.mark.parametrize('name', ['TRUNC', 'QUANTUM', 'SAFEDIV'])
def test_preexisting_graphical_function_names_use_explicit_lookup_on_export(name):
    model = Model(variables=[{'name': 'Result', 'equation': f'{name}(.5)'}],
                  tables=[{'name': name, 'points': [(0, 10), (1, 20)]}],
                  time_settings={'end': 1, 'dt': .25})
    xml = generate_xmile(model)
    assert 'LOOKUP' in xml
    assert simulate(parse_xmile(xml)).values['Result'] == [15]*5
