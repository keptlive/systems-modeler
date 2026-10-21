"""Independent review counterexamples, separate from model-repair pass counts."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.simulate import router
from app.core.equations import EquationError
from app.core.model import Model
from app.core.simulator import simulate


@pytest.mark.parametrize('interpolation', ['discrete', 'continuous', 'extrapolate'])
@pytest.mark.parametrize('aliased', [False, True])
@pytest.mark.parametrize('syntax', ['named', 'lookup'])
def test_radau_rejects_time_lookup_pulse(interpolation, aliased, syntax):
    # Both interpolation families have area .5: a half-unit rectangle for
    # discrete, and a unit-wide triangle for either linear convention.
    argument = 'Clock' if aliased else 'TIME'
    equation = f'Forcing({argument})' if syntax == 'named' else f'LOOKUP(Forcing,{argument})'
    m = Model(stocks=[{'id': 'x', 'name': 'X'}],
              flows=[{'name': 'Input', 'equation': equation, 'to_stock': 'x'}],
              variables=[{'name': 'Clock', 'equation': 'Clock2+1'}, {'name': 'Clock2', 'equation': 'TIME-1'}] if aliased else [],
              tables=[{'name': 'Forcing', 'points': [[0, 0], [10, 0], [10.5, 1], [11, 0], [100, 0]], 'interpolation': interpolation}],
              time_settings={'end': 100, 'dt': 20, 'integration_method': 'radau', 'rtol': 1e-9, 'atol': 1e-12})
    with pytest.raises(EquationError) as caught:
        simulate(m)
    assert caught.value.code == 'unsupported_method_features'
    assert any(row['operation'] == 'time-dependent lookup'
               for row in caught.value.details['time_discontinuities'])


@pytest.mark.parametrize('equation', [
    'WITH_LOOKUP(TIME,((0,0),(10,0),(10.5,1),(11,0),(100,0)))',
    'WITH_LOOKUP(X,((0,0),(1,TIME)))'])
def test_radau_rejects_time_dependent_inline_lookup_input_or_points(equation):
    m = Model(stocks=[{'id': 'x', 'name': 'X', 'initial_value': 1}],
              flows=[{'name': 'Input', 'equation': equation, 'to_stock': 'x'}],
              time_settings={'end': 100, 'dt': 20, 'integration_method': 'radau'})
    with pytest.raises(EquationError) as caught:
        simulate(m)
    assert caught.value.code == 'unsupported_method_features'


@pytest.mark.parametrize('equation', ['-Forcing(X)', '-LOOKUP(Forcing,X)',
                                      '-WITH_LOOKUP(X,((0,0),(1,1)))'])
def test_radau_preserves_stock_driven_graphical_functions(equation):
    import math
    m = Model(stocks=[{'id': 'x', 'name': 'X', 'initial_value': 1}],
              flows=[{'name': 'Change', 'equation': equation, 'to_stock': 'x'}],
              tables=[{'name': 'Forcing', 'points': [[0,0],[1,1]], 'interpolation': 'continuous'}],
              time_settings={'end': 3, 'dt': .3, 'integration_method': 'radau', 'rtol': 1e-9, 'atol': 1e-12})
    r = simulate(m)
    assert r.values['X'] == pytest.approx([math.exp(-t) for t in r.time], abs=2e-9)


def test_radau_partial_final_interval_retains_authored_dt_meaning():
    m = Model(stocks=[{'id': 'x', 'name': 'X'}],
              flows=[{'name': 'Input', 'equation': 'DT', 'to_stock': 'x'}],
              time_settings={'end': 1, 'dt': .3, 'integration_method': 'radau', 'rtol': 1e-10, 'atol': 1e-12})
    r = simulate(m)
    assert r.time == [0, .3, .6, .3*3, 1]
    assert r.values['X'] == pytest.approx([.3*t for t in r.time], abs=1e-12)
    assert m.time_settings.dt == .3


def test_radau_investigation_distinguishes_output_spacing_from_solver_convergence():
    from app.core.diagnostics import investigate_model
    m = Model(stocks=[{'id': 'x', 'name': 'X', 'initial_value': 1}],
              flows=[{'name': 'Loss', 'equation': 'X', 'from_stock': 'x'}],
              time_settings={'end': 1, 'dt': .25, 'integration_method': 'radau', 'rtol': 1e-8, 'atol': 1e-11})
    report = investigate_model(m)
    assert all(row['status'] == 'completed' for row in report['runs'])
    assert [row['samples'] for row in report['runs']] == [5, 9, 17]
    assert {row['settings']['rtol'] for row in report['runs']} == {1e-8}
    assessment = report['timestep_assessment']
    assert assessment['status'] == 'output_grid_comparison_only'
    assert assessment['internal_tolerances_refined'] is False
    assert assessment['scope'] == 'output grids at unchanged adaptive tolerances'
    assert 'not an internal-step or tolerance convergence test' in assessment['interpretation']
    assert any('Radau DT is retained output spacing' in warning for warning in report['warnings'])


def test_actual_dependency_retries_do_not_advance_binomial_streams():
    variables = [{'name': 'Draw', 'equation': 'RANDOM_BINOMIAL(200,.5)+Later'},
                 {'name': 'Later', 'equation': '2'}]
    settings = {'end': 4, 'dt': 1, 'random_seed': 123}
    # In the first ordering the random call executes before the unknown Later,
    # so each accepted-time equation retries after Later becomes available.
    retry = simulate(Model(variables=variables, time_settings=settings))
    ordered = simulate(Model(variables=variables[::-1], time_settings=settings))
    assert retry.values == ordered.values
    assert retry.integration_diagnostics['binomial_trials'] == 200 * 5
    assert ordered.integration_diagnostics['binomial_trials'] == 200 * 5


def test_http_nonfinite_stock_is_json_safe_and_preserves_last_finite_snapshot():
    # Exercise the HTTP endpoint without consuming the process-wide MCP
    # session manager's single-use lifespan needed by transport regressions.
    application = FastAPI()
    application.include_router(router, prefix='/api')
    with TestClient(application) as client:
        response = client.post('/api/simulate', json={'model': {
            'stocks': [{'id': 'x', 'name': 'X', 'initial_value': 1e308}],
            'flows': [{'name': 'Input', 'equation': '1e308', 'to_stock': 'x'}],
            'time_settings': {'end': 2, 'dt': 1}}})
    assert response.status_code == 422
    failure = response.json()['failure']
    assert failure['code'] == 'non_finite_stock'
    assert failure['time'] == 1
    assert failure['previous_stock_values'] == {'X': 1e308}
    assert failure['stocks'] == ['X']
